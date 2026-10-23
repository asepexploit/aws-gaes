"""OCR engine wrapper supporting pytesseract and EasyOCR."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("visual_autoclicker.ocr")

# Auto-detect Tesseract path on Windows
import os as _os, shutil as _shutil
_DEFAULT_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
try:
    import pytesseract as _tess
    if _os.path.exists(_DEFAULT_TESSERACT):
        _tess.pytesseract.tesseract_cmd = _DEFAULT_TESSERACT
except ImportError:
    pass


@dataclass
class OcrResult:
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (left, top, width, height)

    @property
    def center(self) -> Tuple[int, int]:
        return self.bbox[0] + self.bbox[2] // 2, self.bbox[1] + self.bbox[3] // 2


class OcrEngine:
    def __init__(self, config: Dict[str, Any]):
        ocr_cfg = config.get("ocr", {})
        self.engine_name: str = ocr_cfg.get("engine", "tesseract")
        self.lang: str = ocr_cfg.get("lang", "eng")
        self.psm: int = ocr_cfg.get("psm", 6)
        self.scale_factor: float = ocr_cfg.get("scale_factor", 2.0)
        self.preprocess: bool = ocr_cfg.get("preprocess", True)
        self._easyocr_reader = None

    def _preprocess_image(self, img: np.ndarray) -> np.ndarray:
        """Upscale and threshold for better OCR accuracy on screen text."""
        if self.scale_factor != 1.0:
            h, w = img.shape[:2]
            img = cv2.resize(img, (int(w * self.scale_factor), int(h * self.scale_factor)),
                             interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        if self.preprocess:
            gray = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
        return gray

    def extract_text(self, img: np.ndarray) -> str:
        """Extract all text from image."""
        results = self.find_text(img, target=None)
        return " ".join(r.text for r in results)

    def find_text(self, img: np.ndarray,
                  target: Optional[str],
                  case_sensitive: bool = False) -> List[OcrResult]:
        """Find text blocks; if target given, filter by substring match."""
        if self.engine_name == "easyocr":
            return self._find_easyocr(img, target, case_sensitive)
        return self._find_tesseract(img, target, case_sensitive)

    def _find_tesseract(self, img: np.ndarray,
                        target: Optional[str],
                        case_sensitive: bool) -> List[OcrResult]:
        try:
            import pytesseract
        except ImportError:
            raise ImportError("pytesseract not installed. Run: pip install pytesseract")

        processed = self._preprocess_image(img)
        config_str = f"--psm {self.psm}"
        data = pytesseract.image_to_data(
            processed, lang=self.lang, config=config_str,
            output_type=pytesseract.Output.DICT
        )

        results = []
        sf = self.scale_factor
        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = float(data["conf"][i])
            if not text or conf < 0:
                continue
            # Scale bounding box back to original coordinates
            left = int(data["left"][i] / sf)
            top = int(data["top"][i] / sf)
            width = int(data["width"][i] / sf)
            height = int(data["height"][i] / sf)
            r = OcrResult(text=text, confidence=conf / 100.0,
                          bbox=(left, top, width, height))
            if target is None:
                results.append(r)
            else:
                needle = target if case_sensitive else target.lower()
                haystack = text if case_sensitive else text.lower()
                if needle in haystack:
                    results.append(r)
        return results

    def _find_easyocr(self, img: np.ndarray,
                      target: Optional[str],
                      case_sensitive: bool) -> List[OcrResult]:
        try:
            import easyocr
        except ImportError:
            raise ImportError("easyocr not installed. Run: pip install easyocr")

        if self._easyocr_reader is None:
            langs = [self.lang] if self.lang != "eng" else ["en"]
            self._easyocr_reader = easyocr.Reader(langs, gpu=False)
            logger.info("EasyOCR reader initialized (first-run download may occur)")

        processed = self._preprocess_image(img)
        detections = self._easyocr_reader.readtext(processed)
        results = []
        sf = self.scale_factor
        for (box, text, conf) in detections:
            text = text.strip()
            if not text:
                continue
            xs = [int(p[0] / sf) for p in box]
            ys = [int(p[1] / sf) for p in box]
            left, top = min(xs), min(ys)
            width = max(xs) - left
            height = max(ys) - top
            r = OcrResult(text=text, confidence=conf, bbox=(left, top, width, height))
            if target is None:
                results.append(r)
            else:
                needle = target if case_sensitive else target.lower()
                haystack = text if case_sensitive else text.lower()
                if needle in haystack:
                    results.append(r)
        return results
