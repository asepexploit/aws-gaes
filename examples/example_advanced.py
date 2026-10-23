"""
Advanced example: form fill workflow with retry, OCR, custom config overrides.

Use-case: fill out a login form in Chrome using visual detection only.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from visual_autoclicker import AutoClicker, ElementNotFoundError

# Override specific config values at runtime (no YAML file needed for this)
overrides = {
    "matching": {"confidence": 0.75},   # slightly more lenient
    "retry": {"max_attempts": 8, "timeout": 45.0},
    "debug": {"save_screenshots": True, "save_on_failure": True},
    "actions": {"human_jitter": True, "jitter_max_px": 2},
}

ac = AutoClicker(config_overrides=overrides)

TEMPLATES = Path("visual_autoclicker/templates")


def login_flow(username: str, password: str):
    print("=== Starting login flow ===")

    # 1. Wait for the login form to appear
    print("Waiting for email field...")
    ac.wait_for_image(TEMPLATES / "email_field.png", timeout=20)

    # 2. Click the username/email field
    ac.click_image(TEMPLATES / "email_field.png")
    time.sleep(0.3)
    ac.hotkey("ctrl", "a")       # select all existing text
    ac.type(username)

    # 3. Click password field via tab key (faster than image search)
    ac.press("tab")
    time.sleep(0.2)
    ac.type(password)

    # 4. Click the Submit/Login button (try image first, fall back to OCR text)
    try:
        ac.click_image(TEMPLATES / "login_button.png", timeout=5)
    except ElementNotFoundError:
        print("Image match failed, trying OCR for 'Login' text...")
        ac.click_text("Login", timeout=10)

    # 5. Wait for dashboard / home page indicator to confirm success
    print("Waiting for post-login dashboard element...")
    try:
        ac.wait_for_image(TEMPLATES / "dashboard_logo.png", timeout=30)
        print("Login successful!")
    except ElementNotFoundError:
        print("Dashboard not found — login may have failed.")
        screen = ac.screenshot(save_path="debug_screenshots/login_fail.png")
        print("Saved debug screenshot: debug_screenshots/login_fail.png")


def find_all_buttons():
    """Demo: find all instances of a button template on screen."""
    print("\n=== Finding all instances of 'add_button.png' ===")
    results = ac.find_all_images(TEMPLATES / "add_button.png", confidence=0.70)
    if results:
        for i, r in enumerate(results):
            print(f"  Button #{i+1}: center=({r.x},{r.y}) conf={r.confidence:.3f}")
    else:
        print("No buttons found.")


def check_visibility():
    """Demo: conditional logic based on element visibility."""
    print("\n=== Checking element visibility ===")

    if ac.is_image_visible(TEMPLATES / "popup_close.png", confidence=0.80):
        print("Popup detected — closing it.")
        ac.click_image(TEMPLATES / "popup_close.png")
    else:
        print("No popup found, proceeding.")

    if ac.is_text_visible("Cookie"):
        print("Cookie banner visible — dismissing.")
        ac.click_text("Accept")


if __name__ == "__main__":
    # Replace with actual credentials (use env vars in production)
    login_flow("user@example.com", "mypassword123")
    check_visibility()
    find_all_buttons()
