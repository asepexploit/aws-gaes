"""
Flow runner — baca flow.txt dan jalankan otomatis.

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
parser.add_argument("--step",      type=int, default=1)
parser.add_argument("--end",       type=int, default=99)
parser.add_argument("--flow",      default="flow.txt")
parser.add_argument("--skipemail", action="store_true", help="Skip generate email, pakai dummy")
parser.add_argument("--email",     default="example@gmail.com", help="Email dummy saat --skipemail")
parser.add_argument("--otp",       default="123123",            help="OTP dummy saat --skipemail")
args = parser.parse_args()

START = args.step
END   = args.end

# ─── Config ───────────────────────────────────────────────
PANEL_URL     = "https://api.lpmterkam.org/"
DEVICE_SECRET = "4e427c6afcd3267d370d96294b3d6411ffc5ed198dc995e40934ec6b73e32cc5"
PASSWORD      = "Abgteam123@"
OTP_INTERVAL  = 8
OTP_TIMEOUT   = 180
T             = "visual_autoclicker/templates"

ac = AutoClicker(config_overrides={
    "matching": {"confidence": 0.75},
    "retry": {"timeout": 25, "max_attempts": 5, "delay_between": 2.0},
    "debug": {"save_on_failure": True},
})


# ─── Helpers ──────────────────────────────────────────────
def random_name() -> str:
    first = ["James","John","Robert","Michael","William","David","Richard",
             "Emily","Emma","Olivia","Sophia","Charlotte","Amelia","Harper"]
    last  = ["Smith","Johnson","Williams","Brown","Jones","Garcia","Miller",
             "Davis","Wilson","Taylor","Anderson","Jackson","White","Harris"]
    return f"{random.choice(first)} {random.choice(last)}"


def _api(action: str, params: dict = {}, retries: int = 5) -> dict:
    base = PANEL_URL.rstrip("/")
    qp   = {"action": action, **params}
    url  = f"{base}/api/ext/tempmail.php?{urllib.parse.urlencode(qp)}"
    req  = urllib.request.Request(url, headers={
        "X-Device-Secret": DEVICE_SECRET,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    })
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.loads(r.read())
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "API error"))
            return data
        except Exception as e:
            last_err = e
            print(f"  ⚠ API error (attempt {attempt}/{retries}): {e}")
            if attempt < retries:
                time.sleep(3 * attempt)
    raise RuntimeError(f"API gagal setelah {retries} percobaan: {last_err}")


def create_email() -> dict:
    return _api("quick_email")


def poll_otp(email, token, ts) -> str | None:
    print("  ⏳ Menunggu OTP...")
    elapsed = 0
    while elapsed < OTP_TIMEOUT:
        time.sleep(OTP_INTERVAL)
        elapsed += OTP_INTERVAL
        try:
            d = _api("poll_otp", {"email": email, "account_token": token, "ts": ts})
            if d.get("found"):
                return d["otp"]
        except Exception:
            pass
        try:
            msgs = _api("inbox", {"email": email, "account_token": token, "ts": ts})
            for msg in msgs.get("messages", []):
                txt = msg.get("subject","") + " " + msg.get("body_preview","")
                m = re.search(r"\b(\d{6})\b", txt)
                if m:
                    return m.group(1)
        except Exception:
            pass
        print(f"  ... {elapsed}s/{OTP_TIMEOUT}s")
    return None


def parse_variables(path: str = "variables.txt") -> dict:
    vars_ = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    vars_[k.strip().upper()] = v.strip()
    except FileNotFoundError:
        pass
    return vars_


def parse_flow(path: str) -> list:
    steps = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("->")]
            if len(parts) < 3:
                continue
            action = parts[2]
            # Format 4 bagian: input:BEBAS -> nilai bebas
            if len(parts) == 4 and action.lower() == "input:bebas":
                action = f"input:{parts[3]}"
            steps.append({
                "num":      int(parts[0]),
                "template": parts[1],
                "action":   action,
            })
    return sorted(steps, key=lambda x: x["num"])


# ─── MAIN ─────────────────────────────────────────────────
try:
    steps = parse_flow(args.flow)
    VARS  = parse_variables()
    print(f"\n▶ Flow: {args.flow}  ({len(steps)} steps)")
    print(f"▶ Jalankan step {START} {'saja' if END == START else f'sampai {END}'}\n")

    # Generate email kalau ada aksi yang butuh
    EMAIL = EMAIL_TOKEN = EMAIL_TS = ""
    NAMA  = random_name()
    needs_email = any(
        s["action"].upper() in ("INPUT:EMAIL", "OTP")
        for s in steps if START <= s["num"] <= END
    )
    if args.skipemail:
        EMAIL = input("  Masukkan email: ").strip()
        print(f"  ✓ Email : {EMAIL}")
    elif needs_email:
        print("📧 Generate email tempmail...")
        d           = create_email()
        EMAIL       = d["email"]
        EMAIL_TOKEN = d.get("account_token", "")
        EMAIL_TS    = d.get("ts", "")
        print(f"  ✓ Email : {EMAIL}")
        print(f"  ✓ Nama  : {NAMA}")

    for s in steps:
        n        = s["num"]
        template = s["template"]
        action   = s["action"]

        if not (START <= n <= END):
            continue

        # ── sleep tanpa template ──
        if action.lower().startswith("sleep:"):
            secs = float(action.split(":")[1])
            print(f"\n  [STEP {n}] Tunggu {secs}s...")
            time.sleep(secs)
            continue

        print(f"\n{'='*52}")
        print(f"  STEP {n}: {template} → {action}")
        print(f"{'='*52}")

        tmpl_path = f"{T}/{template}.png"
        act_lower = action.lower()

        # ── klik saja ──
        if act_lower in ("klik", "continue", "click"):
            ac.click_image(tmpl_path, timeout=20)
            print("  ✓ Klik selesai")
            time.sleep(1.5)

        # ── input teks biasa ──
        elif act_lower.startswith("input:"):
            nilai = action.split(":", 1)[1]
            key   = nilai.upper()
            if key == "EMAIL":
                nilai = EMAIL
            elif key == "NAMA":
                nilai = NAMA
            elif key == "PASSWORD":
                nilai = PASSWORD
            elif key in VARS:
                nilai = VARS[key]
            ac.click_image(tmpl_path, timeout=15)
            time.sleep(0.3)
            ac.hotkey("ctrl", "a")
            ac.type(nilai)
            print(f"  ✓ Input: {nilai}")
            time.sleep(0.5)

        # ── OTP ──
        elif act_lower == "otp":
            if args.skipemail:
                otp = input("  Masukkan OTP yang diterima di email: ").strip()
                print(f"  ✓ OTP : {otp}")
            else:
                otp = poll_otp(EMAIL, EMAIL_TOKEN, EMAIL_TS)
                if not otp:
                    raise ElementNotFoundError("OTP tidak datang dalam 80 detik")
                print(f"  ✓ OTP: {otp}")
            ac.click_image(tmpl_path, timeout=15)
            time.sleep(0.3)
            ac.hotkey("ctrl", "a")
            ac.type(otp)
            time.sleep(0.5)
            ac.click_text("Verify", timeout=10)
            print("  ✓ OTP disubmit")
            time.sleep(3)

        else:
            print(f"  ⚠ Aksi tidak dikenal: {action} — dilewati")

    print(f"\n{'='*52}")
    print("  FLOW SELESAI ✓")
    if EMAIL:
        print(f"  Email    : {EMAIL}")
        print(f"  Nama     : {NAMA}")
        print(f"  Password : {PASSWORD}")
    print(f"{'='*52}")

except ElementNotFoundError as e:
    print(f"\n  [GAGAL] {e}")
    print("  Cek folder debug_screenshots/")
except Exception as e:
    print(f"\n  [ERROR] {e}")
