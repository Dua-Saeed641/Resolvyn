"""Specialist agent roster and state — docs/architecture.md §2.3, §5.

Backed by seed data for now; move to agents/orchestrator.py once agent
state is driven by real ticket assignment instead of static mock rows.
"""

from fastapi import APIRouter

from data.seed_data import AGENTS

router = APIRouter()


@router.get("")
def list_agents():
    return AGENTS
