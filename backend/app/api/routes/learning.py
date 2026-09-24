"""Learning Signals — docs/architecture.md §2.6 (Solvable Rulebook loop).

Not yet implemented: populate from app/learning/learning_service.py once
human_intelligence actions are persisted.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_learning_signals():
    return []
