"""Email channel: an email is a conversation turn through the same pipeline as a call, and every call or chat ends with a summary.

Inbound   a customer's email goes through Jev, memory, the department desks and their tools, the human approval gate,
          escalation and the truth guard, exactly like speech. A thread stays on one ticket (the subject carries [PH-1234],
          and In-Reply-To / References are honoured), so a reply continues the same conversation.
Outbound  Riya's reply is emailed in the same thread; anything she says later on her own (a refund approved by the manager) is
          emailed too. After a call or chat the customer gets a SUMMARY of what was discussed and decided, never the transcript.

Protocols followed
  * MIME multipart/alternative (text/plain + text/html, UTF-8) with the logo as an inline related part, RFC 5322 headers
    (Date, Message-ID, Reply-To), threading with In-Reply-To and References.
  * RFC 3834: everything we send is marked Auto-Submitted, so vacation responders and other robots do not answer it, and
    anything that is itself automated (Auto-Submitted, Precedence: bulk, mailer-daemon, out-of-office) is never answered.
  * Our own mail carries X-Resolvyn, so it is ignored if it lands in the inbox we watch; a per-ticket cap stops ping-pong.
  * Transport: SMTP over TLS (port 465) or STARTTLS (587) with authentication; IMAP over TLS with BODY.PEEK so mail we do not
    answer stays unread. SPF, DKIM and DMARC are applied by the sending provider (Gmail signs mail from its own accounts).

Three ways in: the customer side's "Email us" panel and POST /api/email/inbound (the simulated inbox used in the demo);
the same endpoint as an inbound-parse webhook; or a real mailbox (EMAIL_IMAP_* / EMAIL_SMTP_*, a Gmail app password works).
"""

import asyncio
import email
import imaplib
import re
import smtplib
import socket
import ssl
import time
from dataclasses import dataclass, field
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid, parseaddr
from pathlib import Path

from app.config import get_settings
from app.services import conversation, email_render, email_summary
from app.services import ticket_service as tickets
from app.services.realtime import hub
from app.services.sessions import CallSession, sessions
from app.utils import utcnow

THREAD = re.compile(r"\[(PH-\d+)\]")
_RE_PREFIX = re.compile(r"^(?:(?:re|fwd?|fw|aw|sv)\s*:\s*)+", re.I)
_QUOTED = re.compile(r"(?ms)^(?:On .{5,200}wrote:|-{2,} ?Original Message ?-{2,}|From: .+?Sent: ).*\Z")
_SIGNATURE = re.compile(r"(?ms)^(?:-- ?$|Sent from my \w+).*\Z")
_LOGO = Path(__file__).parent / "assets" / "logo.png"
MAX_AUTO_EMAILS_PER_HOUR = 8  # per ticket: a hard stop against two robots answering each other

_AUTOMATED_SENDERS = re.compile(r"^(?:mailer-daemon|postmaster|no-?reply|do-?not-?reply|bounce|notifications?)\b", re.I)
_AUTOMATED_SUBJECT = re.compile(r"^(?:automatic reply|auto(?:matic)?[- ]?reply|out of office|undeliverable|delivery status notification|failure notice)", re.I)


@dataclass
class Mail:
    to: str
    subject: str
    body: str  # the plain-text alternative
    ticket_id: str
    sent_at: str = field(default_factory=lambda: utcnow().isoformat())
    delivered: str = "simulated inbox"  # or "smtp"
    html: str | None = None
    kind: str = "reply"  # reply | summary | test
    intended_for: str | None = None  # set when EMAIL_REDIRECT_TO redirected it
    message_id: str = ""
    in_reply_to: str = ""
    references: list[str] = field(default_factory=list)
    raw: bytes = b""  # the message exactly as it goes on the wire

    def public(self, with_html: bool = True) -> dict:
        d = {k: v for k, v in self.__dict__.items() if k != "raw"}
        d["size"] = len(self.raw)
        if not with_html:
            d.pop("html", None)
        return d


OUTBOX: list[Mail] = []  # every email Riya sent (newest last), for the demo inbox, tests and the console
_mailers: dict[str, asyncio.Task] = {}  # session -> task that turns what Riya says into outgoing emails
_addresses: dict[str, tuple[str, str]] = {}  # ticket -> (customer address, thread subject)
_thread_ids: dict[str, list[str]] = {}  # ticket -> Message-IDs seen in the thread (in and out), oldest first
_msgid_ticket: dict[str, str] = {}  # Message-ID -> ticket, for replies that lost the [PH-] tag


class Automated(Exception):
    """The message is itself automated (auto-reply, bounce, mailing list): answering it could start a loop."""


def clean_body(text: str) -> str:
    """Only what the customer wrote this time: drop the quoted thread and the signature."""
    t = (text or "").replace("\r\n", "\n")
    t = _QUOTED.sub("", t)
    t = _SIGNATURE.sub("", t)
    t = "\n".join(line for line in t.split("\n") if not line.startswith(">"))
    return re.sub(r"\s+", " ", t).strip()


def is_automated(headers: dict | None, sender: str, subject: str) -> str | None:
    """Why this message must not be answered (or None). Headers are matched case-insensitively."""
    h = {k.lower(): str(v) for k, v in (headers or {}).items()}
    if h.get("x-resolvyn"):
        return "sent by Resolvyn"
    if h.get("auto-submitted", "no").strip().lower() not in ("", "no"):
        return f"Auto-Submitted: {h['auto-submitted']}"
    if h.get("precedence", "").strip().lower() in ("bulk", "junk", "list", "auto_reply"):
        return f"Precedence: {h['precedence']}"
    if h.get("x-autoreply") or h.get("x-autorespond"):
        return "auto-responder"
    if _AUTOMATED_SENDERS.match(parseaddr(sender)[1].split("@")[0]):
        return "automated sender"
    if _AUTOMATED_SUBJECT.match((subject or "").strip()):
        return "auto-reply subject"
    return None


def _customer_for(address: str) -> dict | None:
    from app.tools import mock_apis

    addr = address.lower()
    for pair in (get_settings().email_aliases or "").split(","):
        mail, _, cid = pair.partition(":")
        if mail.strip().lower() == addr and cid.strip():
            return mock_apis.get_customer(cid.strip())
    return mock_apis.find_customer(email=addr)


# ── building and sending ─────────────────────────────────────────────────────


def build_message(mail: Mail) -> EmailMessage:
    """The message exactly as it goes on the wire: multipart/alternative with an inline logo, threading and RFC 3834 headers."""
    s = get_settings()
    from_addr = s.email_address or "support@novaretail.example"
    msg = EmailMessage()
    msg["From"] = formataddr((f"{s.agent_name} at {s.business_name}", from_addr))
    msg["To"] = mail.to
    msg["Reply-To"] = from_addr
    msg["Subject"] = mail.subject
    msg["Date"] = formatdate(localtime=True)
    mail.message_id = mail.message_id or make_msgid(domain=from_addr.split("@")[-1])
    msg["Message-ID"] = mail.message_id
    if mail.in_reply_to:
        msg["In-Reply-To"] = mail.in_reply_to
    if mail.references:
        msg["References"] = " ".join(mail.references[-10:])
    msg["Auto-Submitted"] = "auto-generated" if mail.kind == "summary" else "auto-replied"  # RFC 3834
    msg["X-Auto-Response-Suppress"] = "All"
    msg["X-Resolvyn"] = "1"
    msg["X-Resolvyn-Ticket"] = mail.ticket_id
    msg.set_content(mail.body, charset="utf-8", cte="quoted-printable")  # 7-bit safe on every hop
    if mail.html:
        msg.add_alternative(mail.html, subtype="html", cte="quoted-printable")
        if _LOGO.exists():
            msg.get_payload()[1].add_related(_LOGO.read_bytes(), "image", "png", cid=f"<{email_render.LOGO_CID}>",
                                             disposition="inline", filename="resolvyn-logo.png")
    return msg


def _v4_socket(host: str, port: int, timeout: float | None) -> socket.socket:
    """A connected IPv4 socket (getaddrinfo would otherwise offer IPv6 first, which some networks reset after the connect)."""
    addr = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)[0][4]
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    sock.connect(addr)
    return sock


def smtp_connect() -> smtplib.SMTP:
    """An SMTP connection to the configured server: TLS from the first byte (ssl), or STARTTLS, or none for a local test server."""
    s = get_settings()
    ctx = ssl.create_default_context()
    v4 = s.email_force_ipv4
    if s.email_smtp_security == "ssl":
        cls = type("SMTP4SSL", (smtplib.SMTP_SSL,), {"_get_socket": lambda self, h, p, t: self.context.wrap_socket(_v4_socket(h, p, t), server_hostname=self._host)}) if v4 else smtplib.SMTP_SSL
        smtp = cls(s.email_smtp_host, s.email_smtp_port, timeout=20, context=ctx)
    else:
        cls = type("SMTP4", (smtplib.SMTP,), {"_get_socket": lambda self, h, p, t: _v4_socket(h, p, t)}) if v4 else smtplib.SMTP
        smtp = cls(s.email_smtp_host, s.email_smtp_port, timeout=20)
    smtp.ehlo()
    if s.email_smtp_security == "starttls":
        smtp.starttls(context=ctx)
        smtp.ehlo()
    return smtp


def imap_connect() -> imaplib.IMAP4_SSL:
    s = get_settings()
    if s.email_force_ipv4:
        cls = type("IMAP4SSL4", (imaplib.IMAP4_SSL,), {"_create_socket": lambda self, timeout=None: self.ssl_context.wrap_socket(_v4_socket(self.host, self.port, timeout), server_hostname=self.host)})
    else:
        cls = imaplib.IMAP4_SSL
    return cls(s.email_imap_host)


def _smtp_ready() -> bool:
    s = get_settings()
    return bool(s.email_smtp_host and s.email_address and (s.email_password or s.email_smtp_security == "none"))


def _smtp_send(msg: EmailMessage) -> None:
    s = get_settings()
    with smtp_connect() as smtp:
        if s.email_password:
            smtp.login(s.email_address, s.email_password.replace(" ", ""))
        smtp.send_message(msg)


def _recent_auto_count(ticket_id: str) -> int:
    cutoff = time.time() - 3600
    return sum(1 for m in OUTBOX if m.ticket_id == ticket_id and m.kind != "test" and getattr(m, "_t", 0) > cutoff)


def _send(mail: Mail) -> None:
    s = get_settings()
    if s.email_redirect_to and mail.to.lower() != s.email_redirect_to.lower():
        mail.intended_for, mail.to = mail.to, s.email_redirect_to
        mail.body = f"[Demo redirect: this email was addressed to {mail.intended_for}]\n\n" + mail.body
    ids = _thread_ids.setdefault(mail.ticket_id, [])
    if ids and not mail.in_reply_to:
        mail.in_reply_to, mail.references = ids[-1], list(ids)
    msg = build_message(mail)
    mail.raw = msg.as_bytes()
    if _smtp_ready():
        try:
            _smtp_send(msg)
            mail.delivered = "smtp"
        except Exception as e:  # noqa: BLE001 - never lose the reply because the mail server hiccuped
            mail.delivered = f"smtp failed: {type(e).__name__}"
            print(f"[email] send failed: {type(e).__name__}: {e}", flush=True)
    mail._t = time.time()  # type: ignore[attr-defined]
    ids.append(mail.message_id)
    _msgid_ticket[mail.message_id] = mail.ticket_id
    OUTBOX.append(mail)
    if mail.ticket_id != "TEST":
        tickets.add_event(mail.ticket_id, "Resolvyn", "EMAIL_SENT", f"Email sent to {mail.to}: {mail.subject}",
                          status="COMPLETED", meta={"delivered": mail.delivered, "kind": mail.kind, "to": mail.to})
    hub.to_ops({"type": "email", "mail": mail.public(with_html=False)})


async def _mailer(session: CallSession) -> None:
    """Everything Riya says in this email thread becomes an email: replies, and follow-ups after a human acts."""
    q = hub.subscribe_session(session.session_id)
    parts: list[str] = []
    try:
        while not session.closed:
            ev = await q.get()
            if ev.get("type") == "agent_sentence" and not ev.get("filler") and ev.get("text"):
                parts.append(ev["text"].strip())
            elif ev.get("type") == "agent_done" and parts:
                to, subject = _addresses[session.ticket_id]
                if _recent_auto_count(session.ticket_id) >= MAX_AUTO_EMAILS_PER_HOUR:
                    tickets.add_event(session.ticket_id, "Resolvyn", "EMAIL_SUPPRESSED", "Reply not emailed: hourly limit for this thread reached", status="COMPLETED")
                    parts = []
                    continue
                first = (session.customer["name"].split()[0] if session.customer else "there")
                paras = email_render.strip_greeting(" ".join(parts))
                _send(Mail(to=to, subject=subject, ticket_id=session.ticket_id, kind="reply",
                           body=email_render.reply_text(first_name=first, paragraphs=paras, ticket_id=session.ticket_id),
                           html=email_render.reply_html(first_name=first, paragraphs=paras, ticket_id=session.ticket_id, subject=subject)))
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
        t = tickets.get(ticket_id)
        s.state.update(problem_stated=True, order_id=t.order_id, department=t.assigned_agent, customer_id=t.customer_id)
        tickets.update(ticket_id, session_id=s.session_id)  # the email thread now owns the ticket
        if t.status == "RESOLVED":  # the customer wrote back: the ticket is open again
            tickets.update(ticket_id, status="ACTIVE", resolved_at=None)
            tickets.add_event(ticket_id, "Resolvyn", "TICKET_REOPENED", "Ticket reopened: the customer replied by email", status="COMPLETED")
        s.history = [{"role": "user" if m["sender"] == "CUSTOMER" else "assistant", "content": m["content"]}
                     for m in tickets.messages(ticket_id)][-10:]
        return s, False
    return sessions.create(channel="Email", customer=_customer_for(sender)), True


async def receive(sender: str, subject: str, body: str, ticket_id: str | None = None, timeout: float = 90, *,
                  headers: dict | None = None) -> dict:
    """Handle one incoming email; returns the reply Riya sent (or None if she stayed quiet, e.g. a human took over)."""
    address = parseaddr(sender)[1] or sender
    why = is_automated(headers, sender, subject)
    if why:
        return {"ticket_id": None, "reply": None, "skipped": why}
    text = clean_body(body)
    if not text:
        raise ValueError("The email has no text")
    h = {k.lower(): v for k, v in (headers or {}).items()}
    tid = ticket_id
    if not tid:
        m = THREAD.search(subject or "")
        tid = m.group(1) if m else None
    if not tid:  # a reply that lost the subject tag still carries In-Reply-To / References
        for ref in reversed(re.findall(r"<[^>]+>", (h.get("in-reply-to", "") + " " + h.get("references", "")))):
            if ref in _msgid_ticket:
                tid = _msgid_ticket[ref]
                break
    session, new = _session_for(tid, address)
    if new:
        await conversation.start(session, greet=False)
        base = _RE_PREFIX.sub("", subject or "").strip() or text[:60]
        tickets.update(session.ticket_id, subject=base[:120])
    plain = THREAD.sub("", _RE_PREFIX.sub("", subject or "")).strip() or (tickets.get(session.ticket_id).subject or "Your request")
    thread_subject = f"Re: {plain} [{session.ticket_id}]"
    _addresses[session.ticket_id] = (address, thread_subject)
    if h.get("message-id"):
        _thread_ids.setdefault(session.ticket_id, []).append(h["message-id"])
        _msgid_ticket[h["message-id"]] = session.ticket_id
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
            return {"ticket_id": session.ticket_id, "reply": mine[-1].public()}
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


def _text_of(msg: email.message.Message) -> str:
    """text/plain if there is one, otherwise the text of the HTML part."""
    plain = html = ""
    for part in msg.walk() if msg.is_multipart() else [msg]:
        if part.get_content_maintype() != "text" or part.get("Content-Disposition", "").startswith("attachment"):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        txt = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if part.get_content_subtype() == "plain" and not plain:
            plain = txt
        elif part.get_content_subtype() == "html" and not html:
            html = txt
    if plain:
        return plain
    return re.sub(r"\s+", " ", re.sub(r"(?is)<(script|style).*?</\1>|<[^>]+>", " ", html)).strip()


def _fetch_unseen() -> list[dict]:
    s = get_settings()
    known = _known_senders()
    box = imap_connect()
    try:
        box.login(s.email_address, s.email_password.replace(" ", ""))
        box.select("INBOX")
        _, data = box.search(None, "UNSEEN")
        mails = []
        for num in (data[0].split() if data and data[0] else [])[:10]:
            _, head = box.fetch(num, "(BODY.PEEK[HEADER.FIELDS (FROM SUBJECT AUTO-SUBMITTED PRECEDENCE X-RESOLVYN X-AUTOREPLY)])")  # PEEK: stays unread
            hdr = email.message_from_bytes(head[0][1])
            if hdr.get("X-Resolvyn"):
                continue  # one of our own emails (it can land in this same inbox when a customer's address is the support address)
            if parseaddr(hdr.get("From", ""))[1].lower() not in known:
                continue
            if is_automated({k: str(v) for k, v in hdr.items()}, hdr.get("From", ""), str(hdr.get("Subject", ""))):
                box.store(num, "+FLAGS", "\\Seen")
                continue
            _, raw = box.fetch(num, "(BODY.PEEK[])")
            msg = email.message_from_bytes(raw[0][1])
            mails.append({
                "sender": parseaddr(msg.get("From", ""))[1], "subject": str(email.header.make_header(email.header.decode_header(msg.get("Subject", "")))),
                "body": _text_of(msg),
                "headers": {k: str(msg.get(k, "")) for k in ("Message-ID", "In-Reply-To", "References", "Auto-Submitted", "Precedence")},
            })
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
            for m in await asyncio.to_thread(_fetch_unseen):
                asyncio.create_task(receive(m["sender"], m["subject"], m["body"], headers=m["headers"]))
        except Exception as e:  # noqa: BLE001
            print(f"[email] mailbox check failed: {type(e).__name__}: {e}", flush=True)
        await asyncio.sleep(s.email_poll_seconds)


# ── the summary after a call or chat ─────────────────────────────────────────


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


def send_summary(ticket_id: str, kind: str = "resolved") -> Mail | None:
    """Email the customer a summary of their call or chat. Once per outcome (resolved / escalated) per ticket."""
    s = get_settings()
    t = tickets.get(ticket_id)
    if not s.email_summaries or not t or t.channel == "Email":  # an email thread already is the record
        return None
    if any(e["event_type"] == "SUMMARY_EMAILED" and e["meta"].get("kind") == kind for e in tickets.events(ticket_id)):
        return None
    if t.subject in (None, "", "Call ended without a request", "New conversation"):
        return None  # nothing was asked
    to = _customer_address(t)
    if not to:
        tickets.add_event(ticket_id, "Resolvyn", "SUMMARY_SKIPPED", "No email address on file: summary not sent", status="COMPLETED")
        return None
    sm = email_summary.build(ticket_id, kind)
    if sm is None:
        return None
    mail = Mail(to=to, subject=email_render.summary_subject(sm), ticket_id=ticket_id, kind="summary",
                body=email_render.summary_text(sm), html=email_render.summary_html(sm))
    tickets.add_event(ticket_id, "Resolvyn", "SUMMARY_EMAILED", f"Summary emailed to {to}", status="COMPLETED", meta={"kind": kind})
    _send(mail)
    return mail


def status() -> dict:
    s = get_settings()
    return {
        "inbox": s.email_address if s.email_imap_host and s.email_password else None,
        "smtp": _smtp_ready(),
        "security": s.email_smtp_security,
        "sent": len(OUTBOX),
        "address": s.email_address or "support@novaretail.example",
        "redirect_to": s.email_redirect_to,
        "summaries": s.email_summaries,
    }
