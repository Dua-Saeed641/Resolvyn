"""Aggregate metrics (project.md §66)."""

from fastapi import APIRouter

from app.services import analytics_service

router = APIRouter()


@router.get("")
def stats():
    return analytics_service.stats()
