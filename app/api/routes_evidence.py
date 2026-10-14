"""Evidence and Source Inspection endpoints."""

from typing import Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
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
def get_run_evidence(run_id: str) -> Any:
    """Retrieves all registered primary-source documents and evidence records for a run."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    ctx = workflow_manager.get_or_create_context(run_id)
    sources = ctx.evidence_registry.list_sources()
    evidence = ctx.evidence_registry.list_evidence()

    return {
        "run_id": run_id,
        "total_sources": len(sources),
        "total_evidence": len(evidence),
        "sources": sources,
        "evidence": evidence,
    }
