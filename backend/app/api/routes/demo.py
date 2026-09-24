"""Demo Mode — project.md §46 (RUN DEMO / RESET DEMO)."""

from fastapi import APIRouter

from app.services import demo_service

router = APIRouter()


@router.post("/run")
def run_demo():
    return demo_service.run_demo()


@router.post("/reset")
def reset_demo():
    demo_service.reset_demo()
    return {"status": "reset"}
