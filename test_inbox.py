"""
Test apakah domain bisa terima email:
1. Generate email dari domain via API tempmail
2. Buat email sender sementara via cPanel
3. Kirim email test via SMTP cPanel
4. Poll inbox 60 detik, kalau masuk = AKTIF

Usage:
    python test_inbox.py --domain leprinter.net
    python test_inbox.py --all
"""
import argparse
import json
import random
import smtplib
import string
import time
import urllib.parse
import urllib.request
from email.mime.text import MIMEText

PANEL_URL     = "https://api.lpmterkam.org/"
DEVICE_SECRET = "4e427c6afcd3267d370d96294b3d6411ffc5ed198dc995e40934ec6b73e32cc5"

CPANEL_HOST   = "s84.gocheapweb.com"
CPANEL_USER   = "leprint2"
CPANEL_TOKEN  = "AHRQQQ2ID2RJJZCXNT544GJQN3J8HQIN"
SENDER_DOMAIN = "leprinter.net"


def _api(action, params={}):
    url = PANEL_URL.rstrip("/") + "/api/ext/tempmail.php?" + urllib.parse.urlencode({"action": action, **params})
    req = urllib.request.Request(url, headers={
        "X-Device-Secret": DEVICE_SECRET,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read())
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "API error"))
    return data


def cpanel(func, params={}):
    url = f"https://{CPANEL_HOST}:2083/execute/{func}?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}",
    })
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def create_sender_email():
    """Buat email sender sementara di cPanel."""
    rnd      = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    username = f"sender_{rnd}"
    password = "Test@" + "".join(random.choices(string.ascii_letters + string.digits, k=10))
    r = cpanel("Email/add_pop", {
        "email":    username,
        "password": password,
        "domain":   SENDER_DOMAIN,
        "quota":    10,
    })
    if r.get("status") != 1:
        raise RuntimeError(f"Gagal buat email sender: {r}")
    return f"{username}@{SENDER_DOMAIN}", password


def delete_sender_email(email):
    """Hapus email sender sementara."""
    username = email.split("@")[0]
    cpanel("Email/delete_pop", {"email": username, "domain": SENDER_DOMAIN})


def send_test_email(sender, password, to_email):
    msg = MIMEText("Test inbox - domain check")
    msg["Subject"] = "INBOX_TEST_CHECK"
    msg["From"]    = sender
    msg["To"]      = to_email
    with smtplib.SMTP_SSL(CPANEL_HOST, 465) as s:
        s.login(sender, password)
        s.sendmail(sender, [to_email], msg.as_string())


def poll_inbox(email, token, ts, timeout=60, interval=5):
    elapsed = 0
    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
        try:
            data = _api("inbox", {"email": email, "account_token": token, "ts": ts})
            for m in data.get("messages", []):
                if "INBOX_TEST" in (m.get("subject", "") + m.get("body_preview", "")):
                    return True
        except Exception as e:
            print(f"    poll error: {e}")
        print(f"    Nunggu... {elapsed}s/{timeout}s")
    return False


def test_domain(domain: str) -> bool:
    print(f"\n  🔍 Test domain: {domain}")
    sender = None
    try:
        # generate email target
        d = _api("quick_email", {"prefer_domain": domain})
        email = d["email"]
        token = d.get("account_token", "")
        ts    = d.get("ts", "")
        got   = d.get("domain", "")
        if got != domain:
            print(f"    ⚠ API kasih domain lain: {got}, skip")
            return False
        print(f"    Target  : {email}")

        # buat email sender sementara
        print(f"    Buat sender email...")
        sender, password = create_sender_email()
        print(f"    Sender  : {sender}")

        # kirim email test
        print(f"    Kirim test email...")
        send_test_email(sender, password, email)
        print(f"    ✓ Terkirim! Poll inbox 60s...")

        result = poll_inbox(email, token, ts)
        return result

    except Exception as e:
        print(f"    ❌ Error: {e}")
        return False
    finally:
        if sender:
            try:
                delete_sender_email(sender)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", default="", help="Domain yang mau ditest, pisah koma, atau 'random' untuk test semua dari email.txt")
    parser.add_argument("--all", action="store_true", help="Test semua domain dari email.txt")
    parser.add_argument("--send", default="", help="Kirim test email ke alamat ini, cek manual")
    args = parser.parse_args()

    # ── mode --send: kirim ke alamat langsung, cek manual ──
    if args.send:
        to_email = args.send.strip()
        print(f"\n📤 Kirim test email ke: {to_email}")
        try:
            sender, password = create_sender_email()
            print(f"  Sender  : {sender}")
            send_test_email(sender, password, to_email)
            delete_sender_email(sender)
            print(f"  ✓ Terkirim! Cek inbox {to_email} manual.")
        except Exception as e:
            print(f"  ❌ Gagal: {e}")
        return

    domains = []
    save_to_file = False
    if args.domain.lower() == "random":
        # generate 1 email random dari API, ambil domainnya
        print("\n📧 Generate email random dari API...")
        d = _api("quick_email")
        domain = d.get("domain", "")
        print(f"  Domain dapat: {domain}")
        domains = [domain]
    elif args.all:
        try:
            with open("email.txt", encoding="utf-8") as f:
                domains = [l.strip() for l in f if l.strip()]
        except FileNotFoundError:
            print("❌ email.txt tidak ditemukan")
            return
        save_to_file = True
    elif args.domain:
        domains = [d.strip() for d in args.domain.split(",") if d.strip()]
    else:
        parser.print_help()
        return

    print(f"\n📬 Test inbox {len(domains)} domain...\n")
    ok_list   = []
    fail_list = []

    for domain in domains:
        ok = test_domain(domain)
        if ok:
            print(f"  ✅ {domain} → AKTIF")
            ok_list.append(domain)
        else:
            print(f"  ❌ {domain} → MATI")
            fail_list.append(domain)

    print(f"\n{'='*50}")
    print(f"  AKTIF : {len(ok_list)}")
    print(f"  MATI  : {len(fail_list)}")
    if ok_list:
        print(f"\n  Domain aktif:")
        for d in ok_list:
            print(f"    ✅ {d}")
    if fail_list:
        print(f"\n  Domain mati:")
        for d in fail_list:
            print(f"    ❌ {d}")
    if save_to_file and ok_list:
        with open("email.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(ok_list) + "\n")
        print(f"\n  ✓ email.txt diupdate dengan {len(ok_list)} domain aktif")
    if fail_list:
        # tambah ke domain-mati.txt (tidak duplikat)
        try:
            with open("domain-mati.txt", encoding="utf-8") as f:
                existing = {l.strip() for l in f if l.strip()}
        except FileNotFoundError:
            existing = set()
        new_mati = [d for d in fail_list if d not in existing]
        if new_mati:
            with open("domain-mati.txt", "a", encoding="utf-8") as f:
                f.write("\n".join(new_mati) + "\n")
            print(f"  ✓ {len(new_mati)} domain mati ditambah ke domain-mati.txt")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
