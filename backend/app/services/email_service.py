"""Email channel: an email is a conversation turn through the same pipeline as a call.

Jev, memory, the department desks and their tools, the human approval gate, escalation and the truth guard all apply;
Riya writes back an email instead of speaking. A thread stays on one ticket: the subject carries [PH-1234], so a reply
continues the same conversation, and anything Riya says later on her own (a refund approved by the manager) is emailed too.

Three ways in:
  * the customer side's "Email us" panel and POST /api/email/inbound (JSON), the simulated inbox used in the demo;
  * the same endpoint as an inbound-parse webhook (form fields from / subject / text, e.g. SendGrid Inbound Parse);
  * a real mailbox: set EMAIL_IMAP_* / EMAIL_SMTP_* (a Gmail address with an app password works) and new mail is
    picked up every few seconds and answered to the sender's real inbox.
"""

import asyncio
import email
import html as _html
import imaplib
import re
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import parseaddr

from app.config import get_settings
from app.services import conversation
from app.services import ticket_service as tickets
from app.services.realtime import hub
from app.services.sessions import CallSession, sessions
from app.utils import utcnow

THREAD = re.compile(r"\[(PH-\d+)\]")
_RE_PREFIX = re.compile(r"^(?:(?:re|fwd?|fw)\s*:\s*)+", re.I)
_QUOTED = re.compile(r"(?ms)^(?:On .{5,200}wrote:|-{2,} ?Original Message ?-{2,}|From: .+?Sent: ).*\Z")
_SIGNATURE = re.compile(r"(?ms)^(?:-- ?$|Sent from my \w+).*\Z")


@dataclass
class Mail:
    to: str
    subject: str
    body: str
    ticket_id: str
    sent_at: str = field(default_factory=lambda: utcnow().isoformat())
    delivered: str = "simulated inbox"  # or "smtp"
    html: str | None = None
    kind: str = "reply"  # reply | summary
    intended_for: str | None = None  # set when EMAIL_REDIRECT_TO redirected it


OUTBOX: list[Mail] = []  # every email Riya sent (newest last), for the demo inbox and tests
_mailers: dict[str, asyncio.Task] = {}  # session -> task that turns what Riya says into outgoing emails
_addresses: dict[str, tuple[str, str]] = {}  # ticket -> (customer address, thread subject)


def clean_body(text: str) -> str:
    """Only what the customer wrote this time: drop the quoted thread and the signature."""
    t = (text or "").replace("\r\n", "\n")
    t = _QUOTED.sub("", t)
    t = _SIGNATURE.sub("", t)
    t = "\n".join(line for line in t.split("\n") if not line.startswith(">"))
    return re.sub(r"\s+", " ", t).strip()


def _customer_for(address: str) -> dict | None:
    from app.tools import mock_apis

    addr = address.lower()
    for pair in (get_settings().email_aliases or "").split(","):
        mail, _, cid = pair.partition(":")
        if mail.strip().lower() == addr and cid.strip():
            return mock_apis.get_customer(cid.strip())
    return mock_apis.find_customer(email=addr)


def _compose(session: CallSession, text: str) -> str:
    cust = session.customer
    hello = f"Hi {cust['name'].split()[0]}," if cust else "Hi there,"
    s = get_settings()
    text = re.sub(r"^(?:hi|hello|hey|dear)\b[^,.!\n]{0,40}[,!.]\s*", "", text.strip(), flags=re.I)  # the greeting is ours
    text = re.sub(r"\s*(?:warm regards|best regards|regards|thanks|cheers),?\s*(?:riya)?[^.!?]*$", "", text, flags=re.I).strip() or text
    return f"{hello}\n\n{text}\n\nWarm regards,\n{s.agent_name}\n{s.business_name} Support\nTicket {session.ticket_id}"


def _send(mail: Mail) -> None:
    s = get_settings()
    if s.email_redirect_to and mail.to.lower() != s.email_redirect_to.lower():
        mail.intended_for, mail.to = mail.to, s.email_redirect_to
        note = f"[Demo redirect: this email was addressed to {mail.intended_for}]\n\n"
        mail.body = note + mail.body
    if s.email_smtp_host and s.email_address and s.email_password:
        try:
            msg = EmailMessage()
            msg["From"], msg["To"], msg["Subject"] = f"{s.agent_name} at {s.business_name} <{s.email_address}>", mail.to, mail.subject
            msg["X-Resolvyn"] = "1"  # lets the mailbox watcher recognise (and ignore) our own emails
            msg.set_content(mail.body)
            if mail.html:
                msg.add_alternative(mail.html, subtype="html")
            with smtplib.SMTP_SSL(s.email_smtp_host, s.email_smtp_port, timeout=20) as smtp:
                smtp.login(s.email_address, s.email_password)
                smtp.send_message(msg)
            mail.delivered = "smtp"
        except Exception as e:  # noqa: BLE001 - never lose the reply because the mail server hiccuped
            mail.delivered = f"smtp failed: {type(e).__name__}"
            print(f"[email] send failed: {e}", flush=True)
    OUTBOX.append(mail)
    if mail.ticket_id != "TEST":
        tickets.add_event(mail.ticket_id, "Resolvyn", "EMAIL_SENT", f"Email sent to {mail.to}: {mail.subject}",
                          status="COMPLETED", meta={"delivered": mail.delivered, "kind": mail.kind, "to": mail.to})
    hub.to_ops({"type": "email", "mail": {k: v for k, v in mail.__dict__.items() if k != "html"}})


async def _mailer(session: CallSession) -> None:
    """Everything Riya says in this thread becomes an email: replies, and follow-ups after a human acts."""
    q = hub.subscribe_session(session.session_id)
    parts: list[str] = []
    try:
        while not session.closed:
            ev = await q.get()
            if ev.get("type") == "agent_sentence" and not ev.get("filler") and ev.get("text"):
                parts.append(ev["text"].strip())
            elif ev.get("type") == "agent_done" and parts:
                to, subject = _addresses[session.ticket_id]
                _send(Mail(to=to, subject=subject, body=_compose(session, " ".join(parts)), ticket_id=session.ticket_id))
                parts = []
    finally:
        hub.unsubscribe_session(session.session_id, q)


def _session_for(ticket_id: str | None, sender: str) -> tuple[CallSession, bool]:
    """The live session of this thread, or a new one. A thread whose session is gone is picked up again."""
    if ticket_id and tickets.get(ticket_id):
        s = sessions.by_ticket(ticket_id)
        if s and not s.closed and s.channel == "Email":
            return s, False
        s = sessions.create(channel="Email", customer=_customer_for(sender))
        s.ticket_id = ticket_id
        s.history = [{"role": "user" if m["sender"] == "CUSTOMER" else "assistant", "content": m["content"]}
                     for m in tickets.messages(ticket_id)][-10:]
        return s, False
    return sessions.create(channel="Email", customer=_customer_for(sender)), True


async def receive(sender: str, subject: str, body: str, ticket_id: str | None = None, timeout: float = 90) -> dict:
    """Handle one incoming email; returns the reply Riya sent (or None if she stayed quiet, e.g. a human took over)."""
    address = parseaddr(sender)[1] or sender
    text = clean_body(body)
    if not text:
        raise ValueError("The email has no text")
    m = THREAD.search(subject or "")
    tid = ticket_id or (m.group(1) if m else None)
    session, new = _session_for(tid, address)
    if new:
        await conversation.start(session, greet=False)
        base = _RE_PREFIX.sub("", subject or "").strip() or text[:60]
        tickets.update(session.ticket_id, subject=base[:120])
    plain = THREAD.sub("", _RE_PREFIX.sub("", subject or "")).strip() or (tickets.get(session.ticket_id).subject or "Your request")
    thread_subject = f"Re: {plain} [{session.ticket_id}]"
    _addresses[session.ticket_id] = (address, thread_subject)
    if session.session_id not in _mailers or _mailers[session.session_id].done():
        _mailers[session.session_id] = asyncio.create_task(_mailer(session))
        await asyncio.sleep(0)  # let the mailer subscribe before the reply streams

    sent_before = sum(1 for x in OUTBOX if x.ticket_id == session.ticket_id)
    tickets.add_event(session.ticket_id, "Resolvyn", "EMAIL_RECEIVED", f"Email from {address}: {subject or '(no subject)'}", status="COMPLETED")
    conversation.submit(session, text)
    loop = asyncio.get_running_loop()
    end = loop.time() + timeout
    while loop.time() < end:
        await asyncio.sleep(0.2)
        mine = [x for x in OUTBOX if x.ticket_id == session.ticket_id]
        if len(mine) > sent_before:
            return {"ticket_id": session.ticket_id, "reply": mine[-1].__dict__}
        if session.human_active and session.task and session.task.done():
            break  # a person owns this thread now: they write the reply
    return {"ticket_id": session.ticket_id, "reply": None}


def thread(ticket_id: str) -> list[dict]:
    """The conversation as emails, oldest first."""
    t = tickets.get(ticket_id)
    who = t.customer_name if t and t.customer_name else "Customer"
    to, subject = _addresses.get(ticket_id, ("", f"[{ticket_id}]"))
    out = []
    for msg in tickets.messages(ticket_id):
        mine = msg["sender"] == "CUSTOMER"
        out.append({"from": who if mine else f"{get_settings().agent_name} (Nova Retail Support)", "incoming": mine,
                    "subject": subject if not mine else subject.replace("Re: ", "", 1), "body": msg["content"],
                    "time": msg["timestamp"]})
    return out


# ── a real mailbox (optional) ────────────────────────────────────────────────


def _known_senders() -> set[str]:
    """Addresses Riya may answer by email: the customers on file (anyone else who writes to this inbox is left alone)."""
    from sqlmodel import Session, select

    from app.database import engine
    from app.models import Customer

    with Session(engine) as s:
        return {c.email.lower() for c in s.exec(select(Customer)).all() if c.email}


def _fetch_unseen() -> list[tuple[str, str, str]]:
    s = get_settings()
    known = _known_senders()
    box = imaplib.IMAP4_SSL(s.email_imap_host)
    try:
        box.login(s.email_address, s.email_password)
        box.select("INBOX")
        _, data = box.search(None, "UNSEEN")
        mails = []
        for num in (data[0].split() if data and data[0] else [])[:10]:
            _, head = box.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM X-RESOLVYN)])")  # PEEK: reading it does not mark it as read
            hdr = email.message_from_bytes(head[0][1])
            if hdr.get("X-Resolvyn"):
                continue  # one of our own emails (it can land in this same inbox when a customer's address is the support address)
            if parseaddr(hdr.get("From", ""))[1].lower() not in known:
                continue
            _, raw = box.fetch(num, "(BODY.PEEK[])")
            msg = email.message_from_bytes(raw[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                        body = part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="replace")
                        break
            else:
                body = msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="replace")
            sender = parseaddr(msg.get("From", ""))[1]
            mails.append((sender, str(msg.get("Subject", "")), body))
            box.store(num, "+FLAGS", "\\Seen")  # only mail we actually answer is marked as read
        return mails
    finally:
        try:
            box.logout()
        except Exception:  # noqa: BLE001
            pass


async def poll_mailbox() -> None:
    """Pick up real email every few seconds (only when EMAIL_IMAP_HOST / EMAIL_ADDRESS / EMAIL_PASSWORD are set)."""
    s = get_settings()
    if not (s.email_imap_host and s.email_address and s.email_password):
        return
    print(f"[email] watching {s.email_address} for customer emails", flush=True)
    while True:
        try:
            for sender, subject, body in await asyncio.to_thread(_fetch_unseen):
                asyncio.create_task(receive(sender, subject, body))
        except Exception as e:  # noqa: BLE001
            print(f"[email] mailbox check failed: {type(e).__name__}: {e}", flush=True)
        await asyncio.sleep(s.email_poll_seconds)


# ── the summary after a call or chat ─────────────────────────────────────────

_STATUS_TEXT = {
    "RESOLVED": "Resolved",
    "WAITING_FOR_HUMAN": "With our team",
    "ACTIVE": "In progress",
    "VERIFYING": "Being verified",
}


_TOPIC = {
    "Duplicate Payment": "a duplicate payment",
    "Refund Request": "a refund",
    "Refund Status": "the status of a refund",
    "Payment Failure": "a failed payment",
    "Billing Query": "a billing question",
    "Account Access": "getting into your account",
    "Profile Update": "updating your account details",
    "Shipping Delay": "where your order is",
    "Order Issue": "your order",
    "Technical Issue": "a problem with your product",
}


def _customer_address(t) -> str | None:
    from sqlmodel import Session

    from app.database import engine
    from app.models import Customer

    if t.customer_id:
        with Session(engine) as s:
            c = s.get(Customer, t.customer_id)
        if c and c.email:
            return c.email
    known = _addresses.get(t.ticket_id)
    return known[0] if known else None


def _summary_lines(t) -> dict:
    """Everything the customer should be able to read afterwards, from verified data only (never model prose)."""
    from app.context_engine.context_engine import _verified_facts
    from app.tools import mock_apis

    done: list[str] = []
    if t.order_id:
        try:
            for r in mock_apis.refunds_for_order(t.order_id):
                state = "confirmed" if r["status"] == "COMPLETED" else r["status"].lower()
                done.append(f"Refund {r['refund_id']} of ₹{int(r['amount']):,} ({state}). It reaches the original payment method in 3 to 5 working days.")
        except Exception:  # noqa: BLE001
            pass
    listed = " ".join(done)
    for f in _verified_facts(t.ticket_id)[:4]:
        refs = re.findall(r"RFD-\d+", f)
        if any(r in listed for r in refs) or f in done or "waiting for human approval" in f.lower():
            continue  # already said in a clearer sentence above
        done.append(f)
    topic = _TOPIC.get(t.intent or "", "")
    if topic:
        asked = topic + (f" (order {t.order_id})" if t.order_id else "")
    else:
        raw = (t.subject or "").strip()
        asked = raw if len(raw) <= 90 else raw[:90].rsplit(" ", 1)[0].rstrip(",.;:- ") + "…"
        asked = asked if raw and raw != "New conversation" else "your request"
    return {"asked": asked, "done": done[:5]}


def _summary_mail(t, kind: str) -> tuple[str, str, str]:
    s = get_settings()
    first = (t.customer_name or "there").split()[0]
    word = {"Call": "call", "Text": "chat"}.get(t.channel, "conversation")
    info = _summary_lines(t)
    status = _STATUS_TEXT.get(t.status, t.status.replace("_", " ").title())
    if kind == "escalated":
        outcome = (f"I have passed this to {t.assignee or 'a specialist on our team'}, with the full conversation, so you will not need to repeat anything. "
                   "They will follow up with you.")
    elif t.status == "RESOLVED":
        outcome = "Everything we discussed is sorted. If something does not look right, just reply to this email and it will reopen this ticket."
    else:
        outcome = "This is still open. Reply to this email any time and we will pick up from here."
    subject = f"Your Nova Retail support summary [{t.ticket_id}]"
    lines = [f"Hi {first},", "", f"Thanks for your {word} with us today. Here is a summary for your records.", "",
             f"You asked about: {info['asked']}"]
    if info["done"]:
        lines += ["", "What we did:"] + [f"  - {d}" for d in info["done"]]
    lines += ["", f"Status: {status}", outcome, "", f"Ticket reference: {t.ticket_id}", "", "Warm regards,", s.agent_name, f"{s.business_name} Support"]
    text = "\n".join(lines)
    esc = _html.escape  # anything a customer typed must not become markup in the email
    rows = "".join(f'<li style="margin:4px 0">{esc(d)}</li>' for d in info["done"])
    html = f"""<!doctype html><html><body style="margin:0;background:#f4f4f5;font-family:-apple-system,Segoe UI,Helvetica,Arial,sans-serif;color:#18181b">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center" style="padding:28px 12px">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border:1px solid #e4e4e7;border-radius:10px">
<tr><td style="padding:22px 28px;border-bottom:1px solid #e4e4e7;font-size:13px;letter-spacing:.14em;font-weight:600">{s.business_name.upper()} SUPPORT</td></tr>
<tr><td style="padding:26px 28px;font-size:15px;line-height:1.6">
<p style="margin:0 0 14px">Hi {esc(first)},</p>
<p style="margin:0 0 18px">Thanks for your {word} with us today. Here is a summary for your records.</p>
<p style="margin:0 0 4px;font-size:12px;color:#71717a;text-transform:uppercase;letter-spacing:.06em">You asked about</p>
<p style="margin:0 0 18px">{esc(info['asked'])}</p>
{('<p style="margin:0 0 4px;font-size:12px;color:#71717a;text-transform:uppercase;letter-spacing:.06em">What we did</p><ul style="margin:0 0 18px;padding-left:18px">' + rows + '</ul>') if rows else ''}
<table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 18px;background:#fafafa;border:1px solid #e4e4e7;border-radius:8px;width:100%"><tr>
<td style="padding:12px 16px;font-size:13px"><span style="color:#71717a">Status</span><br><strong>{status}</strong></td>
<td style="padding:12px 16px;font-size:13px"><span style="color:#71717a">Ticket</span><br><strong>{t.ticket_id}</strong></td></tr></table>
<p style="margin:0 0 18px">{esc(outcome)}</p>
<p style="margin:0">Warm regards,<br>{s.agent_name}<br><span style="color:#71717a">{s.business_name} Support</span></p>
</td></tr></table></td></tr></table></body></html>"""
    return subject, text, html


def send_summary(ticket_id: str, kind: str = "resolved") -> Mail | None:
    """Email the customer what happened on their call or chat. Once per outcome (resolved / escalated) per ticket."""
    s = get_settings()
    t = tickets.get(ticket_id)
    if not s.email_summaries or not t or t.channel == "Email":  # an email thread already is the record
        return None
    if any(e["event_type"] == "SUMMARY_EMAILED" and e["meta"].get("kind") == kind for e in tickets.events(ticket_id)):
        return None
    if t.subject in (None, "", "Call ended without a request") or t.subject == "New conversation":
        return None  # nothing was asked
    to = _customer_address(t)
    if not to:
        tickets.add_event(ticket_id, "Resolvyn", "SUMMARY_SKIPPED", "No email address on file: summary not sent", status="COMPLETED")
        return None
    subject, text, html = _summary_mail(t, kind)
    mail = Mail(to=to, subject=subject, body=text, ticket_id=ticket_id, html=html, kind="summary")
    tickets.add_event(ticket_id, "Resolvyn", "SUMMARY_EMAILED", f"Summary emailed to {to}", status="COMPLETED", meta={"kind": kind})
    _send(mail)
    return mail


def status() -> dict:
    s = get_settings()
    return {
        "inbox": s.email_address if s.email_imap_host and s.email_password else None,
        "smtp": bool(s.email_smtp_host and s.email_password),
        "sent": len(OUTBOX),
        "address": s.email_address or "support@novaretail.example",
        "redirect_to": s.email_redirect_to,
        "summaries": s.email_summaries,
    }
