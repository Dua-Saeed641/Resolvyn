"""Email channel: inbound email (JSON from the demo inbox, or form fields from an inbound-parse webhook), threads, outbox."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.services import email_service

router = APIRouter()


class InboundIn(BaseModel):
    sender: str = Field(alias="from")
    subject: str = ""
    text: str
    ticket_id: str | None = None
    headers: dict | None = None  # Message-ID, In-Reply-To, References, Auto-Submitted... when the sender provides them

    model_config = {"populate_by_name": True}


@router.post("/inbound")
async def inbound(request: Request):
    """Receive one customer email and return Riya's reply. Accepts JSON {from, subject, text, ticket_id?} or form data
    with the same field names (what SendGrid Inbound Parse and similar services post)."""
    if request.headers.get("content-type", "").startswith("application/json"):
        body = InboundIn.model_validate(await request.json())
    else:
        form = await request.form()
        body = InboundIn.model_validate({"from": form.get("from", ""), "subject": form.get("subject", ""),
                                         "text": form.get("text", "") or form.get("body-plain", "")})
    try:
        return await email_service.receive(body.sender, body.subject, body.text, body.ticket_id, headers=body.headers)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/thread/{ticket_id}")
def thread(ticket_id: str):
    return email_service.thread(ticket_id)


@router.get("/outbox")
def outbox(limit: int = 50):
    return [m.public() for m in email_service.OUTBOX[-limit:]][::-1]


@router.get("/status")
def status():
    return email_service.status()


class TestIn(BaseModel):
    to: str


@router.post("/test")
def send_test(body: TestIn):
    """Send a test email through the configured mail server (or the simulated inbox) to check the setup."""
    from app.services.email_service import Mail, _send
    from app.config import get_settings

    s = get_settings()
    mail = Mail(to=body.to.strip(), subject=f"{s.business_name} support: test email", ticket_id="TEST",
                body=f"This is a test from {s.agent_name}. If you can read it, outgoing email works.", kind="test")
    _send(mail)
    return {"to": mail.to, "delivered": mail.delivered, "intended_for": mail.intended_for}


@router.get("/eml/{index}")
def eml(index: int):
    """The message exactly as it goes on the wire (newest first, like /outbox): open it in any mail client."""
    from fastapi import HTTPException
    from fastapi.responses import Response

    box = email_service.OUTBOX[::-1]
    if not 0 <= index < len(box) or not box[index].raw:
        raise HTTPException(404, "No such email")
    return Response(box[index].raw, media_type="message/rfc822", headers={"Content-Disposition": f'attachment; filename="{box[index].ticket_id}.eml"'})
