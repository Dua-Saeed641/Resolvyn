"""Guide / Approve / Correct / Override / Teach — docs/context.md,
Human Intelligence Layer.

Not yet implemented: each action must write a human_action row and be
capable of producing a learning signal (docs/architecture.md §2.5-2.6).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_human_actions():
    return []
