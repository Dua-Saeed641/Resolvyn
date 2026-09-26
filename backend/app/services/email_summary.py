"""What a customer gets after a call or chat: a summary of what was discussed and decided, never the conversation itself.

Everything here is derived from verified records: the tool calls (orders, payments, refunds, shipments, account state),
human approvals, first-time-bug suggestions and the escalation, plus the answer given to information questions.
No model writes this, so nothing in the email can be invented, and it reads the same with or without a language model.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime

from app.services import ticket_service as tickets

_STATUS = {
    "RESOLVED": ("resolved", "Resolved"),
    "WAITING_FOR_HUMAN": ("team", "With our team"),
    "VERIFYING": ("progress", "Being verified"),
    "ACTIVE": ("progress", "In progress"),
}
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@dataclass
class Topic:
    title: str
    points: list[str]
    turn: int = 0  # the turn where it first came up, so topics read in the order they were discussed


@dataclass
class Summary:
    ticket_id: str
    first_name: str
    channel_word: str  # call | chat | conversation
    when: str  # "26 Sep 2026"
    duration: str  # "about 4 minutes" or ""
    status_key: str  # resolved | team | progress
    status_label: str
    handled_by: str
    topics: list[Topic] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
    references: list[tuple[str, str]] = field(default_factory=list)
    headline: str = ""

    @property
    def topic_titles(self) -> str:
        names = [t.title.lower() for t in self.topics]
        if not names:
            return "your request"
        return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def rupees(n) -> str:
    return f"₹{int(n):,}"


def _day(iso: str) -> str:
    """2026-09-20 -> 20 Sep"""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    return f"{int(m.group(3))} {_MONTHS[int(m.group(2)) - 1]}" if m else (iso or "")


def _parse(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "").replace(" ", "T")[:19])
    except (ValueError, AttributeError):
        return None


_SPOKEN_OPENER = re.compile(
    r"^(?:(?:right|okay|ok|yeah|yep|sure|mm-?hmm|hmm|umm?|uh|so|well|alright|acha|haan|got it|one sec|one moment|hold on)[,.!\s]*)+$", re.I)


def _first_sentences(text: str, n: int = 2, limit: int = 240) -> str:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text or "").strip())
    while len(parts) > 1 and (_SPOKEN_OPENER.match(parts[0]) or len(parts[0].split()) <= 3 and not re.search(r"\d", parts[0])):
        parts = parts[1:]  # spoken openers ("Right, right.") do not belong in a written summary
    parts[0] = re.sub(r"^(?:(?:right|okay|ok|yeah|sure|mm-?hmm|hmm|so|well)[,.]?\s+)+", "", parts[0], flags=re.I)
    out = " ".join(parts[:n]).strip()
    if len(out) > limit:
        out = out[:limit].rsplit(" ", 1)[0].rstrip(",;:- ") + "…"
    return out


def _by_tool(calls: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for c in calls:
        if c["status"] == "COMPLETED" and c.get("response") is not None:
            out.setdefault(c["tool_name"], []).append(c["response"])
    return out


def _traces(detail: dict) -> list[dict]:
    return [e["meta"]["trace"] for e in detail["events"] if e["event_type"] == "TURN_TRACE" and e.get("meta", {}).get("trace")]


# ── topics ───────────────────────────────────────────────────────────────────


def _payment_topic(detail: dict, tools: dict) -> Topic | None:
    points: list[str] = []
    order = next((o for o in tools.get("get_order", []) if o and o.get("order_id") == detail.get("order_id")), None) \
        or next((r["order"] for r in tools.get("lookup_order", []) if r.get("found")), None)
    if order:
        points.append(f"Order {order['order_id']}: {order['item']} ({rupees(order['amount'])}), placed {_day(order['placed'])}.")
    txns = tools.get("get_payment_transactions", [[]])[-1] if tools.get("get_payment_transactions") else []
    ok = [t for t in txns if t["status"] == "SUCCESS"]
    policy = next((p for p in tools.get("check_refund_policy", []) if p.get("eligible")), None)
    if len(ok) >= 2 and ok[0]["amount"] == ok[1]["amount"]:
        a, b = _parse(ok[0]["timestamp"]), _parse(ok[1]["timestamp"])
        gap = f", {int(abs((b - a).total_seconds()))} seconds apart" if a and b else ""
        points.append(f"We found two successful charges of {rupees(ok[0]['amount'])} on {ok[0]['method']}{gap}. "
                      f"The second ({ok[1]['transaction_id']}) was a duplicate.")
    elif txns:
        points.append(f"Payment on record: {rupees(ok[0]['amount'])} on {ok[0]['method']}." if ok else "No successful payment was found on the order.")
    approvals = [h for h in detail["human_actions"] if h["event_type"] == "APPROVAL"]
    pend = next((p for p in detail["pending_actions"] if p["action_type"] == "refund"), None)
    if pend:
        amt = pend["params"].get("amount", 0)
        if approvals:
            points.append(f"A refund of {rupees(amt)} needed a team lead's approval, and it was approved.")
        elif pend["status"] == "PENDING":
            points.append(f"A refund of {rupees(amt)} is waiting for a team lead's approval; nothing has been refunded yet.")
        elif pend["status"] == "REJECTED":
            points.append(f"The refund of {rupees(amt)} was reviewed by our team and not approved.")
    verified = next((v for v in reversed(tools.get("verify_refund", [])) if v.get("verified")), None)
    if verified:
        eta = "3 to 5 working days"
        method = (pend or {}).get("params", {}).get("method", "") or ""
        if method.lower().startswith("card"):
            eta += " (some banks take up to 7)"
        points.append(f"Refund {verified['refund_id']} of {rupees(verified['amount'])} was completed and verified. "
                      f"It returns to your original payment method in {eta}.")
    elif not pend and policy is None and not txns and not order:
        return None
    return Topic("Payment and refund", points) if points else None


def _order_topic(detail: dict, tools: dict) -> Topic | None:
    points: list[str] = []
    cancelled = next((c for c in tools.get("cancel_order", []) if c.get("ok")), None)
    order = next((o for o in reversed(tools.get("get_order", [])) if o), None) \
        or next((r["order"] for r in reversed(tools.get("lookup_order", [])) if r.get("found")), None)
    ship = tools.get("get_shipment", [None])[-1] if tools.get("get_shipment") else None
    if order:
        head = f"{order['item']} (order {order['order_id']}, {rupees(order['amount'])})"
        if cancelled:
            points.append(f"{head} was cancelled and the cancellation was verified. The refund of {rupees(order['amount'])} returns to your "
                          "original payment method in 3 to 5 working days.")
        elif ship:
            where = f" at the {ship['location']}" if ship.get("location") and ship["location"] != "Delivered" else ""
            line = f"{head} is {ship['status'].lower()}{where} with {ship['carrier']}."
            if ship.get("delayed"):
                line += f" The delay is due to {ship.get('delay_reason', 'a carrier issue').lower()}."
            if ship.get("eta") and ship["status"] != "Delivered":
                line += f" Expected delivery: {_day(ship['eta'])}."
            points.append(line)
        else:
            state = order["status"].lower()
            tail = " It has not shipped yet, so there is no tracking or delivery date." if order["status"] in ("Processing", "Confirmed") else ""
            points.append(f"{head} is {state}.{tail}")
    return Topic("Your order", points) if points else None


def _account_topic(detail: dict, tools: dict) -> Topic | None:
    points: list[str] = []
    ver = next((v for v in tools.get("verify_identity", []) if v.get("verified")), None)
    if ver:
        points.append(f"We verified your identity using your registered {ver.get('matched') or 'details'}.")
    acc = tools.get("get_account_status", [None])[0] if tools.get("get_account_status") else None
    unlocked = next((u for u in tools.get("unlock_account", []) if u.get("ok")), None)
    if acc and acc.get("status") == "LOCKED":
        why = acc.get("locked_reason", "").lower() or "too many failed sign-in attempts"
        points.append(f"Your account was locked ({why}).")
    if unlocked:
        points.append("We unlocked it and checked that it is active again.")
    reset = next((r for r in tools.get("send_reset_link", []) if r.get("ok")), None)
    if reset:
        points.append(f"A password reset link was sent to {reset['sent_to']}. It expires in {reset['expires_in_minutes']} minutes.")
    return Topic("Your account", points) if points else None


def _info_topics(traces: list[dict]) -> list[Topic]:
    """Questions answered from our documents (warranty, price, pick-up...): the topic and the gist of the answer."""
    out, seen = [], set()
    for t in traces:
        decision = t.get("decision") or {}
        reason = decision.get("reason", "")
        if t.get("tools") or decision.get("path") not in ("INSTANT", None) or reason.startswith(("No problem", "Caller", "Nothing concrete")):
            continue
        hits = (t.get("memory") or {}).get("hits") or []
        if not t.get("said") or not hits or hits[0]["score"] < 0.25 or hits[0]["kind"] in ("rule", "past_query", "bug"):
            continue
        title = re.split(r"\s+[—-]\s+", hits[0]["title"])[-1].strip(" .")[:60]
        if not title or title.lower() in seen:
            continue
        seen.add(title.lower())
        out.append(Topic(title[:1].upper() + title[1:], [_first_sentences(t["said"], 2, 220)], turn=t["turn"]))
    return out[:3]


def _bug_topic(detail: dict) -> Topic | None:
    if not detail["bugs"]:
        return None
    b = detail["bugs"][0]
    points = ["This was a new problem for us, so we passed it to our team lead instead of guessing."]
    if b.get("suggestion"):
        points.append(f"Suggested fix from our team: {_first_sentences(b['suggestion'], 2, 260)}")
    elif b["status"] == "OPEN":
        points.append("Our team lead is preparing a suggestion and will follow up.")
    return Topic("A new issue", points)


# ── the whole summary ────────────────────────────────────────────────────────


def build(ticket_id: str, kind: str = "resolved") -> Summary | None:
    d = tickets.detail(ticket_id)
    if not d:
        return None
    tools = _by_tool(d["tool_calls"])
    traces = _traces(d)
    depts = {t.get("department") for t in traces}

    def first_turn(dept: str) -> int:
        return next((t["turn"] for t in traces if t.get("department") == dept), 999)

    topics: list[Topic] = []
    for builder, dept in ((_payment_topic, "Billing"), (_order_topic, "Order"), (_account_topic, "Account")):
        if dept in depts or (builder is _payment_topic and d["pending_actions"]):
            t = builder(d, tools)
            if t:
                t.turn = first_turn(dept)
                topics.append(t)
    bug = _bug_topic(d)
    topics += _info_topics(traces)
    if bug:
        bug.turn = next((t["turn"] for t in traces if (t.get("decision") or {}).get("path") in ("FIRST_TIME_BUG", "KNOWN_OPEN_BUG")), 999)
        topics.append(bug)
    topics.sort(key=lambda t: t.turn)

    key, label = _STATUS.get(d["status"], ("progress", d["status"].replace("_", " ").title()))
    approvals = [h for h in d["human_actions"] if h["event_type"] == "APPROVAL"]
    took_over = d["handled_by"] == "HUMAN"
    handled = "A Nova Retail team member" if took_over else ("Riya, with a team lead's approval" if approvals else "Riya")
    if d["escalated"] and not took_over:
        handled = "Riya, then " + (d["assignee"] or "our team")

    steps: list[str] = []
    pend = next((p for p in d["pending_actions"] if p["action_type"] == "refund" and p["status"] == "PENDING"), None)
    if pend:
        steps.append("Your refund is with our team lead. You will get another email as soon as it is done.")
    if d["escalated"]:
        who = d["assignee"] or "a specialist on our team"
        steps.append(f"{who} has the full conversation and will follow up with you, so you do not need to repeat anything.")
    if d["bugs"] and d["bugs"][0]["status"] == "OPEN" and not d["escalated"]:
        steps.append("Our team lead will send you the fix for the new issue as soon as it is ready.")
    verified = next((v for v in reversed(tools.get("verify_refund", [])) if v.get("verified")), None)
    if verified and key == "resolved":
        steps.append("Watch for the refund on your statement within 3 to 5 working days. Nothing else is needed from you.")
    if not steps:
        steps.append("Nothing further is needed from you." if key == "resolved" else "Reply to this email if you would like to add anything.")

    refs: list[tuple[str, str]] = [("Ticket", ticket_id)]
    if d.get("order_id"):
        refs.append(("Order", d["order_id"]))
    for r in tools.get("verify_refund", []):
        if r.get("verified"):
            refs.append(("Refund", r["refund_id"]))
    for r in tools.get("issue_refund", []):
        if r.get("refund_id") and ("Refund", r["refund_id"]) not in refs:
            refs.append(("Refund", r["refund_id"]))
    for c in tools.get("check_refund_policy", []):
        if c.get("eligible") and c.get("transaction_id"):
            refs.append(("Duplicate charge", c["transaction_id"]))
            break

    msgs = d["messages"]
    stamps = [x for x in (_parse(m["timestamp"]) for m in msgs) if x]
    start = _parse(d["created_at"]) or (stamps[0] if stamps else None)
    when = f"{start.day} {_MONTHS[start.month - 1]} {start.year}" if start else ""
    duration = ""
    if len(stamps) >= 2:
        mins = max(1, round((stamps[-1] - stamps[0]).total_seconds() / 60))
        duration = f"about {mins} minute{'s' if mins != 1 else ''}"

    return Summary(
        ticket_id=ticket_id, first_name=(d["customer_name"] or "there").split()[0],
        channel_word={"Call": "call", "Text": "chat"}.get(d["channel"], "conversation"),
        when=when, duration=duration, status_key=key, status_label=label, handled_by=handled,
        topics=topics, next_steps=steps, references=refs,
    )
