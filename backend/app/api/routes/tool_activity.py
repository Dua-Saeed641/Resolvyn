"""Tool/API activity across all tickets — spec §18 (AI Operations > Tool Activity)."""

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.tool_call import ToolCall

router = APIRouter()


@router.get("")
def list_tool_activity(status: str | None = None, session: Session = Depends(get_session)):
    statement = select(ToolCall).order_by(ToolCall.timestamp.desc())
    if status:
        statement = statement.where(ToolCall.status == status)
    return session.exec(statement).all()
