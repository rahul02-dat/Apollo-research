"""Evidence and Source Inspection endpoints."""

from typing import Annotated, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.api.auth import User, get_current_user, verify_user_workspace_access
from app.models.evidence import EvidenceRecord
from app.models.sources import SourceDocument
from app.services.workflow_manager import workflow_manager

router = APIRouter(prefix="/api/runs", tags=["Evidence & Sources"])


class EvidenceOverviewResponse(BaseModel):
    run_id: str
    total_sources: int
    total_evidence: int
    sources: list[SourceDocument]
    evidence: list[EvidenceRecord]


@router.get("/{run_id}/evidence", response_model=EvidenceOverviewResponse)
def get_run_evidence(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """Retrieves all registered primary-source documents and evidence records for a run."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    if not verify_user_workspace_access(current_user, run.workspace_id):
        raise HTTPException(status_code=403, detail="Access denied to this workspace's evidence.")

    ctx = workflow_manager.get_or_create_context(run_id)
    sources = ctx.evidence_registry.list_sources_for_run(run_id)
    evidence = ctx.evidence_registry.list_for_run(run_id)

    return {
        "run_id": run_id,
        "total_sources": len(sources),
        "total_evidence": len(evidence),
        "sources": sources,
        "evidence": evidence,
    }


