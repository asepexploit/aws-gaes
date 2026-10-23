"""
Flow: Auto signup AWS Free Trial

Usage:
  python my_flow.py                  → jalankan semua step
  python my_flow.py --step 3         → step 3 saja
  python my_flow.py --step 3 --end 5 → step 3 sampai 5
"""
import sys
import argparse
import time
import urllib.parse
import urllib.request
import json
import re
import random

sys.path.insert(0, '.')
from visual_autoclicker import AutoClicker, ElementNotFoundError

# ─── Parse argumen ────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--step", type=int, default=1,  help="Mulai dari step ini")
parser.add_argument("--end",  type=int, default=99, help="Berhenti setelah step ini")
args = parser.parse_args()

START = args.step
END   = args.end
print(f"\n▶ Menjalankan step {START} {'saja' if END == START else f'sampai {END}'}")

# ─── Config ───────────────────────────────────────────────
PANEL_URL     = "https://api.lpmterkam.org/"
DEVICE_SECRET = "4e427c6afcd3267d370d96294b3d6411ffc5ed198dc995e40934ec6b73e32cc5"
AWS_PASSWORD  = "Abgteam123@"
OTP_INTERVAL  = 5
OTP_TIMEOUT   = 80
T             = "visual_autoclicker/templates"

ac = AutoClicker(config_overrides={
    "matching": {"confidence": 0.75},
    "retry": {"timeout": 25, "max_attempts": 5, "delay_between": 2.0},
    "debug": {"save_on_failure": True},
})


# ─── Helpers ──────────────────────────────────────────────
def should_run(n: int) -> bool:
    return START <= n <= END


def step(n, msg):
    print(f"\n{'='*52}")
    print(f"  STEP {n}: {msg}")
    print(f"{'='*52}")


def random_name() -> str:
    first = ["James","John","Robert","Michael","William","David","Richard","Joseph",
             "Thomas","Charles","Emily","Emma","Olivia","Ava","Sophia","Isabella",
             "Mia","Charlotte","Amelia","Harper"]
    last  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis",
             "Wilson","Taylor","Anderson","Thomas","Jackson","White","Harris","Martin"]
    return f"{random.choice(first)} {random.choice(last)}"


def _api(action: str, params: dict = {}) -> dict:
    base = PANEL_URL.rstrip("/")
    qp   = {"action": action, **params}
    url  = f"{base}/api/ext/tempmail.php?{urllib.parse.urlencode(qp)}"
    req  = urllib.request.Request(url, headers={
        "X-Device-Secret": DEVICE_SECRET,
        "User-Agent": "Mozilla/5.0",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "API error"))
    return data


def create_email() -> dict:
    return _api("quick_email")


def poll_otp(email: str, token: str, ts: str) -> str | None:
    print("  ⏳ Menunggu OTP di inbox...")
    elapsed = 0
    while elapsed < OTP_TIMEOUT:
        time.sleep(OTP_INTERVAL)
        elapsed += OTP_INTERVAL
        try:
            data = _api("poll_otp", {"email": email, "account_token": token, "ts": ts})
            if data.get("found"):
                return data["otp"]
        except Exception:
            pass
        try:
            msgs = _api("inbox", {"email": email, "account_token": token, "ts": ts})
            for msg in msgs.get("messages", []):
                txt = msg.get("subject", "") + " " + msg.get("body_preview", "")
                m = re.search(r"\b(\d{6})\b", txt)
                if m:
                    return m.group(1)
        except Exception:
            pass
        print(f"  ... {elapsed}s/{OTP_TIMEOUT}s")
    return None


# ─── FLOW ─────────────────────────────────────────────────
try:
    EMAIL = EMAIL_TOKEN = EMAIL_TS = ""
    NAME  = random_name()

    if should_run(3):
        print("\n📧 Generate email tempmail...")
        email_data  = create_email()
        EMAIL       = email_data["email"]
        EMAIL_TOKEN = email_data.get("account_token", "")
        EMAIL_TS    = email_data.get("ts", "")
        print(f"  ✓ Email : {EMAIL}")
        print(f"  ✓ Nama  : {NAME}")

    # ══════════════════════════════════════════════════════
    # STEP 1 — Klik hasil Google Search AWS
    # ══════════════════════════════════════════════════════
    if should_run(1):
        step(1, "Klik hasil Google 'Get AWS Free Trial Account'")
        ac.click_image(f"{T}/step1-klik-google-search-aws.png", timeout=20)
        print("  ✓ Selesai")
        time.sleep(3)

    # ══════════════════════════════════════════════════════
    # STEP 2 — Klik tombol Buat Akun
    # ══════════════════════════════════════════════════════
    if should_run(2):
        step(2, "Klik tombol 'Buat akun'")
        ac.click_image(f"{T}/step2-klik-buat-akun.png", timeout=20)
        print("  ✓ Selesai")
        time.sleep(3)

    # ══════════════════════════════════════════════════════
    # STEP 3 — Klik field Email lalu isi dengan tempmail
    # ══════════════════════════════════════════════════════
    if should_run(3):
        step(3, f"Isi email: {EMAIL}")
        ac.click_image(f"{T}/3.png", timeout=15)
        time.sleep(0.4)
        ac.hotkey("ctrl", "a")
        ac.type(EMAIL)
        print(f"  ✓ Email diisi: {EMAIL}")
        time.sleep(0.5)

    # ══════════════════════════════════════════════════════
    # STEP 4 — Klik tombol Continue
    # ══════════════════════════════════════════════════════
    if should_run(4):
        step(4, "Klik tombol Continue")
        ac.click_image(f"{T}/4.png", timeout=15)
        print("  ✓ Selesai")
        time.sleep(3)

    # ══════════════════════════════════════════════════════
    # STEP 5 — Isi nama random
    # ══════════════════════════════════════════════════════
    if should_run(5):
        step(5, f"Isi nama: {NAME}")
        ac.click_image(f"{T}/5.png", timeout=15)
        time.sleep(0.4)
        ac.hotkey("ctrl", "a")
        ac.type(NAME)
        print(f"  ✓ Nama diisi: {NAME}")
        time.sleep(0.5)

    # ══════════════════════════════════════════════════════
    # STEP 6 — (capture dulu, lalu uncomment)
    # ══════════════════════════════════════════════════════
    if should_run(6):
        step(6, "Step 6")
        ac.click_image(f"{T}/6.png", timeout=15)
        print("  ✓ Selesai")
        time.sleep(1.5)

    # ══════════════════════════════════════════════════════
    # STEP 7 — OTP dari inbox tempmail
    # ══════════════════════════════════════════════════════
    if should_run(7):
        step(7, "Ambil OTP dari inbox tempmail")
        otp = poll_otp(EMAIL, EMAIL_TOKEN, EMAIL_TS)
        if not otp:
            raise ElementNotFoundError("OTP tidak datang dalam 80 detik")
        print(f"  ✓ OTP diterima: {otp}")
        ac.click_image(f"{T}/7-otp-field.png", timeout=15)
        time.sleep(0.3)
        ac.hotkey("ctrl", "a")
        ac.type(otp)
        time.sleep(0.5)
        ac.click_text("Verify", timeout=10)
        print("  ✓ OTP disubmit")
        time.sleep(3)

    # ══════════════════════════════════════════════════════
    print(f"\n{'='*52}")
    print("  SELESAI ✓")
    if EMAIL:
        print(f"  Email    : {EMAIL}")
        print(f"  Nama     : {NAME}")
        print(f"  Password : {AWS_PASSWORD}")
    print(f"{'='*52}")

except ElementNotFoundError as e:
    print(f"\n  [GAGAL] {e}")
    print("  Cek folder debug_screenshots/ untuk screenshot saat gagal")
except Exception as e:
    print(f"\n  [ERROR] {e}")
