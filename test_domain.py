"""
Test apakah domain bisa dipakai di API tempmail.

Usage:
    python test_domain.py --email la.co.mz
    python test_domain.py --email la.co.mz,leprinter.net,riwaweb.com
    python test_domain.py --all   (test semua domain dari email.txt)
"""
import argparse
import json
import time
import urllib.parse
import urllib.request

PANEL_URL     = "https://api.lpmterkam.org/"
DEVICE_SECRET = "4e427c6afcd3267d370d96294b3d6411ffc5ed198dc995e40934ec6b73e32cc5"


def test_domain(domain: str) -> dict:
    url = PANEL_URL.rstrip("/") + "/api/ext/tempmail.php?" + urllib.parse.urlencode({
        "action": "quick_email",
        "prefer_domain": domain,
    })
    req = urllib.request.Request(url, headers={
        "X-Device-Secret": DEVICE_SECRET,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        if not data.get("ok"):
            return {"ok": False, "error": data.get("error", "unknown")}
        return {"ok": True, "email": data["email"], "domain": data.get("domain", "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default="", help="Domain atau beberapa domain pisah koma")
    parser.add_argument("--all",   action="store_true", help="Test semua domain dari email.txt")
    args = parser.parse_args()

    domains = []
    if args.all:
        try:
            with open("email.txt", encoding="utf-8") as f:
                domains = [l.strip() for l in f if l.strip()]
        except FileNotFoundError:
            print("❌ email.txt tidak ditemukan")
            return
    elif args.email:
        domains = [d.strip() for d in args.email.split(",") if d.strip()]
    else:
        parser.print_help()
        return

    print(f"\n🔍 Test {len(domains)} domain...\n")
    ok_list  = []
    fail_list = []

    for domain in domains:
        result = test_domain(domain)
        if result["ok"]:
            got = result.get("domain", "")
            match = "✓" if got == domain else f"⚠ (dapat {got})"
            print(f"  ✅ {domain} → {result['email']}  {match}")
            ok_list.append(domain)
        else:
            print(f"  ❌ {domain} → GAGAL: {result['error']}")
            fail_list.append(domain)
        time.sleep(0.5)

    print(f"\n{'='*50}")
    print(f"  BERHASIL : {len(ok_list)}")
    print(f"  GAGAL    : {len(fail_list)}")
    if fail_list:
        print(f"\n  Domain gagal:")
        for d in fail_list:
            print(f"    - {d}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
