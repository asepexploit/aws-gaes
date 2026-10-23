"""
Basic example: find and click an image button, then type text.

Steps:
1. Take a screenshot of the button you want to click.
2. Save it to visual_autoclicker/templates/my_button.png
3. Run this script while Chrome is open.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from visual_autoclicker import AutoClicker, ElementNotFoundError

# Initialize — uses default config
ac = AutoClicker()

try:
    # --- Example 1: Click an image template ---
    print("Looking for 'search_button.png' on screen...")
    result = ac.click_image(
        "visual_autoclicker/templates/search_button.png",
        confidence=0.80,
        timeout=15,
    )
    print(f"Clicked at ({result.x}, {result.y}) with confidence {result.confidence:.3f}")

    # --- Example 2: Type into the focused field ---
    ac.type("hello world")
    ac.press("enter")

    # --- Example 3: Click text found via OCR ---
    print("Looking for 'Sign In' text on screen via OCR...")
    ocr_result = ac.click_text("Sign In", timeout=10)
    print(f"Clicked OCR text at {ocr_result.center}")

    # --- Example 4: Scroll down on an element ---
    ac.scroll(x=800, y=400, amount=5, direction="down")

except ElementNotFoundError as e:
    print(f"ERROR: {e}")
    print("Make sure to add template images to visual_autoclicker/templates/")
