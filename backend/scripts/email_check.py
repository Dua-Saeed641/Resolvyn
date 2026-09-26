"""Check that real email is set up correctly. Sends NOTHING unless you pass --send-to.

  .venv\\Scripts\\python scripts\\email_check.py                       # settings, SMTP login, IMAP login
  .venv\\Scripts\\python scripts\\email_check.py --send-to you@gmail.com   # also send one real test email

Gmail needs: 2-step verification on, an App Password (Google Account > Security > App passwords), and IMAP enabled
(Gmail > Settings > Forwarding and POP/IMAP) if you want Riya to read replies.
"""

import argparse
import imaplib
import smtplib
import ssl
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
from app.config import get_settings  # noqa: E402

S = get_settings()
bad = 0


def line(ok: bool | None, what: str, fix: str = "") -> None:
    global bad
    mark = {True: "[ ok ]", False: "[FAIL]", None: "[info]"}[ok]
    bad += ok is False
    print(f"{mark} {what}" + (f"\n         -> {fix}" if fix and ok is False else ""))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--send-to", help="send one real test email to this address")
    args = ap.parse_args()
    print("Resolvyn email check\n")
    line(bool(S.email_address), f"EMAIL_ADDRESS = {S.email_address or '(empty)'}", "set your Gmail address in backend/.env")
    pw = S.email_password or ""
    line(bool(pw), "EMAIL_PASSWORD is set" if pw else "EMAIL_PASSWORD is empty", "paste your 16-character Google App Password (not your normal password)")
    if pw and len(pw.replace(" ", "")) != 16:
        line(False, f"the password is {len(pw.replace(' ', ''))} characters", "a Gmail App Password is exactly 16 letters (spaces are fine)")
    line(None, f"SMTP {S.email_smtp_host}:{S.email_smtp_port} ({S.email_smtp_security}), IMAP {S.email_imap_host}")
    line(None, f"customers: {S.customer_emails or '(none set)'}")
    if S.email_redirect_to:
        line(None, f"EMAIL_REDIRECT_TO = {S.email_redirect_to}: every email goes there instead of to the customer")
    if not (S.email_address and pw):
        print("\nNothing more to test until the address and app password are set.")
        sys.exit(1)
    password = pw.replace(" ", "")

    from app.services.email_service import imap_connect, smtp_connect

    try:
        with smtp_connect() as smtp:
            smtp.login(S.email_address, password)
        line(True, "SMTP login works: Riya can send email")
    except smtplib.SMTPAuthenticationError:
        line(False, "SMTP login was rejected", "use an App Password with 2-step verification on; a normal Gmail password does not work")
    except Exception as e:  # noqa: BLE001
        line(False, f"SMTP failed: {type(e).__name__}: {e}", "check EMAIL_SMTP_HOST / port / your network (try EMAIL_FORCE_IPV4=true)")

    if S.email_imap_host:
        try:
            box = imap_connect()
            box.login(S.email_address, password)
            box.select("INBOX", readonly=True)
            _, data = box.search(None, "UNSEEN")
            line(True, f"IMAP login works: Riya can read replies ({len(data[0].split()) if data and data[0] else 0} unread in the inbox)")
            box.logout()
        except imaplib.IMAP4.error:
            line(False, "IMAP login was rejected", "enable IMAP in Gmail (Settings > Forwarding and POP/IMAP) and use the App Password")
        except Exception as e:  # noqa: BLE001
            line(False, f"IMAP failed: {type(e).__name__}: {e}", "check EMAIL_IMAP_HOST and your network")

    if args.send_to and not bad:
        from app.services.email_service import Mail, _send

        mail = Mail(to=args.send_to, ticket_id="TEST", kind="test", subject="Resolvyn email check",
                    body="This is a test from Riya at Nova Retail. If you can read it, outgoing email works.\n")
        _send(mail)
        line(mail.delivered == "smtp", f"test email to {mail.to}: {mail.delivered}", "see the message printed above")
    print("\nAll good." if not bad else f"\n{bad} problem(s) to fix.")
    sys.exit(1 if bad else 0)


main()
