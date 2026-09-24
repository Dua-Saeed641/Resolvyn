"""Global system activity/event stream — project.md §14, §37.

Not yet implemented: needs the agent_event model + a real or simulated
event source (see app/services and docs/architecture.md §8, Event Stream).
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_activity():
    return []
