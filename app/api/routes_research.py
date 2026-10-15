"""Research Run endpoints."""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from app.api.auth import User, UserRole, get_current_user, verify_user_workspace_access
from app.models.research import ResearchItinerary, ResearchRun
from app.services.event_stream import event_broadcaster
from app.services.workflow_manager import workflow_manager

router = APIRouter(prefix="/api/runs", tags=["Research Runs"])


class CreateRunRequest(BaseModel):
    ticker_or_name: str = Field(..., description="Company ticker symbol (e.g. MSFT) or official name")
    objective: str = Field(
        default="Analyze latest annual financial results, liquidity, debt exposure, segment performance, and principal risks.",
        description="Core research objective for Apollo.",
    )
    workspace_id: str | None = Field(default=None, description="Optional target workspace ID. Defaults to user's active workspace.")


class CreateRunResponse(BaseModel):
    run: ResearchRun
    itinerary: ResearchItinerary | None = None


@router.post("", response_model=CreateRunResponse)
def create_research_run(
    request: CreateRunRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """Initiates a new research run, resolves the issuer, and generates the itinerary."""
    target_ws = request.workspace_id or current_user.active_workspace_id
    if not verify_user_workspace_access(current_user, target_ws):
        raise HTTPException(status_code=403, detail=f"Access denied to target workspace '{target_ws}'.")

    try:
        run, itinerary = workflow_manager.create_run(
            ticker_or_name=request.ticker_or_name,
            objective=request.objective,
            user_id=current_user.user_id,
            workspace_id=target_ws,
            requested_by=current_user.name,
        )
        return {"run": run, "itinerary": itinerary}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[ResearchRun])
def list_research_runs(
    current_user: Annotated[User, Depends(get_current_user)],
    workspace_id: str | None = None,
) -> list[ResearchRun]:
    """Lists research runs scoped by tenant workspace and permissions."""
    if workspace_id:
        if not verify_user_workspace_access(current_user, workspace_id):
            raise HTTPException(status_code=403, detail=f"Access denied to workspace '{workspace_id}'.")
        return workflow_manager.store.list_runs(workspace_id=workspace_id)

    if current_user.role == UserRole.ADMIN:
        return workflow_manager.store.list_runs()
    return workflow_manager.store.list_runs(workspace_id=current_user.active_workspace_id)


@router.get("/{run_id}", response_model=ResearchRun)
def get_research_run(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResearchRun:
    """Retrieves status and metadata for a specific research run."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    if not verify_user_workspace_access(current_user, run.workspace_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace's research run.")
    return run


@router.get("/{run_id}/itinerary", response_model=ResearchItinerary)
def get_run_itinerary(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ResearchItinerary:
    """Retrieves the research itinerary and question coverage status for a run."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    if not verify_user_workspace_access(current_user, run.workspace_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace's itinerary.")
    itinerary = workflow_manager.store.get_itinerary(run_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail=f"Itinerary for run '{run_id}' not found.")
    return itinerary


@router.get("/{run_id}/events")
async def stream_run_events(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    """Server-Sent Events (SSE) stream for real-time run progress updates."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    if not verify_user_workspace_access(current_user, run.workspace_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace's events.")

    return StreamingResponse(
        event_broadcaster.subscribe_async(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )



