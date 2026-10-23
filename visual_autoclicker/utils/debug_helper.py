"""Screenshot debug helper: annotate and save debug images."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("visual_autoclicker.debug")


class DebugHelper:
    def __init__(self, config: Dict[str, Any]):
        dbg_cfg = config.get("debug", {})
        self.enabled: bool = dbg_cfg.get("save_screenshots", False)
        self.save_on_failure: bool = dbg_cfg.get("save_on_failure", True)
        self.annotate: bool = dbg_cfg.get("annotate_matches", True)
        self.out_dir = Path(dbg_cfg.get("screenshot_dir", "debug_screenshots"))
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def _timestamp(self) -> str:
        return time.strftime("%Y%m%d_%H%M%S")

    def save(self, screen: np.ndarray, filename: str,
             matches: Optional[List] = None,
             label: str = "") -> Path:
        """Save annotated screenshot. matches: list of MatchResult."""
        annotated = screen.copy()
        if self.annotate and matches:
            for m in matches:
                left, top = m.left, m.top
                cv2.rectangle(annotated,
                              (left, top),
                              (left + m.width, top + m.height),
                              (0, 255, 0), 2)
                conf_text = f"{m.confidence:.2f}"
                cv2.putText(annotated, conf_text, (left, top - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        if label:
            cv2.putText(annotated, label, (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

        path = self.out_dir / filename
        cv2.imwrite(str(path), annotated)
        logger.debug("Debug screenshot saved: %s", path)
        return path

    def save_match_attempt(self, screen: np.ndarray,
                           template_name: str,
                           matches: Optional[List] = None,
                           success: bool = True) -> Optional[Path]:
        status = "ok" if success else "fail"
        if success and not self.enabled:
            return None
        if not success and not self.save_on_failure:
            return None
        ts = self._timestamp()
        filename = f"{ts}_{template_name}_{status}.png"
        label = f"{'FOUND' if success else 'NOT FOUND'}: {template_name}"
        return self.save(screen, filename, matches=matches, label=label)

    def save_ocr_attempt(self, screen: np.ndarray,
                         target_text: str,
                         results: Optional[List] = None,
                         success: bool = True) -> Optional[Path]:
        if success and not self.enabled:
            return None
        if not success and not self.save_on_failure:
            return None
        ts = self._timestamp()
        safe_name = "".join(c if c.isalnum() else "_" for c in target_text[:20])
        status = "ok" if success else "fail"
        filename = f"{ts}_ocr_{safe_name}_{status}.png"

        annotated = screen.copy()
        if self.annotate and results:
            for r in results:
                left, top, width, height = r.bbox
                cv2.rectangle(annotated, (left, top),
                              (left + width, top + height), (255, 128, 0), 2)
                cv2.putText(annotated, r.text, (left, top - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 128, 0), 1)

        label = f"OCR {'FOUND' if success else 'NOT FOUND'}: {target_text}"
        cv2.putText(annotated, label, (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 128, 0), 2)
        path = self.out_dir / filename
        cv2.imwrite(str(path), annotated)
        logger.debug("OCR debug screenshot saved: %s", path)
        return path
