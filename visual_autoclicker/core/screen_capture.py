"""Fast screen capture using mss, with PIL/numpy conversion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import mss
import numpy as np
from PIL import Image


@dataclass
class ScreenRegion:
    left: int
    top: int
    width: int
    height: int

    def to_mss_monitor(self) -> dict:
        return {"left": self.left, "top": self.top,
                "width": self.width, "height": self.height}

    @classmethod
    def full_screen(cls, monitor_idx: int = 1) -> "ScreenRegion":
        with mss.MSS() as sct:
            mon = sct.monitors[monitor_idx]
            return cls(mon["left"], mon["top"], mon["width"], mon["height"])


class ScreenCapture:
    """Thread-safe screen capture via mss."""

    def __init__(self, config: Dict[str, Any]):
        cap_cfg = config.get("capture", {})
        self._monitor_idx: int = cap_cfg.get("monitor", 1)
        region_cfg = cap_cfg.get("region")  # [left, top, w, h] or null
        if region_cfg:
            self._region = ScreenRegion(*region_cfg)
        else:
            self._region: Optional[ScreenRegion] = None

    def capture(self, region: Optional[ScreenRegion] = None) -> np.ndarray:
        """Returns BGR numpy array (OpenCV format)."""
        target = region or self._region
        with mss.MSS() as sct:
            if target:
                monitor = target.to_mss_monitor()
            else:
                monitor = sct.monitors[self._monitor_idx]
            raw = sct.grab(monitor)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return np.array(img)  # BGR numpy array

    def capture_pil(self, region: Optional[ScreenRegion] = None) -> Image.Image:
        """Returns PIL Image (RGB)."""
        bgr = self.capture(region)
        return Image.fromarray(bgr[:, :, ::-1])  # BGR -> RGB

    def get_screen_size(self) -> Tuple[int, int]:
        with mss.MSS() as sct:
            mon = sct.monitors[self._monitor_idx]
            return mon["width"], mon["height"]
