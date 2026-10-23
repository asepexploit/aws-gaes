"""
AutoClicker — main orchestrator.

Usage:
    from visual_autoclicker import AutoClicker

    ac = AutoClicker()
    ac.click_image("templates/button.png")
    ac.click_text("Submit")
    ac.type("hello world")
"""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

from .actions.keyboard_actions import KeyboardController
from .actions.mouse_actions import MouseController
from .core.ocr_engine import OcrEngine, OcrResult
from .core.screen_capture import ScreenCapture, ScreenRegion
from .core.template_matcher import MatchResult, TemplateMatcher
from .utils.config_loader import load_config
from .utils.debug_helper import DebugHelper
from .utils.logger import setup_logger

logger = logging.getLogger("visual_autoclicker")


class ElementNotFoundError(Exception):
    """Raised when a visual element cannot be located within timeout."""


class AutoClicker:
    """
    High-level API for visual desktop automation.

    All find/click operations support retry and timeout automatically.
    """

    def __init__(self, config_path: Optional[str | Path] = None,
                 config_overrides: Optional[Dict[str, Any]] = None):
        self.config = load_config(config_path)
        if config_overrides:
            self._apply_overrides(config_overrides)

        setup_logger(self.config)

        self.capture = ScreenCapture(self.config)
        self.matcher = TemplateMatcher(self.config)
        self.ocr = OcrEngine(self.config)
        self.mouse = MouseController(self.config)
        self.keyboard = KeyboardController(self.config)
        self.debug = DebugHelper(self.config)

        retry_cfg = self.config.get("retry", {})
        self._max_attempts: int = retry_cfg.get("max_attempts", 5)
        self._retry_delay: float = retry_cfg.get("delay_between", 1.0)
        self._timeout: float = retry_cfg.get("timeout", 30.0)

        logger.info("AutoClicker initialized (engine=%s, confidence=%.2f)",
                    self.config.get("ocr", {}).get("engine", "tesseract"),
                    self.config.get("matching", {}).get("confidence", 0.80))

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def find_image(self, template: str | Path | np.ndarray,
                   confidence: Optional[float] = None,
                   region: Optional[Tuple[int, int, int, int]] = None,
                   timeout: Optional[float] = None,
                   max_attempts: Optional[int] = None) -> MatchResult:
        """
        Find a template image on screen. Retries until found or timeout.
        Returns MatchResult with screen coordinates of the match center.
        Raises ElementNotFoundError on failure.
        """
        return self._retry_find(
            self._do_find_image,
            args=(template, confidence, region),
            label=str(template),
            timeout=timeout,
            max_attempts=max_attempts,
        )

    def find_all_images(self, template: str | Path | np.ndarray,
                        confidence: Optional[float] = None,
                        region: Optional[Tuple[int, int, int, int]] = None,
                        max_results: int = 50) -> List[MatchResult]:
        """Find all occurrences of a template. Returns empty list if none found."""
        screen = self.capture.capture()
        results = self.matcher.find_all(screen, template,
                                        confidence=confidence,
                                        region=region,
                                        max_results=max_results)
        self.debug.save_match_attempt(screen, str(template), results, bool(results))
        return results

    def click_image(self, template: str | Path | np.ndarray,
                    button: str = "left",
                    confidence: Optional[float] = None,
                    region: Optional[Tuple[int, int, int, int]] = None,
                    timeout: Optional[float] = None,
                    offset: Tuple[int, int] = (0, 0)) -> MatchResult:
        """Find image and click its center."""
        result = self.find_image(template, confidence=confidence,
                                 region=region, timeout=timeout)
        x = result.x + offset[0]
        y = result.y + offset[1]
        self.mouse.click(x, y, button=button)
        logger.info("Clicked image '%s' at (%d, %d) confidence=%.3f",
                    template, x, y, result.confidence)
        return result

    def double_click_image(self, template: str | Path | np.ndarray,
                           confidence: Optional[float] = None,
                           timeout: Optional[float] = None) -> MatchResult:
        result = self.find_image(template, confidence=confidence, timeout=timeout)
        self.mouse.double_click(result.x, result.y)
        return result

    def find_text(self, text: str,
                  region: Optional[Tuple[int, int, int, int]] = None,
                  timeout: Optional[float] = None,
                  max_attempts: Optional[int] = None,
                  case_sensitive: bool = False) -> OcrResult:
        """Find text on screen via OCR. Returns OcrResult with screen coordinates."""
        return self._retry_find(
            self._do_find_text,
            args=(text, region, case_sensitive),
            label=f'text:"{text}"',
            timeout=timeout,
            max_attempts=max_attempts,
        )

    def click_text(self, text: str,
                   button: str = "left",
                   region: Optional[Tuple[int, int, int, int]] = None,
                   timeout: Optional[float] = None,
                   offset: Tuple[int, int] = (0, 0)) -> OcrResult:
        """Find text via OCR and click it."""
        result = self.find_text(text, region=region, timeout=timeout)
        x = result.center[0] + offset[0]
        y = result.center[1] + offset[1]
        self.mouse.click(x, y, button=button)
        logger.info("Clicked text '%s' at (%d, %d) confidence=%.3f",
                    text, x, y, result.confidence)
        return result

    def type(self, text: str, use_clipboard: bool = False) -> None:
        """Type text using keyboard simulation."""
        if use_clipboard:
            self.keyboard.type_text_clipboard(text)
        else:
            self.keyboard.type_text(text)

    def hotkey(self, *keys: str) -> None:
        self.keyboard.hotkey(*keys)

    def press(self, key: str) -> None:
        self.keyboard.press(key)

    def scroll(self, x: int, y: int, amount: int = 3,
               direction: str = "down") -> None:
        self.mouse.scroll(x, y, amount=amount, direction=direction)

    def scroll_at_image(self, template: str | Path | np.ndarray,
                        amount: int = 3, direction: str = "down",
                        timeout: Optional[float] = None) -> None:
        result = self.find_image(template, timeout=timeout)
        self.mouse.scroll(result.x, result.y, amount=amount, direction=direction)

    def wait_for_image(self, template: str | Path | np.ndarray,
                       confidence: Optional[float] = None,
                       timeout: Optional[float] = None) -> MatchResult:
        """Block until image appears."""
        return self.find_image(template, confidence=confidence, timeout=timeout)

    def wait_for_image_to_disappear(self, template: str | Path | np.ndarray,
                                     confidence: Optional[float] = None,
                                     timeout: Optional[float] = None) -> bool:
        """Block until image disappears from screen."""
        deadline = time.time() + (timeout or self._timeout)
        while time.time() < deadline:
            screen = self.capture.capture()
            result = self.matcher.find_best(screen, template, confidence=confidence)
            if result is None:
                logger.info("Image '%s' disappeared from screen", template)
                return True
            time.sleep(self._retry_delay)
        logger.warning("Image '%s' still visible after %.1fs", template,
                       timeout or self._timeout)
        return False

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None,
                   save_path: Optional[str | Path] = None) -> np.ndarray:
        """Capture current screen (or region). Optionally save to file."""
        r = ScreenRegion(*region) if region else None
        img = self.capture.capture(region=r)
        if save_path:
            import cv2
            cv2.imwrite(str(save_path), img)
            logger.info("Screenshot saved: %s", save_path)
        return img

    def is_image_visible(self, template: str | Path | np.ndarray,
                         confidence: Optional[float] = None) -> bool:
        screen = self.capture.capture()
        result = self.matcher.find_best(screen, template, confidence=confidence)
        return result is not None

    def is_text_visible(self, text: str,
                        region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        screen = self.capture.capture()
        if region:
            lx, ly, rw, rh = region
            screen = screen[ly:ly + rh, lx:lx + rw]
        results = self.ocr.find_text(screen, text)
        return len(results) > 0

    def set_confidence(self, value: float) -> None:
        """Dynamically adjust match confidence threshold."""
        self.matcher.confidence = value
        logger.info("Confidence threshold set to %.2f", value)

    def set_timeout(self, value: float) -> None:
        self._timeout = value

    # -------------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------------

    def _do_find_image(self, template, confidence, region) -> Optional[MatchResult]:
        screen = self.capture.capture()
        result = self.matcher.find_best(screen, template,
                                        confidence=confidence,
                                        region=region)
        self.debug.save_match_attempt(screen, str(template),
                                      [result] if result else None,
                                      result is not None)
        return result

    def _do_find_text(self, text, region, case_sensitive) -> Optional[OcrResult]:
        screen = self.capture.capture()
        crop = screen
        offset_x, offset_y = 0, 0
        if region:
            lx, ly, rw, rh = region
            crop = screen[ly:ly + rh, lx:lx + rw]
            offset_x, offset_y = lx, ly

        results = self.ocr.find_text(crop, text, case_sensitive=case_sensitive)
        success = len(results) > 0

        if success and (offset_x or offset_y):
            # adjust bbox back to full-screen coordinates
            adjusted = []
            for r in results:
                l, t, w, h = r.bbox
                from .core.ocr_engine import OcrResult as OR
                adjusted.append(OR(text=r.text, confidence=r.confidence,
                                   bbox=(l + offset_x, t + offset_y, w, h)))
            results = adjusted

        self.debug.save_ocr_attempt(screen, text, results if success else None,
                                    success)
        return results[0] if success else None

    def _retry_find(self, fn, args: tuple, label: str,
                    timeout: Optional[float],
                    max_attempts: Optional[int]) -> Any:
        deadline = time.time() + (timeout or self._timeout)
        attempts = max_attempts or self._max_attempts
        last_exc = None

        for attempt in range(1, attempts + 1):
            if time.time() > deadline:
                break
            result = fn(*args)
            if result is not None:
                logger.debug("Found '%s' on attempt %d", label, attempt)
                return result
            logger.debug("Attempt %d/%d — '%s' not found, retrying in %.1fs",
                         attempt, attempts, label, self._retry_delay)
            remaining = deadline - time.time()
            sleep_for = min(self._retry_delay, max(0, remaining))
            if sleep_for > 0:
                time.sleep(sleep_for)

        raise ElementNotFoundError(
            f"Could not find '{label}' after {attempts} attempts "
            f"(timeout={timeout or self._timeout}s)"
        )

    def _apply_overrides(self, overrides: Dict[str, Any]) -> None:
        from .utils.config_loader import _deep_merge
        self.config = _deep_merge(self.config, overrides)
