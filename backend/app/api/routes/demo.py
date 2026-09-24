"""Demo Mode: RUN DEMO / RESET DEMO (project.md §46)."""

from fastapi import APIRouter, HTTPException

from app.services import demo_service

router = APIRouter()


@router.get("/scenarios")
def scenarios():
    return demo_service.scenarios()


@router.post("/run/{scenario_id}")
async def run(scenario_id: str, auto_human: bool = True):
    try:
        return demo_service.run(scenario_id, auto_human)
    except KeyError as e:
        raise HTTPException(404, "unknown scenario") from e


@router.post("/reset")
async def reset():
    demo_service.reset()
    return {"reset": True}


@router.post("/fail-next/{tool_name}")
def fail_next(tool_name: str):
    """Make one simulated API call fail once, to show the retry path (project.md §88)."""
    from app.tools import mock_apis, tool_service

    if tool_name not in tool_service.REGISTRY:
        raise HTTPException(404, "unknown tool")
    mock_apis.fail_next(tool_name)
    return {"armed": tool_name}
