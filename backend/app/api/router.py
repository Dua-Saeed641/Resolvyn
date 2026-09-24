"""Aggregates every route module under a single /api prefix.

Route → architecture mapping (docs/architecture.md §3 table): each module is
one sidebar section on the ops side, plus /system + /tts for the voice channel.
"""

from fastapi import APIRouter

from app.api.routes import (
    activity,
    agents,
    analytics,
    customers,
    demo,
    human_intelligence,
    knowledge,
    learning,
    system,
    tickets,
)

api_router = APIRouter(prefix="/api")

api_router.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(customers.router, prefix="/customers", tags=["customers"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(activity.router, prefix="/activity", tags=["activity"])
api_router.include_router(
    human_intelligence.router, prefix="/human-intelligence", tags=["human-intelligence"]
)
api_router.include_router(learning.router, prefix="/learning-signals", tags=["learning"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(system.router, tags=["system"])
