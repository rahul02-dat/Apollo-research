"""Research Run endpoints."""

from typing import Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
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


class CreateRunResponse(BaseModel):
    run: ResearchRun
    itinerary: ResearchItinerary | None = None


@router.post("", response_model=CreateRunResponse)
def create_research_run(request: CreateRunRequest) -> Any:
    """Initiates a new research run, resolves the issuer, and generates the itinerary."""
    try:
        run, itinerary = workflow_manager.create_run(
            ticker_or_name=request.ticker_or_name,
            objective=request.objective,
        )
        return {"run": run, "itinerary": itinerary}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("", response_model=list[ResearchRun])
def list_research_runs() -> list[ResearchRun]:
    """Lists all research runs."""
    return workflow_manager.store.list_runs()


@router.get("/{run_id}", response_model=ResearchRun)
def get_research_run(run_id: str) -> ResearchRun:
    """Retrieves status and metadata for a specific research run."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return run


@router.get("/{run_id}/itinerary", response_model=ResearchItinerary)
def get_run_itinerary(run_id: str) -> ResearchItinerary:
    """Retrieves the research itinerary and question coverage status for a run."""
    itinerary = workflow_manager.store.get_itinerary(run_id)
    if not itinerary:
        raise HTTPException(status_code=404, detail=f"Itinerary for run '{run_id}' not found.")
    return itinerary


@router.get("/{run_id}/events")
async def stream_run_events(run_id: str) -> StreamingResponse:
    """Server-Sent Events (SSE) stream for real-time run progress updates."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    return StreamingResponse(
        event_broadcaster.subscribe_async(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

