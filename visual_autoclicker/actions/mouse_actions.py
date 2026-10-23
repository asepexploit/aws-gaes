"""Mouse actions: click, double-click, right-click, drag, scroll."""
from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, Optional, Tuple

import pyautogui

logger = logging.getLogger("visual_autoclicker.mouse")

# pyautogui global failsafe: move mouse to top-left (0,0) to abort
pyautogui.FAILSAFE = True


class MouseController:
    def __init__(self, config: Dict[str, Any]):
        act_cfg = config.get("actions", {})
        self.click_delay: float = act_cfg.get("click_delay", 0.1)
        self.move_duration: float = act_cfg.get("move_duration", 0.3)
        self.human_jitter: bool = act_cfg.get("human_jitter", False)
        self.jitter_max: int = act_cfg.get("jitter_max_px", 3)
        failsafe_cfg = config.get("failsafe", {})
        pyautogui.FAILSAFE = failsafe_cfg.get("enabled", True)
        pyautogui.PAUSE = failsafe_cfg.get("pause", 0.05)

    def _apply_jitter(self, x: int, y: int) -> Tuple[int, int]:
        if self.human_jitter and self.jitter_max > 0:
            x += random.randint(-self.jitter_max, self.jitter_max)
            y += random.randint(-self.jitter_max, self.jitter_max)
        return x, y

    def move_to(self, x: int, y: int, duration: Optional[float] = None) -> None:
        dur = duration if duration is not None else self.move_duration
        fx, fy = self._apply_jitter(x, y)
        logger.debug("Move to (%d, %d) duration=%.2fs", fx, fy, dur)
        pyautogui.moveTo(fx, fy, duration=dur)

    def click(self, x: int, y: int, button: str = "left",
              duration: Optional[float] = None) -> None:
        dur = duration if duration is not None else self.move_duration
        fx, fy = self._apply_jitter(x, y)
        logger.info("Click %s at (%d, %d)", button, fx, fy)
        pyautogui.moveTo(fx, fy, duration=dur)
        time.sleep(1.0)
        pyautogui.click(button=button)
        time.sleep(self.click_delay)

    def double_click(self, x: int, y: int,
                     duration: Optional[float] = None) -> None:
        dur = duration if duration is not None else self.move_duration
        fx, fy = self._apply_jitter(x, y)
        logger.info("Double-click at (%d, %d)", fx, fy)
        pyautogui.doubleClick(fx, fy, duration=dur)
        time.sleep(self.click_delay)

    def right_click(self, x: int, y: int,
                    duration: Optional[float] = None) -> None:
        self.click(x, y, button="right", duration=duration)

    def drag_to(self, start_x: int, start_y: int,
                end_x: int, end_y: int,
                duration: float = 0.5, button: str = "left") -> None:
        logger.info("Drag (%d,%d) -> (%d,%d)", start_x, start_y, end_x, end_y)
        pyautogui.mouseDown(start_x, start_y, button=button)
        time.sleep(0.05)
        pyautogui.moveTo(end_x, end_y, duration=duration)
        time.sleep(0.05)
        pyautogui.mouseUp(button=button)
        time.sleep(self.click_delay)

    def scroll(self, x: int, y: int, amount: int,
               direction: str = "down") -> None:
        """Scroll at position. direction: 'up' or 'down'. amount: scroll units."""
        sign = -1 if direction == "down" else 1
        logger.info("Scroll %s x%d at (%d,%d)", direction, amount, x, y)
        pyautogui.scroll(sign * amount, x=x, y=y)
        time.sleep(self.click_delay)

    def get_position(self) -> Tuple[int, int]:
        pos = pyautogui.position()
        return pos.x, pos.y
