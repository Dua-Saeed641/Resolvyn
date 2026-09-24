"""Routing decisions workspace — spec §22."""

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.database import get_session
from app.services import routing_service

router = APIRouter()


@router.get("")
def list_routing_decisions(session: Session = Depends(get_session)):
    return routing_service.list_routing_decisions(session)
