"""Learning signals (project.md §28)."""

from fastapi import APIRouter

from app.learning import learning_service

router = APIRouter()


@router.get("")
def list_signals():
    return learning_service.list_signals()
