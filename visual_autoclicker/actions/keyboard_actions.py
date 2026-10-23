"""Keyboard actions: type text, hotkeys, key press/release."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Union

import pyautogui

logger = logging.getLogger("visual_autoclicker.keyboard")


class KeyboardController:
    def __init__(self, config: Dict[str, Any]):
        act_cfg = config.get("actions", {})
        self.type_interval: float = act_cfg.get("type_interval", 0.05)

    def type_text(self, text: str, interval: float | None = None) -> None:
        """Type a string character by character."""
        iv = interval if interval is not None else self.type_interval
        logger.info("Typing text (length=%d)", len(text))
        pyautogui.typewrite(text, interval=iv)

    def type_text_clipboard(self, text: str) -> None:
        """Paste text via clipboard — faster for long strings, bypasses typewrite encoding issues."""
        import subprocess
        try:
            import pyperclip
            pyperclip.copy(text)
            logger.info("Pasting text via clipboard (length=%d)", len(text))
            self.hotkey("ctrl", "v")
        except ImportError:
            logger.warning("pyperclip not installed; falling back to typewrite")
            self.type_text(text)

    def press(self, key: str) -> None:
        """Press and release a single key."""
        logger.debug("Key press: %s", key)
        pyautogui.press(key)

    def key_down(self, key: str) -> None:
        logger.debug("Key down: %s", key)
        pyautogui.keyDown(key)

    def key_up(self, key: str) -> None:
        logger.debug("Key up: %s", key)
        pyautogui.keyUp(key)

    def hotkey(self, *keys: str) -> None:
        """Press a combination of keys simultaneously."""
        logger.info("Hotkey: %s", "+".join(keys))
        pyautogui.hotkey(*keys)
        time.sleep(0.05)

    def press_enter(self) -> None:
        self.press("enter")

    def press_tab(self) -> None:
        self.press("tab")

    def press_escape(self) -> None:
        self.press("escape")

    def press_sequence(self, keys: List[str], delay: float = 0.1) -> None:
        """Press keys in sequence with optional delay."""
        for key in keys:
            self.press(key)
            time.sleep(delay)
