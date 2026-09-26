"""Email benchmarks: one Dua Saeed chat (account unlock, order cancellation with refund, a warranty question) run end to end,
then the summary email is judged against protocol, content, accuracy, privacy, presentation and safety benchmarks.

Each test name starts with its benchmark id (B01, B02...) so a failure says exactly which benchmark broke.
"""

import email
import json
import re
import socketserver
import threading
import time
from email import policy
from email.utils import parsedate_to_datetime

import pytest

from app.services import conversation, email_render, email_service
from app.services.sessions import sessions
from tests.test_flows import _open, _turn

DUA_LINES = [
    "Hi, I can't log in, my account is locked",
    "the last four digits of my phone are 3390",
    "yes please unlock it",
    "Also, where is my yoga mat order ORD-84155?",
    "can I cancel that one?",
    "yes please cancel it",
    "what is the warranty on the smart kettle",
    "no that's all, thanks a lot",
]


def _wait(pred, timeout=15.0):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(0.25)
    return None


@pytest.fixture(scope="module")
def dua(client):
    """Dua's whole chat, then the summary email that follows it."""
    client.post("/api/demo/reset")
    ws, c, tid = _open(client, "CUS-20517")
    for line in DUA_LINES:
        _turn(c, line)
    ws.__exit__(None, None, None)
    mail = _wait(lambda: next((m for m in email_service.OUTBOX if m.ticket_id == tid and m.kind == "summary"), None))
    assert mail, "no summary email was produced after the chat"
    return {"tid": tid, "mail": mail, "msg": email.message_from_bytes(mail.raw, policy=policy.default),
            "detail": client.get(f"/api/tickets/{tid}").json()}


def _parts(msg):
    text = msg.get_body(preferencelist=("plain",)).get_content()
    html = msg.get_body(preferencelist=("html",)).get_content()
    return text, html


# ── protocol ─────────────────────────────────────────────────────────────────


def test_B01_mime_structure_is_multipart_alternative_with_text_html_and_inline_logo(dua):
    msg = dua["msg"]
    assert msg.get_content_type() == "multipart/alternative"
    kinds = [p.get_content_type() for p in msg.iter_parts()]
    assert kinds[0] == "text/plain" and kinds[1] in ("text/html", "multipart/related")
    _, html = _parts(msg)
    logo = [p for p in msg.walk() if p.get_content_type() == "image/png"]
    assert logo and logo[0]["Content-ID"].strip("<>") == email_render.LOGO_CID
    assert f"cid:{email_render.LOGO_CID}" in html
    assert msg.get_body(preferencelist=("plain",)).get_content_charset() == "utf-8"


def test_B02_headers_are_complete_and_well_formed(dua):
    msg = dua["msg"]
    assert msg["MIME-Version"] == "1.0"
    for h in ("From", "To", "Reply-To", "Subject", "Date", "Message-ID"):
        assert msg[h], f"missing {h}"
    assert re.fullmatch(r"<[^<>@\s]+@[^<>\s]+>", msg["Message-ID"])
    assert parsedate_to_datetime(msg["Date"]).year >= 2026
    assert msg["From"].addresses[0].display_name.startswith("Riya at ")
    assert msg["To"].addresses[0].addr_spec == "duasaeed641@gmail.com" or msg["To"].addresses[0].addr_spec.endswith("@example.com")
    assert len(msg["Subject"]) <= 78 and dua["tid"] in msg["Subject"], "subject is short and carries the ticket tag for threading"


def test_B03_rfc3834_marks_the_message_automatic_and_ours(dua):
    msg = dua["msg"]
    assert msg["Auto-Submitted"] == "auto-generated"
    assert msg["X-Auto-Response-Suppress"] == "All"
    assert msg["X-Resolvyn"] == "1" and msg["X-Resolvyn-Ticket"] == dua["tid"]


def test_B04_non_ascii_survives_the_round_trip(dua):
    text, html = _parts(dua["msg"])
    assert "₹1,299" in text and "₹1,299" in html


# ── content ──────────────────────────────────────────────────────────────────


def test_B05_it_is_a_summary_not_the_conversation(dua):
    text, html = _parts(dua["msg"])
    blob = (text + html).lower()
    said = [m["content"] for m in dua["detail"]["messages"] if m["sender"] == "CUSTOMER"]
    for line in said:
        assert line.lower().rstrip(".?!") not in blob, f"customer's own words were dumped: {line!r}"
    assert not re.search(r"^\s*(you|riya|customer)\s*:", text, re.I | re.M)
    assert len(text) <= 2600 and len(text.splitlines()) <= 60


def test_B06_every_important_point_of_the_conversation_is_covered(dua):
    text, _ = _parts(dua["msg"])
    low = text.lower()
    assert "your account" in low and "unlocked" in low and "identity" in low          # account: verified, unlocked
    assert "reset link" in low                                                          # what was sent
    assert "ord-84155" in low and "cancelled" in low and "₹1,299" in text              # order: cancelled, amount
    assert "3 to 5 working days" in low                                                 # refund timeline
    assert "warranty" in low                                                            # the information question
    assert "status" in low and "resolved" in low and dua["tid"].lower() in low         # outcome and reference
    assert "what happens next" in low


def test_B07_topics_follow_the_order_they_were_discussed(dua):
    text, _ = _parts(dua["msg"])
    assert text.index("Your account") < text.index("Your order") < text.lower().index("warranty")


def test_B08_every_id_and_amount_comes_from_verified_records(dua):
    text, _ = _parts(dua["msg"])
    verified = json.dumps(dua["detail"]["tool_calls"]) + json.dumps(dua["detail"]["pending_actions"]) + json.dumps(dua["detail"]["messages"])
    for ref in set(re.findall(r"\b(?:ORD|RFD|TXN|SHP)-\d+\b", text)):
        assert ref in verified or ref == dua["tid"], f"{ref} is not in the ticket's records"
    for amount in set(re.findall(r"₹([\d,]+)", text)):
        assert amount.replace(",", "") in verified, f"₹{amount} is not in the ticket's records"


def test_B09_privacy_masks_addresses_and_leaks_no_internals(dua):
    text, html = _parts(dua["msg"])
    blob = text + html
    assert not re.search(r"[A-Za-z0-9._%+-]+@gmail\.com", blob.replace("d***@gmail.com", ""))  # nobody's full address inside the body
    assert not re.search(r"\b\d{12,16}\b", blob)                                                # no card numbers
    for internal in ("Jev", "TURN_TRACE", "confidence", "first-time bug", "tool_call", "Decision Engine", "truth guard"):
        assert internal.lower() not in blob.lower(), internal


def test_B10_tone_is_personal_clear_and_ends_with_next_steps(dua):
    text, _ = _parts(dua["msg"])
    assert text.startswith("Hi Dua,")
    assert not re.search(r"valued customer|dear customer|kindly|inconvenience", text, re.I)
    assert "reply to this email" in text.lower()


# ── plain text ───────────────────────────────────────────────────────────────


def test_B11_plain_text_is_wrapped_and_clean(dua):
    text, _ = _parts(dua["msg"])
    assert max(len(l) for l in text.splitlines()) <= 78
    assert not re.search(r"</?\w+[^>]*>", text) and "**" not in re.sub(r"\w\*{3}@", "", text) and "##" not in text


# ── HTML and presentation ────────────────────────────────────────────────────


def test_B12_html_is_email_safe(dua):
    _, html = _parts(dua["msg"])
    assert html.lstrip().lower().startswith("<!doctype html>") and '<html lang="en">' in html
    assert "<title>" in html and 'name="viewport"' in html
    assert re.search(r'<table[^>]*width="600"', html) and "max-width:100%" in html
    assert "<script" not in html.lower() and "javascript:" not in html.lower()
    assert not re.search(r'(?:src|href)="https?://', html), "no external resources: the logo is inline (cid:)"
    for img in re.findall(r"<img\b[^>]*>", html):
        assert 'alt="' in img and "width=" in img and "height=" in img
    assert html.count('role="presentation"') >= 3


def test_B13_hidden_preheader_previews_the_outcome_in_the_inbox(dua):
    _, html = _parts(dua["msg"])
    m = re.search(r'display:none;[^>]*>(.*?)&#8199;', html, re.S)
    assert m and "Resolved" in m.group(1) and len(m.group(1)) <= 140


def test_B14_size_stays_under_gmails_clipping_limit(dua):
    _, html = _parts(dua["msg"])
    assert len(html.encode()) < 102_000 and len(dua["mail"].raw) < 200_000


def test_B15_text_and_background_colours_meet_wcag_aa_contrast():
    def lum(hexc):
        r, g, b = (int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)

    def ratio(a, b):
        la, lb = sorted((lum(a), lum(b)), reverse=True)
        return (la + 0.05) / (lb + 0.05)

    C = email_render.C
    pairs = [("text", "card"), ("muted", "card"), ("muted", "soft"), ("muted", "bg"), ("brand_text", "brand_tint"), ("warn_text", "warn_tint"),
             ("info_text", "info_tint"), ("text", "soft"), ("brand_text", "card")]
    for fg, bg in pairs:
        assert ratio(C[fg], C[bg]) >= 4.5, f"{fg} on {bg} is {ratio(C[fg], C[bg]):.2f}:1"


def test_B16_readable_type_sizes_and_dark_mode_support(dua):
    _, html = _parts(dua["msg"])
    sizes = [int(x) for x in re.findall(r"font-size:(\d+)px", html) if int(x) > 1]
    assert min(sizes) >= 11 and max(sizes) <= 28
    assert "prefers-color-scheme: dark" in html and 'name="color-scheme" content="light dark"' in html


def test_B17_text_and_html_say_the_same_things(dua):
    text, html = _parts(dua["msg"])
    plain_html = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"(?is)<style.*?</style>", "", html)))
    for needle in ("Your account", "Your order", "ORD-84155", "₹1,299", "Resolved", "3 to 5 working days", dua["tid"]):
        assert needle in text and needle in plain_html, needle


# ── threading and inbound ────────────────────────────────────────────────────


def _send(client, sender, subject, text, headers=None, ticket_id=None):
    body = {"from": sender, "subject": subject, "text": text}
    if headers:
        body["headers"] = headers
    if ticket_id:
        body["ticket_id"] = ticket_id
    r = client.post("/api/email/inbound", json=body)
    assert r.status_code == 200, r.text
    return r.json()


def test_B18_replies_thread_by_message_id_even_when_the_subject_tag_is_lost(client):
    client.post("/api/demo/reset")
    first = _send(client, "dua.saeed@example.com", "Order status", "Where is my yoga mat order ORD-84155?",
                  headers={"Message-ID": "<abc1@mail.example>"})
    tid = first["ticket_id"]
    sent = next(m for m in email_service.OUTBOX if m.ticket_id == tid)
    assert sent.in_reply_to == "<abc1@mail.example>" and "<abc1@mail.example>" in sent.references
    # her next mail has a brand-new subject and no [PH-] tag, only In-Reply-To
    second = _send(client, "dua.saeed@example.com", "one more thing", "Can I cancel it?", headers={"In-Reply-To": sent.message_id, "Message-ID": "<abc2@mail.example>"})
    assert second["ticket_id"] == tid


def test_B19_automated_mail_is_never_answered(client):
    client.post("/api/demo/reset")
    for headers, sender, subject in [
        ({"Auto-Submitted": "auto-replied"}, "dua.saeed@example.com", "Re: hello"),
        ({"Precedence": "bulk"}, "dua.saeed@example.com", "Sale!"),
        ({"X-Resolvyn": "1"}, "dua.saeed@example.com", "Your support summary [PH-1]"),
        (None, "MAILER-DAEMON@mail.example", "Undeliverable: hello"),
        (None, "no-reply@shop.example", "Your receipt"),
        (None, "dua.saeed@example.com", "Automatic reply: I am out of office"),
    ]:
        out = _send(client, sender, subject, "please answer this", headers)
        assert out["reply"] is None and out.get("skipped"), (headers, sender, subject)
    assert not email_service.OUTBOX, "nothing was sent in reply to robots"


def test_B20_a_thread_cannot_ping_pong_forever(client, monkeypatch):
    client.post("/api/demo/reset")
    monkeypatch.setattr(email_service, "MAX_AUTO_EMAILS_PER_HOUR", 2)
    tid = _send(client, "dua.saeed@example.com", "Question", "Where is my yoga mat order ORD-84155?")["ticket_id"]
    _send(client, "dua.saeed@example.com", f"Re: Question [{tid}]", "and can I cancel it?", ticket_id=tid)
    third = _send(client, "dua.saeed@example.com", f"Re: Question [{tid}]", "hello?", ticket_id=tid)
    assert third["reply"] is None
    assert any(e["event_type"] == "EMAIL_SUPPRESSED" for e in client.get(f"/api/tickets/{tid}").json()["events"])


def test_B21_imap_only_answers_customers_leaves_other_mail_unread_and_skips_our_own(monkeypatch):
    from app.config import get_settings
    s = get_settings()
    for k, v in dict(email_address="support@x.test", email_password="pw", email_imap_host="imap.x.test").items():
        monkeypatch.setattr(s, k, v)
    plain = lambda frm, subj, body, extra="": (f"From: {frm}\r\nTo: support@x.test\r\nSubject: {subj}\r\nMessage-ID: <{abs(hash(subj))}@m>\r\n{extra}\r\n{body}").encode()
    box = {
        b"1": plain("Dua <dua.saeed@example.com>", "Order", "Where is my order?"),
        b"2": plain("Stranger <spam@evil.example>", "Buy now", "cheap watches"),
        b"3": plain("Riya <support@x.test>", "Your support summary [PH-1]", "summary", "X-Resolvyn: 1\r\n"),
        b"4": plain("Dua <dua.saeed@example.com>", "Automatic reply: away", "away", "Auto-Submitted: auto-replied\r\n"),
    }
    calls = []

    class FakeIMAP:
        def __init__(self, host): calls.append(("connect", host))
        def login(self, u, p): calls.append(("login", u))
        def select(self, m): return "OK", [b"4"]
        def search(self, *a): return "OK", [b" ".join(box)]
        def fetch(self, num, what):
            calls.append(("fetch", num, what))
            assert "PEEK" in what, "reading mail we may not answer must not mark it as read"
            msg = email.message_from_bytes(box[num])
            if "HEADER.FIELDS" in what:
                hdr = "".join(f"{k}: {v}\r\n" for k, v in msg.items() if k.lower() in ("from", "subject", "auto-submitted", "precedence", "x-resolvyn", "x-autoreply")) + "\r\n"
                return "OK", [(b"1", hdr.encode())]
            return "OK", [(b"1", box[num])]
        def store(self, num, op, flag): calls.append(("store", num, flag))
        def logout(self): pass

    monkeypatch.setattr(email_service.imaplib, "IMAP4_SSL", FakeIMAP)
    got = email_service._fetch_unseen()
    assert [m["sender"] for m in got] == ["dua.saeed@example.com"] and got[0]["subject"] == "Order"
    stored = [c[1] for c in calls if c[0] == "store"]
    assert b"1" in stored and b"2" not in stored and b"3" not in stored, "only the mail we answered (and automated noise from a customer) is marked read"


# ── transport ────────────────────────────────────────────────────────────────


class _MiniSMTP(socketserver.StreamRequestHandler):
    """Just enough SMTP to receive a message: EHLO, MAIL, RCPT, DATA, QUIT."""

    def handle(self):
        w = lambda s: self.wfile.write((s + "\r\n").encode())
        w("220 test ESMTP")
        data, rcpts, sender = [], [], ""
        while True:
            line = self.rfile.readline().decode("utf-8", "replace").rstrip("\r\n")
            cmd = line.upper()
            if cmd.startswith("EHLO") or cmd.startswith("HELO"):
                w("250-test"); w("250 8BITMIME")
            elif cmd.startswith("MAIL FROM"):
                sender = line.split(":", 1)[1].strip(); w("250 ok")
            elif cmd.startswith("RCPT TO"):
                rcpts.append(line.split(":", 1)[1].strip()); w("250 ok")
            elif cmd == "DATA":
                w("354 go")
                while True:
                    ln = self.rfile.readline().decode("utf-8", "replace")
                    if ln in (".\r\n", ".\n"):
                        break
                    data.append(ln[1:] if ln.startswith("..") else ln)
                self.server.received.append({"from": sender, "to": rcpts, "data": "".join(data)})
                w("250 queued")
            elif cmd == "QUIT":
                w("221 bye"); return
            else:
                w("250 ok")


def test_B22_message_is_delivered_over_real_smtp_and_arrives_byte_faithful(monkeypatch):
    from app.config import get_settings

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        received: list = []

    srv = Server(("127.0.0.1", 0), _MiniSMTP)
    srv.received = []
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    s = get_settings()
    for k, v in dict(email_address="support@x.test", email_smtp_host="127.0.0.1", email_smtp_port=srv.server_address[1], email_smtp_security="none", email_password=None, email_redirect_to=None).items():
        monkeypatch.setattr(s, k, v)
    try:
        mail = email_service.Mail(to="duasaeed641@gmail.com", subject="Your support summary [PH-9]", body="Hi Dua,\n\nRefund ₹1,299.\n", ticket_id="TEST", kind="summary",
                                  html="<html><body><p>Refund ₹1,299.</p></body></html>")
        email_service._send(mail)
        assert mail.delivered == "smtp"
        got = srv.received[0]
        assert got["to"] == ["<duasaeed641@gmail.com>"] or "duasaeed641@gmail.com" in got["to"][0]
        wire = email.message_from_string(got["data"], policy=policy.default)
        assert wire["Message-ID"] == mail.message_id and wire["Subject"] == mail.subject
        assert "₹1,299" in wire.get_body(preferencelist=("plain",)).get_content()
    finally:
        srv.shutdown()


def test_B23_redirect_sends_everything_to_one_inbox_and_says_who_it_was_for(monkeypatch):
    from app.config import get_settings
    monkeypatch.setattr(get_settings(), "email_redirect_to", "tester@example.org")
    mail = email_service.Mail(to="duasaeed641@gmail.com", subject="Hi", body="Body\n", ticket_id="TEST", kind="test")
    email_service._send(mail)
    msg = email.message_from_bytes(mail.raw, policy=policy.default)
    assert msg["To"].addresses[0].addr_spec == "tester@example.org"
    assert "addressed to duasaeed641@gmail.com" in msg.get_body(preferencelist=("plain",)).get_content()


# ── the customer's own reply is answered in the same pretty format ──────────


def test_B24_replies_use_the_same_layout_and_read_naturally(client):
    client.post("/api/demo/reset")
    out = _send(client, "dua.saeed@example.com", "Order status", "Where is my yoga mat order ORD-84155?")
    mail = next(m for m in email_service.OUTBOX if m.ticket_id == out["ticket_id"])
    msg = email.message_from_bytes(mail.raw, policy=policy.default)
    text, html = _parts(msg)
    assert msg["Auto-Submitted"] == "auto-replied"
    assert text.startswith("Hi Dua,") and "Warm regards," in text and mail.ticket_id in text
    assert "Yoga Mat Pro" in text and "<title>" in html and 'lang="en"' in html and 'width="600"' in html


def test_B25_a_customer_replying_to_the_summary_gets_a_correct_threaded_answer_and_the_ticket_reopens(client):
    """Dua cancels her yoga mat in a chat, gets the summary, replies to it (only In-Reply-To links the two) and asks when the refund arrives."""
    client.post("/api/demo/reset")
    ws, c, tid = _open(client, "CUS-20517")
    for line in ("I want to cancel my order ORD-84155", "yes please cancel it", "no that's all, thanks"):
        _turn(c, line)
    ws.__exit__(None, None, None)
    summary = _wait(lambda: next((m for m in email_service.OUTBOX if m.ticket_id == tid and m.kind == "summary"), None))
    assert summary
    out = _send(client, "duasaeed641@gmail.com", "thanks - one more question",
                "Thanks! When exactly will the refund for the yoga mat show up in my account?\n\nOn Sat, Riya wrote:\n> Hi Dua, here is what we sorted out.",
                headers={"Message-ID": "<dua-reply-1@mail.gmail.com>", "In-Reply-To": summary.message_id, "References": summary.message_id})
    assert out["ticket_id"] == tid, "threaded by In-Reply-To alone"
    old = next(x for x in sessions._sessions.values() if x.channel == "Text" and x.ticket_id == tid)
    client.portal.call(conversation.end_call, old, "connection lost")  # the chat's own hang-up handler fires late
    t = client.get(f"/api/tickets/{tid}").json()
    assert not t["escalated"] and t["status"] != "WAITING_FOR_HUMAN", "the old chat session must not close or escalate the reopened ticket"
    body = " ".join(out["reply"]["body"].split())
    assert "3 to 5 working days" in body and "duplicate" not in body.lower(), body
    events = [e["event_type"] for e in client.get(f"/api/tickets/{tid}").json()["events"]]
    assert "TICKET_REOPENED" in events
