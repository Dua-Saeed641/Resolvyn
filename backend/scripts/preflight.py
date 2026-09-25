"""Pre-demo checklist: run this 5 minutes before you present.

  .venv\\Scripts\\python scripts\\preflight.py            # check everything
  .venv\\Scripts\\python scripts\\preflight.py --reset    # ...and clear old demo tickets/refunds/bugs for a clean start

Checks the backend and model, Gnani speech (with a real request), the disk voice cache, the public tunnel, that the
phone webhook is reachable from the internet, and (if TWILIO_* is set) asks Twilio whether your number points at
this tunnel and your phone is a verified caller ID. Exit code 1 if anything FAILS.
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import httpx  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app.config import get_settings  # noqa: E402

S = get_settings()
LOCAL = "http://127.0.0.1:8000"
results: list[tuple[str, str, str]] = []


def rec(status: str, name: str, detail: str = "") -> None:
    results.append((status, name, detail))
    icon = {"PASS": "[ ok ]", "WARN": "[warn]", "FAIL": "[FAIL]"}[status]
    print(f"{icon} {name}" + (f"  -  {detail}" if detail else ""))


def get(url: str, **kw):
    return httpx.get(url, timeout=kw.pop("timeout", 8), **kw)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="clear demo tickets, refunds, bugs and taught rules first")
    args = ap.parse_args()
    print("Resolvyn pre-demo check\n")

    # ── backend + model ──────────────────────────────────────────────────────
    try:
        sysinfo = get(f"{LOCAL}/api/system").json()
    except Exception as e:  # noqa: BLE001
        rec("FAIL", "Backend reachable", f"{type(e).__name__}: start it with .\\start.ps1 -Tunnel")
        sys.exit(1)
    rec("PASS", "Backend reachable", f"{sysinfo['product']} / {sysinfo['business']}, agent {sysinfo['agent']}")
    llm = sysinfo["llm"]
    if llm["live_ready"]:
        rec("PASS", "Live language model", (llm["engine"].get("tiers", {}).get("fast", {}) or {}).get("model", "ready"))
    else:
        rec("FAIL", "Live language model", llm["engine"].get("error") or "still loading (wait ~15 s)")
    if llm["deep_ready"]:
        rec("PASS", "Deep model (27B) available for post-call analysis")
    else:
        rec("WARN", "Deep model (27B) not available", "optional: .\\engine\\download_models.ps1 -Deep")

    # ── speech ───────────────────────────────────────────────────────────────
    if sysinfo["stt"]["gnani"]:
        rec("PASS", "Gnani key configured", f"speech recognition: {sysinfo['stt']['provider']}")
        t = time.perf_counter()
        r = get(f"{LOCAL}/api/tts", params={"text": "Hi, this is Riya. Just a quick sound check.", "lang": "en"}, timeout=25)
        if r.status_code == 200 and len(r.content) > 2000:
            rec("PASS", "Voice synthesis works", f"{len(r.content) // 1024} KB in {time.perf_counter() - t:.1f}s, provider {sysinfo['tts']['providers'][0]}")
        else:
            rec("WARN", "Voice synthesis failed", "browser voice will be used; on the phone Riya would be silent (Gnani rate limit? wait a minute)")
    else:
        rec("WARN", "No Gnani key", "phone calls need it; the website mic falls back to Chrome/Edge speech recognition")
    cache = Path(__file__).resolve().parent.parent / "data" / "tts_cache"
    n = len(list(cache.glob("*.bin"))) if cache.exists() else 0
    rec("PASS" if n >= 60 else "WARN", "Voice phrase cache", f"{n} phrases cached" + ("" if n >= 60 else " (still warming: keep the server running a few minutes)"))

    # ── data state ───────────────────────────────────────────────────────────
    if args.reset:
        httpx.post(f"{LOCAL}/api/demo/reset", timeout=20)
        rec("PASS", "Demo reset", "old demo tickets, refunds, bugs and taught rules cleared")
    stats = get(f"{LOCAL}/api/analytics").json()
    docs = get(f"{LOCAL}/api/knowledge").json()
    rec("PASS" if docs else "FAIL", "Knowledge loaded", f"{len(docs)} documents")
    if stats["open_bugs"] or stats["pending_approvals"]:
        rec("WARN", "Leftovers from earlier runs", f"{stats['open_bugs']} open bug(s), {stats['pending_approvals']} pending approval(s): run with --reset")

    # ── tunnel + webhook ─────────────────────────────────────────────────────
    public = None
    try:
        tunnels = get("http://127.0.0.1:4040/api/tunnels", timeout=3).json()["tunnels"]
        public = next((t["public_url"] for t in tunnels if t["public_url"].startswith("https")), None)
    except Exception:  # noqa: BLE001
        pass
    if not public:
        rec("WARN", "No ngrok tunnel", "phones and Twilio cannot reach you: start with .\\start.ps1 -Tunnel")
    else:
        rec("PASS", "Public tunnel", public)
        try:  # what the *running* server believes (start.ps1 -Tunnel sets it in the server's environment)
            hook = get(f"{LOCAL}/api/telephony/status").json()["webhook_url"]
        except Exception:  # noqa: BLE001
            hook = ""
        if not hook.startswith(public):
            rec("WARN", "The server does not know its public URL", f"webhook would be {hook!r}: restart with .\start.ps1 -Tunnel")
        try:
            h = {"ngrok-skip-browser-warning": "1"}
            r = httpx.post(f"{public}/api/telephony/twilio/voice", data={"From": "+10000000000"}, headers=h, timeout=10)
            ok = r.status_code == 200 and "<Stream" in r.text and public.replace("https", "wss") in r.text
            rec("PASS" if ok else "FAIL", "Phone webhook reachable from the internet", "returns the stream TwiML" if ok else f"HTTP {r.status_code}")
            page = httpx.get(f"{public}/", headers=h, timeout=10)
            rec("PASS" if page.status_code == 200 else "FAIL", "Website reachable from the internet", f"HTTP {page.status_code}")
        except Exception as e:  # noqa: BLE001
            rec("FAIL", "Public URL check", f"{type(e).__name__}: {e}")

    # ── twilio ───────────────────────────────────────────────────────────────
    if not S.twilio_account_sid:
        rec("WARN", "Twilio not configured", "fine for the website mic; see docs/demo-runbook.md to set up the phone")
    else:
        auth = (S.twilio_account_sid, S.twilio_auth_token or "")
        base = f"https://api.twilio.com/2010-04-01/Accounts/{S.twilio_account_sid}"
        try:
            acc = httpx.get(f"{base}.json", auth=auth, timeout=10)
            if acc.status_code != 200:
                rec("FAIL", "Twilio credentials", f"HTTP {acc.status_code}: check TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN")
            else:
                a = acc.json()
                rec("PASS", "Twilio credentials", f"account {a['friendly_name']!r}, type {a['type']}, status {a['status']}")
                nums = httpx.get(f"{base}/IncomingPhoneNumbers.json", auth=auth, timeout=10).json().get("incoming_phone_numbers", [])
                mine = next((n for n in nums if n["phone_number"] == S.twilio_phone_number), None)
                if not mine and a["type"] == "Trial" and not nums:
                    rec("WARN", "Twilio number not purchasable on this trial", "fine: use the Call me button (Twilio dials you); dialling in needs a paid number")
                elif not mine:
                    rec("FAIL", "Twilio number", f"{S.twilio_phone_number!r} is not on this account ({[n['phone_number'] for n in nums]})")
                else:
                    want = f"{(public or '').rstrip('/')}/api/telephony/twilio/voice"
                    same = mine.get("voice_url") == want
                    rec("PASS" if same else "FAIL", "Twilio number webhook",
                        "points at this tunnel" if same else f"is {mine.get('voice_url')!r}, should be {want!r}")
                ids = httpx.get(f"{base}/OutgoingCallerIds.json", auth=auth, timeout=10).json().get("outgoing_caller_ids", [])
                verified = {i["phone_number"] for i in ids}
                for pair in S.phone_aliases.split(","):
                    num = pair.partition(":")[0].strip()
                    if num:
                        rec("PASS" if num in verified else "WARN", f"{num} is a verified caller ID" if num in verified else f"{num} not in the caller-ID list",
                            "" if num in verified else "new trial accounts list verified recipients elsewhere; the Call me test will confirm")
                if not S.phone_aliases.strip():
                    rec("WARN", "PHONE_ALIASES empty", "your phone will be treated as a guest (Riya asks who you are)")
        except Exception as e:  # noqa: BLE001
            rec("FAIL", "Twilio API", f"{type(e).__name__}: {e}")

    fails = sum(1 for r in results if r[0] == "FAIL")
    warns = sum(1 for r in results if r[0] == "WARN")
    print(f"\n{len(results) - fails - warns} ok, {warns} warning(s), {fails} failure(s)")
    sys.exit(1 if fails else 0)


main()
