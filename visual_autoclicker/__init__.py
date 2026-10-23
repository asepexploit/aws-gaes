"""Visual AutoClicker — visual desktop automation package."""
from .auto_clicker import AutoClicker, ElementNotFoundError
from .core.template_matcher import MatchResult
from .core.ocr_engine import OcrResult
from .core.screen_capture import ScreenRegion

__all__ = ["AutoClicker", "ElementNotFoundError", "MatchResult", "OcrResult", "ScreenRegion"]
__version__ = "1.0.0"
