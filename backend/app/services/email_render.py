"""Email layout: one HTML template (table based, inline styles, dark-mode aware) and a matching plain-text version.

Built to the usual email rules: 600 px wide, system font stack (web fonts are not reliable in mail clients), a hidden
preheader for the inbox preview, real text (no images carry meaning), an inline logo with alt text, contrast of at least 4.5:1,
and a plain-text alternative wrapped at 72 columns.
"""

import html as _html
import re
import textwrap

from app.config import get_settings
from app.services.email_summary import Summary

LOGO_CID = "resolvyn-logo@resolvyn"
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

# the palette of the app (frontend/app/globals.css), as email-safe hex
C = {
    "bg": "#FAFAFA", "card": "#FFFFFF", "text": "#0A0A0A", "muted": "#525252", "border": "#E5E5E5", "soft": "#F5F5F5",
    "brand": "#38BB2D", "brand_text": "#1F6B1A", "brand_tint": "#EAF7E8", "warn_text": "#8A5300", "warn_tint": "#FFF3DC",
    "info_text": "#1D4E9E", "info_tint": "#E8F0FD",
}
_PILL = {
    "resolved": (C["brand_tint"], C["brand_text"], "#B9E3B4"),
    "team": (C["warn_tint"], C["warn_text"], "#F1D9A6"),
    "progress": (C["info_tint"], C["info_text"], "#C4D7F6"),
}

_DARK_CSS = """
@media (prefers-color-scheme: dark) {
  .dm-bg { background-color: #0A0D0A !important; }
  .dm-card { background-color: #111511 !important; border-color: #232923 !important; }
  .dm-soft { background-color: #171C17 !important; border-color: #232923 !important; }
  .dm-text { color: #F2F4F2 !important; }
  .dm-muted { color: #A3ABA3 !important; }
  .dm-line { border-color: #232923 !important; }
  .dm-pill { background-color: #16301A !important; color: #7FD97A !important; border-color: #245A2A !important; }
}
@media only screen and (max-width: 620px) {
  .container { width: 100% !important; }
  .pad { padding-left: 20px !important; padding-right: 20px !important; }
}
"""


def e(s) -> str:
    return _html.escape(str(s), quote=True)


def _shell(*, title: str, preheader: str, body_rows: str, footer_note: str) -> str:
    s = get_settings()
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="supported-color-schemes" content="light dark">
<title>{e(title)}</title>
<style>{_DARK_CSS}</style>
</head>
<body class="dm-bg" style="margin:0;padding:0;background-color:{C['bg']};-webkit-text-size-adjust:100%;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;font-size:1px;line-height:1px;color:{C['bg']};">{e(preheader)}&#8199;&#847;&#8199;&#847;&#8199;&#847;</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="dm-bg" style="background-color:{C['bg']};">
<tr><td align="center" style="padding:28px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" class="container dm-card" style="width:600px;max-width:100%;background-color:{C['card']};border:1px solid {C['border']};border-radius:14px;">
  <tr><td style="height:4px;line-height:4px;font-size:0;background-color:{C['brand']};border-radius:14px 14px 0 0;">&nbsp;</td></tr>
  <tr><td class="pad" style="padding:22px 32px 18px 32px;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="vertical-align:middle;padding-right:10px;"><img src="cid:{LOGO_CID}" width="32" height="32" alt="Resolvyn" style="display:block;border:0;outline:none;"></td>
      <td style="vertical-align:middle;font-family:{FONT};">
        <div class="dm-text" style="font-size:16px;line-height:20px;color:{C['text']};letter-spacing:-0.01em;">{e(s.business_name)} Support</div>
        <div class="dm-muted" style="font-size:11px;line-height:14px;color:{C['muted']};">Powered by Resolvyn</div>
      </td>
    </tr></table>
  </td></tr>
  <tr><td class="pad dm-line" style="padding:0 32px;border-top:1px solid {C['border']};font-size:0;line-height:0;">&nbsp;</td></tr>
{body_rows}
  <tr><td class="pad dm-line" style="padding:20px 32px 26px 32px;border-top:1px solid {C['border']};font-family:{FONT};">
    <div class="dm-muted" style="font-size:12px;line-height:18px;color:{C['muted']};">{footer_note}</div>
  </td></tr>
</table>
<div class="dm-muted" style="max-width:600px;font-family:{FONT};font-size:11px;line-height:16px;color:{C['muted']};padding:14px 8px 0 8px;text-align:center;">
  {e(s.business_name)} is a demo business. This message was written by an AI assistant from verified records.
</div>
</td></tr></table>
</body></html>"""


def _pill(key: str, label: str) -> str:
    bg, fg, br = _PILL.get(key, _PILL["progress"])
    return (f'<span class="dm-pill" style="display:inline-block;padding:3px 10px;border-radius:999px;background-color:{bg};color:{fg};'
            f'border:1px solid {br};font-size:12px;line-height:16px;font-weight:600;">{e(label)}</span>')


def _h(text: str) -> str:
    return (f'<div class="dm-muted" style="font-size:11px;line-height:16px;letter-spacing:0.08em;text-transform:uppercase;color:{C["muted"]};'
            f'padding:0 0 8px 0;">{e(text)}</div>')


# ── the summary email ────────────────────────────────────────────────────────


def summary_subject(sm: Summary) -> str:
    return f"Your support summary [{sm.ticket_id}]"


def summary_preheader(sm: Summary) -> str:
    lead = sm.topics[0].points[0] if sm.topics and sm.topics[0].points else ""
    return f"{sm.status_label}. " + (lead if lead else f"Summary of your {sm.channel_word} with {get_settings().business_name}.")


def summary_html(sm: Summary) -> str:
    s = get_settings()
    when = f" on {sm.when}" if sm.when else ""
    topics = ""
    for t in sm.topics:
        pts = "".join(
            f'<tr><td valign="top" width="24" style="width:24px;padding:0 10px 8px 0;color:{C["brand"]};font-size:14px;line-height:22px;">&#9679;</td>'
            f'<td class="dm-text" style="padding:0 0 8px 0;font-family:{FONT};font-size:14px;line-height:22px;color:{C["text"]};">{e(p)}</td></tr>'
            for p in t.points)
        topics += (f'<tr><td class="pad" style="padding:0 32px 18px 32px;font-family:{FONT};">'
                   f'<div class="dm-text" style="font-size:17px;line-height:24px;color:{C["text"]};padding-bottom:8px;">{e(t.title)}</div>'
                   f'<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{pts}</table></td></tr>')
    if not sm.topics:
        topics = (f'<tr><td class="pad dm-muted" style="padding:0 32px 18px 32px;font-family:{FONT};font-size:14px;line-height:22px;color:{C["muted"]};">'
                  f'You reached out to us{e(when)}, and we have noted your request.</td></tr>')

    steps = "".join(
        f'<tr><td valign="top" width="24" style="width:24px;padding:0 10px 6px 0;color:{C["brand_text"]};font-size:14px;line-height:22px;">&rarr;</td>'
        f'<td class="dm-text" style="padding:0 0 6px 0;font-family:{FONT};font-size:14px;line-height:22px;color:{C["text"]};">{e(x)}</td></tr>'
        for x in sm.next_steps)
    refs = "".join(
        f'<tr><td class="dm-muted" style="padding:4px 12px 4px 0;font-family:{FONT};font-size:13px;line-height:18px;color:{C["muted"]};">{e(k)}</td>'
        f'<td class="dm-text" style="padding:4px 0;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:13px;line-height:18px;color:{C["text"]};">{e(v)}</td></tr>'
        for k, v in sm.references)
    meta = " &middot; ".join(x for x in (e(sm.channel_word.capitalize()), e(sm.when), e(sm.duration)) if x)

    body = f"""  <tr><td class="pad" style="padding:26px 32px 6px 32px;font-family:{FONT};">
    <div class="dm-text" style="font-size:26px;line-height:32px;color:{C['text']};letter-spacing:-0.02em;">Hi {e(sm.first_name)}, here is what we sorted out.</div>
    <div class="dm-muted" style="font-size:14px;line-height:22px;color:{C['muted']};padding-top:8px;">A short summary of your {e(sm.channel_word)} with us{e(when)}, for your records.</div>
  </td></tr>
  <tr><td class="pad" style="padding:20px 32px 22px 32px;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" class="dm-soft" style="background-color:{C['soft']};border:1px solid {C['border']};border-radius:10px;">
      <tr>
        <td style="padding:14px 16px;font-family:{FONT};" width="34%"><div class="dm-muted" style="font-size:11px;color:{C['muted']};letter-spacing:0.06em;text-transform:uppercase;padding-bottom:6px;">Status</div>{_pill(sm.status_key, sm.status_label)}</td>
        <td style="padding:14px 16px;font-family:{FONT};" width="33%"><div class="dm-muted" style="font-size:11px;color:{C['muted']};letter-spacing:0.06em;text-transform:uppercase;padding-bottom:6px;">Ticket</div><div class="dm-text" style="font-size:14px;line-height:22px;color:{C['text']};">{e(sm.ticket_id)}</div></td>
        <td style="padding:14px 16px;font-family:{FONT};" width="33%"><div class="dm-muted" style="font-size:11px;color:{C['muted']};letter-spacing:0.06em;text-transform:uppercase;padding-bottom:6px;">Handled by</div><div class="dm-text" style="font-size:14px;line-height:22px;color:{C['text']};">{e(sm.handled_by)}</div></td>
      </tr>
    </table>
  </td></tr>
  <tr><td class="pad" style="padding:0 32px 6px 32px;font-family:{FONT};">{_h('What we covered')}</td></tr>
{topics}
  <tr><td class="pad" style="padding:6px 32px 8px 32px;font-family:{FONT};">{_h('What happens next')}
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%">{steps}</table>
  </td></tr>
  <tr><td class="pad" style="padding:14px 32px 26px 32px;font-family:{FONT};">{_h('References')}
    <table role="presentation" cellpadding="0" cellspacing="0" border="0">{refs}</table>
    <div class="dm-muted" style="font-size:12px;line-height:18px;color:{C['muted']};padding-top:10px;">{meta}</div>
  </td></tr>"""
    note = (f"Something not right, or want to add anything? Just reply to this email and it will reopen ticket {e(sm.ticket_id)}, "
            f"with everything above already in front of us. &mdash; {e(s.agent_name)}")
    return _shell(title=summary_subject(sm), preheader=summary_preheader(sm), body_rows=body, footer_note=note)


def _wrap(text: str, indent: str = "", sub: str = "") -> str:
    return textwrap.fill(text, width=72, initial_indent=indent, subsequent_indent=sub or indent, break_long_words=False)


def summary_text(sm: Summary) -> str:
    s = get_settings()
    when = f" on {sm.when}" if sm.when else ""
    out = [f"Hi {sm.first_name}, here is what we sorted out.", "",
           _wrap(f"A short summary of your {sm.channel_word} with us{when}, for your records."), "",
           f"STATUS      {sm.status_label}", f"TICKET      {sm.ticket_id}", f"HANDLED BY  {sm.handled_by}", "", "WHAT WE COVERED", "---------------"]
    if not sm.topics:
        out += [_wrap(f"You reached out to us{when}, and we have noted your request.")]
    for t in sm.topics:
        out += ["", t.title]
        out += [_wrap(p, "  - ", "    ") for p in t.points]
    out += ["", "WHAT HAPPENS NEXT", "-----------------"] + [_wrap(x, "  > ", "    ") for x in sm.next_steps]
    out += ["", "REFERENCES", "----------"] + [f"  {k:<18}{v}" for k, v in sm.references]
    meta = " | ".join(x for x in (sm.channel_word.capitalize(), sm.when, sm.duration) if x)
    out += ["", meta, "", _wrap(f"Something not right, or want to add anything? Just reply to this email and it will reopen ticket {sm.ticket_id}."),
            "", s.agent_name, f"{s.business_name} Support (powered by Resolvyn)"]
    return "\n".join(out) + "\n"


# ── a reply inside an email thread ───────────────────────────────────────────


def reply_html(*, first_name: str, paragraphs: list[str], ticket_id: str, subject: str) -> str:
    s = get_settings()
    body_html = "".join(
        f'<div class="dm-text" style="font-size:15px;line-height:24px;color:{C["text"]};padding-bottom:12px;">{e(p)}</div>' for p in paragraphs)
    body = f"""  <tr><td class="pad" style="padding:26px 32px 22px 32px;font-family:{FONT};">
    <div class="dm-text" style="font-size:22px;line-height:28px;color:{C['text']};letter-spacing:-0.02em;padding-bottom:12px;">Hi {e(first_name)},</div>
    {body_html}
    <div class="dm-text" style="font-size:15px;line-height:24px;color:{C['text']};padding-top:6px;">Warm regards,<br>{e(s.agent_name)}<br><span class="dm-muted" style="color:{C['muted']};">{e(s.business_name)} Support</span></div>
  </td></tr>
  <tr><td class="pad" style="padding:0 32px 22px 32px;font-family:{FONT};">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" class="dm-soft" style="background-color:{C['soft']};border:1px solid {C['border']};border-radius:8px;"><tr>
      <td class="dm-muted" style="padding:8px 12px;font-family:{FONT};font-size:12px;line-height:16px;color:{C['muted']};">Ticket <span class="dm-text" style="color:{C['text']};">{e(ticket_id)}</span></td></tr></table>
  </td></tr>"""
    note = f"Reply to this email to continue this conversation. Ticket {e(ticket_id)}."
    return _shell(title=subject, preheader=paragraphs[0][:110] if paragraphs else subject, body_rows=body, footer_note=note)


def reply_text(*, first_name: str, paragraphs: list[str], ticket_id: str) -> str:
    s = get_settings()
    out = [f"Hi {first_name},", ""]
    for p in paragraphs:
        out += [_wrap(p), ""]
    out += ["Warm regards,", s.agent_name, f"{s.business_name} Support", "", f"Ticket {ticket_id}"]
    return "\n".join(out) + "\n"


def strip_greeting(text: str) -> list[str]:
    """The model's reply body without its own greeting and sign-off (the template adds both), split into paragraphs."""
    t = text.strip()
    t = re.sub(r"^(?:hi|hello|hey|dear)\b[^,.!\n]{0,40}[,!.]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*(?:warm regards|best regards|kind regards|regards|thanks|cheers),?\s*(?:riya)?[^.!?]*$", "", t, flags=re.I).strip() or text.strip()
    sentences = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", t))
    paras, cur = [], []
    for sent in sentences:
        cur.append(sent)
        if len(" ".join(cur)) > 240:
            paras.append(" ".join(cur))
            cur = []
    if cur:
        paras.append(" ".join(cur))
    return paras or [t]
