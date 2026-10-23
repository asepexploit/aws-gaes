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
parser.add_argument("--email",     default="example@gmail.com", help="Email dummy saat --skipemail, atau 'success' untuk random dari email.txt")
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
    "retry": {"timeout": 600, "max_attempts": 999, "delay_between": 2.0},
    "debug": {"save_on_failure": True},
})


# ─── Helpers ──────────────────────────────────────────────
def random_domain_from_file(path: str = "email.txt") -> str:
    try:
        with open(path, encoding="utf-8") as f:
            domains = [l.strip() for l in f if l.strip()]
        if not domains:
            raise ValueError("email.txt kosong")
        return random.choice(domains)
    except FileNotFoundError:
        raise RuntimeError("email.txt tidak ditemukan")


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


def create_email(prefer_domain: str = "") -> dict:
    params = {}
    if prefer_domain:
        params["prefer_domain"] = prefer_domain
    return _api("quick_email", params)


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
            extra  = parts[3] if len(parts) >= 4 else ""
            extra2 = parts[4] if len(parts) >= 5 else ""
            # Format 4 bagian: input:BEBAS -> nilai bebas
            if extra and action.lower() == "input:bebas":
                action = f"input:{extra}"
                extra  = extra2  # geser: extra2 jadi extra (misal "false")
            # Cek sleep sebelum aksi: klik -> sleep:10
            pre_sleep = 0.0
            if extra and extra.lower().startswith("sleep:") and action.lower() != "input:bebas":
                try:
                    pre_sleep = float(extra.split(":")[1])
                except ValueError:
                    pass
            # Cek skip deteksi template: -> false
            skip_detect = extra.lower() == "false"

            steps.append({
                "num":         int(parts[0]),
                "template":    parts[1],
                "action":      action,
                "pre_sleep":   pre_sleep,
                "skip_detect": skip_detect,
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
    if args.email.lower() == "success" and needs_email:
        domain = random_domain_from_file()
        print(f"📧 Generate email dengan domain: {domain}...")
        d           = create_email(prefer_domain=domain)
        EMAIL       = d["email"]
        EMAIL_TOKEN = d.get("account_token", "")
        EMAIL_TS    = d.get("ts", "")
        print(f"  ✓ Email : {EMAIL}")
        print(f"  ✓ Nama  : {NAMA}")
    elif args.skipemail and needs_email:
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

        # ── scroll tanpa template (pakai - sebagai template) ──
        if action.lower().startswith("scroll:") and template.strip() == "-":
            import pyautogui as _pg
            parts_s = action.lower().split(":")
            direction = parts_s[1] if len(parts_s) > 1 else "down"
            amount = int(parts_s[2]) if len(parts_s) > 2 else 3
            cx, cy = _pg.size()
            ac.scroll(cx // 2, cy // 2, amount=amount, direction=direction)
            print(f"\n  [STEP {n}] Scroll {direction} x{amount}")
            continue

        print(f"\n{'='*52}")
        print(f"  STEP {n}: {template} → {action}")
        print(f"{'='*52}")

        tmpl_path    = f"{T}/{template}.png"
        act_lower    = action.lower()
        pre_sleep    = s.get("pre_sleep", 0.0)
        skip_detect  = s.get("skip_detect", False)
        if pre_sleep > 0:
            print(f"  ⏳ Tunggu {pre_sleep}s sebelum aksi...")
            time.sleep(pre_sleep)

        # ── klik saja ──
        # support: klik, klik:timeout:60
        if act_lower.startswith("klik") or act_lower in ("continue", "click"):
            timeout = 600
            if "timeout:" in act_lower:
                try:
                    timeout = int(act_lower.split("timeout:")[1])
                except ValueError:
                    pass
            ac.click_image(tmpl_path, timeout=timeout)
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
            if not skip_detect:
                ac.click_image(tmpl_path, timeout=600)
                time.sleep(0.3)
            ac.hotkey("ctrl", "a")
            ac.type(nilai)
            print(f"  ✓ Input: {nilai}")
            time.sleep(0.5)

        # ── OTP ──
        # ── scroll dengan template (klik dulu baru scroll di posisi sama) ──
        elif act_lower.startswith("scroll:"):
            parts_s = act_lower.split(":")
            direction = parts_s[1] if len(parts_s) > 1 else "down"
            amount = int(parts_s[2]) if len(parts_s) > 2 else 3
            import pyautogui as _pg
            result = ac.find_image(tmpl_path, timeout=600)
            _pg.click(result.x, result.y)
            time.sleep(1)
            ac.scroll(result.x, result.y, amount=amount, direction=direction)
            print(f"  ✓ Scroll {direction} x{amount}")
            time.sleep(0.5)

        elif act_lower == "otp":
            if args.skipemail:
                otp = input("  Masukkan OTP yang diterima di email: ").strip()
                print(f"  ✓ OTP : {otp}")
            else:
                otp = poll_otp(EMAIL, EMAIL_TOKEN, EMAIL_TS)
                if not otp:
                    raise ElementNotFoundError("OTP tidak datang dalam 80 detik")
                print(f"  ✓ OTP: {otp}")
            ac.click_image(tmpl_path, timeout=600)
            time.sleep(0.3)
            ac.hotkey("ctrl", "a")
            ac.type(otp)
            print("  ✓ OTP diisi")
            time.sleep(3)

        # ── scroll ──
        elif act_lower.startswith("scroll:"):
            parts_s = act_lower.split(":")
            direction = parts_s[1] if len(parts_s) > 1 else "down"
            amount = int(parts_s[2]) if len(parts_s) > 2 else 3
            import pyautogui as _pg
            cx, cy = _pg.size()
            ac.scroll(cx // 2, cy // 2, amount=amount, direction=direction)
            print(f"  ✓ Scroll {direction} x{amount}")
            time.sleep(0.5)

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
