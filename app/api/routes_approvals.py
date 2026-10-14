"""Approval Checkpoint endpoints."""

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.models.approvals import ApprovalDecision, ApprovalEvent
from app.models.research import ResearchRun
from app.services.workflow_manager import workflow_manager

router = APIRouter(prefix="/api/runs", tags=["Approvals"])


class ApprovalSubmissionRequest(BaseModel):
    decision: ApprovalDecision = Field(default=ApprovalDecision.APPROVED)
    feedback: str | None = None
    async_execution: bool = Field(default=False, description="If true, executes research in background.")


@router.post("/{run_id}/approvals", response_model=ResearchRun)
def submit_approval_decision(run_id: str, request: ApprovalSubmissionRequest) -> ResearchRun:
    """Submits human approval or rejection for the research plan, resuming workflow execution."""
    try:
        updated_run = workflow_manager.approve_and_execute(
            run_id=run_id,
            decision=request.decision,
            feedback=request.feedback,
            async_execution=request.async_execution,
        )
        return updated_run
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{run_id}/approvals", response_model=list[ApprovalEvent])
def list_approval_events(run_id: str) -> list[ApprovalEvent]:
    """Lists audit history of approval events for a run."""
    return workflow_manager.store.list_approvals(run_id)
