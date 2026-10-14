"""Report and PDF Download endpoints."""

from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.models.reports import FinalReport, ReportArtifact
from app.services.workflow_manager import workflow_manager

router = APIRouter(prefix="/api/runs", tags=["Reports & Artifacts"])


@router.get("/{run_id}/report", response_model=FinalReport)
def get_research_report(run_id: str) -> FinalReport:
    """Retrieves structured final research report JSON."""
    report = workflow_manager.store.get_report(run_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Report for run '{run_id}' not yet generated.")
    return report


@router.get("/{run_id}/report/pdf")
def download_report_pdf(run_id: str) -> FileResponse:
    """Downloads the generated PDF report with clickable primary-source citations."""
    artifact = workflow_manager.store.get_artifact(run_id)
    if not artifact or not Path(artifact.file_path).exists():
        raise HTTPException(status_code=404, detail=f"PDF report for run '{run_id}' not found.")

    path = Path(artifact.file_path)
    return FileResponse(
        path=str(path),
        media_type="application/pdf",
        filename=path.name,
    )
