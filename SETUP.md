# Visual AutoClicker — Setup Guide

## Requirements

- Python 3.9+
- Windows 10/11 (also works on macOS/Linux with minor changes)
- Tesseract OCR installed separately (see below)

---

## 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

## 2. Install Tesseract OCR (required for OCR features)

### Windows
Download the installer from:  
https://github.com/UB-Mannheim/tesseract/wiki

Default install path: `C:\Program Files\Tesseract-OCR\tesseract.exe`

After installing, either:
- Add Tesseract to your system PATH, **or**
- Set the path in your script:

```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
```

### Indonesian/other language support
Download `ind.traineddata` from https://github.com/tesseract-ocr/tessdata  
and place it in `C:\Program Files\Tesseract-OCR\tessdata\`

Then set `lang: ind` in your config.

---

## 3. Project Structure

```
visual_autoclicker/
├── auto_clicker.py          # Main AutoClicker class (start here)
├── config/
│   ├── default.yaml         # All default settings
│   └── user_example.yaml    # Copy & customize
├── core/
│   ├── screen_capture.py    # mss-based screen capture
│   ├── template_matcher.py  # OpenCV template matching + NMS + multi-scale
│   └── ocr_engine.py        # Tesseract / EasyOCR wrapper
├── actions/
│   ├── mouse_actions.py     # click, scroll, drag, double-click
│   └── keyboard_actions.py  # type, hotkey, press
├── utils/
│   ├── config_loader.py     # YAML config loader with deep-merge
│   ├── logger.py            # Logging setup
│   └── debug_helper.py      # Annotated debug screenshots
├── templates/               # Put your .png template images here
└── debug_screenshots/       # Auto-saved failure screenshots
examples/
├── capture_template.py      # Tool to capture template screenshots
├── example_basic.py         # Basic usage
└── example_advanced.py      # Advanced: form fill, OCR, multi-find
```

---

## 4. Capture a template image

```bash
# Interactive (draw a rectangle on screen):
python examples/capture_template.py --name my_button

# From coordinates (x y width height):
python examples/capture_template.py --name search_icon --region 1200 50 30 30
```

---

## 5. Quick start

```python
from visual_autoclicker import AutoClicker, ElementNotFoundError

ac = AutoClicker()

# Click an image button
ac.click_image("visual_autoclicker/templates/my_button.png", confidence=0.80)

# Click text found via OCR
ac.click_text("Sign In")

# Type text
ac.type("hello world")
ac.press("enter")

# Scroll
ac.scroll(x=800, y=400, amount=5, direction="down")

# Wait for an element with timeout
try:
    ac.wait_for_image("templates/result.png", timeout=20)
except ElementNotFoundError:
    print("Element not found!")
```

---

## 6. Configuration

Copy `visual_autoclicker/config/user_example.yaml` to your project root and pass it:

```python
ac = AutoClicker(config_path="my_config.yaml")
```

Or pass overrides inline:

```python
ac = AutoClicker(config_overrides={
    "matching": {"confidence": 0.75},
    "debug": {"save_on_failure": True},
})
```

---

## 7. Key settings

| Setting | Default | Description |
|---|---|---|
| `matching.confidence` | `0.80` | Min template match score (0–1) |
| `matching.multi_scale` | `true` | Handles DPI/zoom differences |
| `ocr.engine` | `tesseract` | `tesseract` or `easyocr` |
| `retry.timeout` | `30.0` | Seconds before giving up |
| `retry.max_attempts` | `5` | Retries before timeout |
| `debug.save_on_failure` | `true` | Save screenshot when match fails |
| `actions.human_jitter` | `false` | Add random pixel offset to clicks |
| `failsafe.enabled` | `true` | Move mouse to top-left to abort |

---

## 8. Abort / failsafe

Move your mouse to the **top-left corner** of the screen at any time to abort the script (pyautogui failsafe). This is enabled by default.

---

## 9. Notes

- This tool uses **real screen pixels and OS-level mouse/keyboard events** — it works with any visible application, not just the browser DOM.
- Always comply with the Terms of Service of the applications you automate.
- Template images should be captured at the same display scaling (DPI) as the target machine. Use `multi_scale: true` to add tolerance.
