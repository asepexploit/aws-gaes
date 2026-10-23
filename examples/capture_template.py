"""
Capture template + test deteksi + auto tambah ke my_flow.py

Usage:
    python examples/capture_template.py --name step1-klik-google --step 1
    python examples/capture_template.py --name step2-isi-email --step 2
    python examples/capture_template.py --name step3-klik-submit --step 3
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import mss
import numpy as np
from PIL import Image

FLOW_FILE = Path("my_flow.py")
TEMPLATES_DIR = Path("visual_autoclicker/templates")

FLOW_HEADER = """\"""
Auto-generated flow. Edit sesuai kebutuhan.
Jalankan: python my_flow.py
\"""
import sys
import time

sys.path.insert(0, '.')
from visual_autoclicker import AutoClicker, ElementNotFoundError

ac = AutoClicker(config_overrides={
    "matching": {"confidence": 0.75},
    "retry": {"timeout": 20, "max_attempts": 5, "delay_between": 1.5},
    "debug": {"save_on_failure": True},
})

T = "visual_autoclicker/templates"


def step(n, msg):
    print(f"\\n{'='*50}")
    print(f"  STEP {n}: {msg}")
    print(f"{'='*50}")


try:
    pass  # steps ditambah otomatis

except ElementNotFoundError as e:
    print(f"\\n  [GAGAL] {e}")
    print("  Cek folder debug_screenshots/ untuk screenshot saat gagal")
"""


def capture_region_interactive():
    with mss.MSS() as sct:
        raw = sct.grab(sct.monitors[1])
    screen = np.array(Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX"))
    screen_bgr = screen[:, :, ::-1].copy()

    roi = cv2.selectROI("Gambar kotak di elemen → ENTER simpan, ESC batal",
                        screen_bgr, showCrosshair=True)
    cv2.destroyAllWindows()
    if roi[2] == 0 or roi[3] == 0:
        print("  Tidak ada seleksi.")
        return None
    x, y, w, h = roi
    return screen_bgr[y:y + h, x:x + w], (x, y, w, h)


def test_and_click(template_path: Path):
    from visual_autoclicker import AutoClicker, ElementNotFoundError

    ac = AutoClicker(config_overrides={
        "matching": {"confidence": 0.70},
        "retry": {"max_attempts": 1, "timeout": 5},
        "debug": {"save_on_failure": False},
        "logging": {"level": "WARNING"},
    })

    print("\n  🔍 Test deteksi...")
    try:
        result = ac.find_image(str(template_path), timeout=5)
        print(f"  ✓ KETEMU! Posisi: ({result.x}, {result.y})  Confidence: {result.confidence:.3f}")

        jawab = input("  Mau langsung diklik sekarang? (y/n): ").strip().lower()
        if jawab == "y":
            print("  🖱 Klik dalam 2 detik...")
            time.sleep(2)
            ac.click_image(str(template_path), timeout=5)
            print("  ✓ Klik berhasil!")
        return True
    except ElementNotFoundError:
        print("  ✗ Tidak terdeteksi sekarang (mungkin elemen belum muncul — tidak masalah)")
        return False


def build_step_code(step_num: int, name: str, template_path: str,
                    after_click_sleep: float = 1.5) -> str:
    label = name.replace("-", " ").replace("_", " ").title()
    return (
        f"\n    # {'='*54}\n"
        f"    # STEP {step_num} — {label}\n"
        f"    # {'='*54}\n"
        f"    step({step_num}, \"{label}\")\n"
        f"    ac.click_image(f\"{{T}}/{Path(template_path).name}\", timeout=20)\n"
        f"    print(\"  ✓ Selesai\")\n"
        f"    time.sleep({after_click_sleep})\n"
    )


def insert_step_into_flow(step_num: int, step_code: str):
    """Sisipkan step ke my_flow.py pada posisi yang benar."""

    # Buat file baru kalau belum ada
    if not FLOW_FILE.exists():
        FLOW_FILE.write_text(FLOW_HEADER, encoding="utf-8")
        print(f"  ✓ File baru dibuat: {FLOW_FILE}")

    content = FLOW_FILE.read_text(encoding="utf-8")

    # Cek apakah step ini sudah ada — kalau ada, replace
    pattern = rf"(    # [=]{{10,}}\n    # STEP {step_num} —.*?    time\.sleep\([^)]+\)\n)"
    if re.search(pattern, content, re.DOTALL):
        content = re.sub(pattern, step_code.lstrip("\n"), content, flags=re.DOTALL)
        print(f"  ✓ STEP {step_num} diperbarui di {FLOW_FILE}")
    else:
        # Sisipkan sebelum baris "except ElementNotFoundError"
        insert_before = "except ElementNotFoundError"
        if insert_before in content:
            content = content.replace(
                insert_before,
                step_code + "\n    " + insert_before
            )
        else:
            content += step_code
        print(f"  ✓ STEP {step_num} ditambahkan ke {FLOW_FILE}")

    # Hapus "    pass  # steps akan ditambah otomatis di bawah" kalau masih ada
    content = content.replace("    pass  # steps akan ditambah otomatis di bawah\n", "")

    FLOW_FILE.write_text(content, encoding="utf-8")


def show_current_flow():
    if not FLOW_FILE.exists():
        return
    content = FLOW_FILE.read_text(encoding="utf-8")
    steps = re.findall(r"# STEP (\d+) — (.+)", content)
    if steps:
        print("\n  📋 Flow saat ini:")
        for num, label in sorted(steps, key=lambda x: int(x[0])):
            print(f"     Step {num}: {label}")


def main():
    parser = argparse.ArgumentParser(description="Capture template + auto build flow")
    parser.add_argument("--name", required=True, help="Nama template (tanpa .png)")
    parser.add_argument("--step", type=int, required=True, help="Nomor step di flow")
    parser.add_argument("--sleep", type=float, default=1.5,
                        help="Jeda (detik) setelah klik step ini (default: 1.5)")
    parser.add_argument("--out-dir", default=str(TEMPLATES_DIR))
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.name}.png"

    print(f"\n📸 Capture template: {args.name}  (Step {args.step})")
    print("  Gambar kotak di sekitar elemen → ENTER untuk simpan\n")

    result = capture_region_interactive()
    if result is None:
        sys.exit(1)

    img, region_info = result
    cv2.imwrite(str(out_path), img)
    print(f"\n  ✓ Template disimpan: {out_path}")
    print(f"  ✓ Ukuran: {img.shape[1]}x{img.shape[0]} px")

    # Test deteksi & opsional klik
    test_and_click(out_path)

    print(f"\n  ▶ Jalankan flow: python my_flow.py\n")


if __name__ == "__main__":
    main()
