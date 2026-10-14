"""End-to-End Workflow Integration Tests."""

from pathlib import Path
from typing import Any
import pytest
from app.models.research import QuestionStatus, RunStatus
from app.plugins.registry import PluginRegistry
from app.services.workflow_manager import WorkflowManager


def test_end_to_end_workflow_with_fake_source(fake_source: Any) -> None:
    """Demonstrates complete end-to-end slice using fake source fixtures."""
    registry = PluginRegistry()
    registry.register(fake_source)

    manager = WorkflowManager(plugin_registry=registry)

    # 1. Create run & plan research
    run, itinerary = manager.create_run(
        ticker_or_name="MSFT",
        objective="Analyze latest annual financial results, revenue, liquidity, and risks.",
        source_plugin_id="fake_source",
    )

    assert run.status == RunStatus.AWAITING_APPROVAL
    assert run.cik == "0000789019"
    assert itinerary is not None
    assert len(itinerary.sections) == 5
    assert len(itinerary.questions) == 7

    # 2. Human approval of plan -> resumes workflow through completion
    completed_run = manager.approve_and_execute(
        run_id=run.run_id,
        decision="APPROVED",
        async_execution=False,
    )

    # Status must be COMPLETE or INCOMPLETE depending on question coverage
    assert completed_run.status in [RunStatus.COMPLETE, RunStatus.INCOMPLETE]

    # 3. Verify final report
    report = manager.store.get_report(run.run_id)
    assert report is not None
    assert len(report.sections) == 5
    assert len(report.bibliography) >= 1
    assert "Executive Summary" in report.executive_summary

    # 4. Verify PDF artifact
    artifact = manager.store.get_artifact(run.run_id)
    assert artifact is not None
    assert artifact.format == "PDF"
    assert Path(artifact.file_path).exists()
    assert artifact.file_size_bytes > 1000

    with open(artifact.file_path, "rb") as f:
        pdf_bytes = f.read()
    assert pdf_bytes.startswith(b"%PDF-")


def test_live_sec_integration_if_available() -> None:
    """Integration test against live SEC EDGAR API."""
    import httpx
    try:
        # Quick ping to see if live SEC is responding
        headers = {"User-Agent": "ApolloResearch/1.0 (research@example.com)"}
        with httpx.Client(timeout=5.0) as client:
            resp = client.get("https://data.sec.gov/submissions/CIK0000789019.json", headers=headers)
        if resp.status_code != 200:
            pytest.skip("SEC EDGAR API not returning 200")
    except Exception as e:
        pytest.skip(f"SEC EDGAR network unavailable: {e}")

    manager = WorkflowManager()
    run, itinerary = manager.create_run(
        ticker_or_name="MSFT",
        objective="Verify live SEC issuer resolution and planning",
        source_plugin_id="sec_edgar",
    )

    assert run.status == RunStatus.AWAITING_APPROVAL
    assert run.cik == "0000789019"
    assert "MICROSOFT" in run.company_name.upper()
    assert len(itinerary.sections) > 0
