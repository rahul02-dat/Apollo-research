"""Report and PDF Download endpoints."""

from pathlib import Path
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.api.auth import User, UserRole, get_current_user
from app.models.reports import FinalReport, ReportArtifact
from app.services.workflow_manager import workflow_manager

router = APIRouter(prefix="/api/runs", tags=["Reports & Artifacts"])


@router.get("/{run_id}/report", response_model=FinalReport)
def get_research_report(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> FinalReport:
    """Retrieves structured final research report JSON."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    if current_user.role != UserRole.ADMIN and run.workspace_id != current_user.active_workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace's report.")

    report = workflow_manager.store.get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report for run '{run_id}' not yet generated.")
    return report


@router.get("/{run_id}/report/pdf")
def download_report_pdf(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
) -> FileResponse:
    """Downloads the generated PDF report with clickable primary-source citations."""
    run = workflow_manager.store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    if current_user.role != UserRole.ADMIN and run.workspace_id != current_user.active_workspace_id:
        raise HTTPException(status_code=403, detail="Access denied to this workspace's report.")

    artifact = workflow_manager.store.get_artifact(run_id)
    if not artifact or not Path(artifact.file_path).exists():
        raise HTTPException(status_code=404, detail=f"PDF report for run '{run_id}' not found.")

    path = Path(artifact.file_path)
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=path.name,
    )

