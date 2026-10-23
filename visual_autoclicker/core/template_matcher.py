"""OpenCV template matching with multi-scale support and NMS."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("visual_autoclicker.matcher")

_METHOD_MAP = {
    "TM_CCOEFF_NORMED": cv2.TM_CCOEFF_NORMED,
    "TM_CCORR_NORMED": cv2.TM_CCORR_NORMED,
    "TM_SQDIFF_NORMED": cv2.TM_SQDIFF_NORMED,
}


@dataclass
class MatchResult:
    x: int          # center x on screen
    y: int          # center y on screen
    width: int
    height: int
    confidence: float
    scale: float = 1.0

    @property
    def left(self) -> int:
        return self.x - self.width // 2

    @property
    def top(self) -> int:
        return self.y - self.height // 2

    @property
    def center(self) -> Tuple[int, int]:
        return self.x, self.y


def _non_max_suppression(boxes: List[Tuple[int, int, int, int, float]],
                          overlap_thresh: float = 0.5) -> List[Tuple[int, int, int, int, float]]:
    """boxes: list of (x, y, w, h, confidence)"""
    if not boxes:
        return []
    arr = np.array([[b[0], b[1], b[0] + b[2], b[1] + b[3], b[4]] for b in boxes],
                   dtype=np.float32)
    x1, y1, x2, y2, scores = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3], arr[:, 4]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(scores)[::-1]
    kept = []
    while idxs.size > 0:
        i = idxs[0]
        kept.append(i)
        ix1 = np.maximum(x1[i], x1[idxs[1:]])
        iy1 = np.maximum(y1[i], y1[idxs[1:]])
        ix2 = np.minimum(x2[i], x2[idxs[1:]])
        iy2 = np.minimum(y2[i], y2[idxs[1:]])
        iw = np.maximum(0, ix2 - ix1 + 1)
        ih = np.maximum(0, iy2 - iy1 + 1)
        overlap = (iw * ih) / areas[idxs[1:]]
        idxs = idxs[1:][overlap <= overlap_thresh]
    return [(int(arr[i, 0]), int(arr[i, 1]),
             int(arr[i, 2] - arr[i, 0]), int(arr[i, 3] - arr[i, 1]),
             float(arr[i, 4])) for i in kept]


class TemplateMatcher:
    def __init__(self, config: Dict[str, Any]):
        m_cfg = config.get("matching", {})
        self.confidence: float = m_cfg.get("confidence", 0.80)
        method_name: str = m_cfg.get("method", "TM_CCOEFF_NORMED")
        self.method = _METHOD_MAP.get(method_name, cv2.TM_CCOEFF_NORMED)
        self.grayscale: bool = m_cfg.get("grayscale", True)
        self.multi_scale: bool = m_cfg.get("multi_scale", True)
        scale_range = m_cfg.get("scale_range", [0.8, 1.2])
        self.scale_min: float = scale_range[0]
        self.scale_max: float = scale_range[1]
        self.scale_steps: int = m_cfg.get("scale_steps", 5)
        self.nms_overlap: float = m_cfg.get("nms_overlap", 0.5)

    def _to_gray(self, img: np.ndarray) -> np.ndarray:
        if self.grayscale:
            if len(img.shape) == 3:
                return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return img

    def _load_template(self, template: str | Path | np.ndarray) -> np.ndarray:
        if isinstance(template, np.ndarray):
            return template
        path = Path(template)
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        img = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Could not load template image: {path}")
        return img

    def find_best(self, screen: np.ndarray,
                  template: str | Path | np.ndarray,
                  confidence: Optional[float] = None,
                  region: Optional[Tuple[int, int, int, int]] = None
                  ) -> Optional[MatchResult]:
        results = self.find_all(screen, template, confidence=confidence,
                                region=region, max_results=1)
        return results[0] if results else None

    def find_all(self, screen: np.ndarray,
                 template: str | Path | np.ndarray,
                 confidence: Optional[float] = None,
                 region: Optional[Tuple[int, int, int, int]] = None,
                 max_results: int = 50) -> List[MatchResult]:
        min_conf = confidence if confidence is not None else self.confidence
        tmpl_raw = self._load_template(template)

        offset_x, offset_y = 0, 0
        if region:
            lx, ly, rw, rh = region
            screen = screen[ly:ly + rh, lx:lx + rw]
            offset_x, offset_y = lx, ly

        screen_gray = self._to_gray(screen)
        tmpl_gray = self._to_gray(tmpl_raw)
        tmpl_h, tmpl_w = tmpl_gray.shape[:2]

        if self.multi_scale:
            candidates = self._match_multiscale(screen_gray, tmpl_gray,
                                                tmpl_w, tmpl_h, min_conf)
        else:
            candidates = self._match_single(screen_gray, tmpl_gray,
                                            tmpl_w, tmpl_h, min_conf, scale=1.0)

        # Non-maximum suppression
        suppressed = _non_max_suppression(candidates, self.nms_overlap)

        results = []
        for (bx, by, bw, bh, conf) in suppressed[:max_results]:
            cx = offset_x + bx + bw // 2
            cy = offset_y + by + bh // 2
            results.append(MatchResult(x=cx, y=cy, width=bw, height=bh,
                                        confidence=conf))
        return results

    def _match_single(self, screen_gray: np.ndarray, tmpl_gray: np.ndarray,
                      orig_w: int, orig_h: int, min_conf: float,
                      scale: float) -> List[Tuple[int, int, int, int, float]]:
        sh, sw = screen_gray.shape[:2]
        scaled_w = int(orig_w * scale)
        scaled_h = int(orig_h * scale)
        if scaled_w > sw or scaled_h > sh or scaled_w < 1 or scaled_h < 1:
            return []

        if scale != 1.0:
            tmpl_s = cv2.resize(tmpl_gray, (scaled_w, scaled_h),
                                interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
        else:
            tmpl_s = tmpl_gray

        result = cv2.matchTemplate(screen_gray, tmpl_s, self.method)
        candidates = []

        # For SQDIFF methods, lower is better
        if self.method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            locs = np.where(result <= (1.0 - min_conf))
            for pt in zip(*locs[::-1]):
                conf = 1.0 - float(result[pt[1], pt[0]])
                candidates.append((pt[0], pt[1], scaled_w, scaled_h, conf))
        else:
            locs = np.where(result >= min_conf)
            for pt in zip(*locs[::-1]):
                conf = float(result[pt[1], pt[0]])
                candidates.append((pt[0], pt[1], scaled_w, scaled_h, conf))
        return candidates

    def _match_multiscale(self, screen_gray: np.ndarray, tmpl_gray: np.ndarray,
                          orig_w: int, orig_h: int,
                          min_conf: float) -> List[Tuple[int, int, int, int, float]]:
        scales = np.linspace(self.scale_min, self.scale_max, self.scale_steps)
        all_candidates: List[Tuple[int, int, int, int, float]] = []
        for scale in scales:
            all_candidates.extend(
                self._match_single(screen_gray, tmpl_gray, orig_w, orig_h,
                                   min_conf, scale=float(scale))
            )
        return all_candidates
