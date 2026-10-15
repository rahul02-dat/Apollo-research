"""Tests for Phase 3: Durable SQLite Persistence, Multi-Tenant Workspace Scoping, and Authentication."""

import time
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from app.api.auth import (
    User,
    UserRole,
    create_access_token,
    verify_access_token,
)
from app.api.main import app
from app.models.approvals import ApprovalCheckpoint, ApprovalDecision, ApprovalEvent
from app.models.reports import FinalReport, ReportArtifact
from app.models.research import ResearchItinerary, ResearchRun, RunStatus
from app.persistence.database import RunStore


def test_durable_sqlite_persistence_across_instances(tmp_path: Path) -> None:
    """Verifies that runs, itineraries, reports, artifacts, and approvals persist across store lifecycles."""
    db_file = tmp_path / "apollo_test.db"
    db_url = f"sqlite:///{db_file}"

    # Instance 1: write records
    store1 = RunStore(database_url=db_url)

    run = ResearchRun(
        run_id="RUN_PERSIST_01",
        requested_by="Test Analyst",
        user_id="usr_01",
        workspace_id="ws_test",
        company_name="Microsoft Corp",
        ticker="MSFT",
        cik="0000789019",
        objective="Verify persistence across server reboots.",
        status=RunStatus.COMPLETE,
    )
    store1.save_run(run)

    itinerary = ResearchItinerary(
        run_id="RUN_PERSIST_01",
        itinerary_id="ITIN_PERSIST_01",
        company_name="Microsoft Corp",
        ticker="MSFT",
        cik="0000789019",
        sections=[],
        questions=[],
    )
    store1.save_itinerary(itinerary)

    report = FinalReport(
        run_id="RUN_PERSIST_01",
        report_id="RPT_PERSIST_01",
        company_name="Microsoft Corp",
        ticker="MSFT",
        cik="0000789019",
        objective="Verify persistence across server reboots.",
        status=RunStatus.COMPLETE,
        executive_summary="Test report executive summary.",
        sections=[],
        unresolved_limitations=[],
    )
    store1.save_report(report)

    artifact = ReportArtifact(
        run_id="RUN_PERSIST_01",
        artifact_id="ART_PERSIST_01",
        format="PDF",
        file_path=str(tmp_path / "report.pdf"),
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=1024,
        is_complete=True,
    )
    store1.save_artifact(artifact)

    appr = ApprovalEvent(
        event_id="EVT_APPR_01",
        run_id="RUN_PERSIST_01",
        checkpoint=ApprovalCheckpoint.PLAN_APPROVAL,
        decision=ApprovalDecision.APPROVED,
        feedback="Approved for persistence testing",
    )
    store1.save_approval(appr)

    # Instance 2: completely fresh store reading the existing SQLite database
    store2 = RunStore(database_url=db_url)

    loaded_run = store2.get_run("RUN_PERSIST_01")
    assert loaded_run is not None
    assert loaded_run.run_id == "RUN_PERSIST_01"
    assert loaded_run.ticker == "MSFT"
    assert loaded_run.workspace_id == "ws_test"
    assert loaded_run.status == RunStatus.COMPLETE

    loaded_itin = store2.get_itinerary("RUN_PERSIST_01")
    assert loaded_itin is not None
    assert loaded_itin.itinerary_id == "ITIN_PERSIST_01"

    loaded_rpt = store2.get_report("RUN_PERSIST_01")
    assert loaded_rpt is not None
    assert loaded_rpt.executive_summary == "Test report executive summary."

    loaded_art = store2.get_artifact("RUN_PERSIST_01")
    assert loaded_art is not None
    assert loaded_art.artifact_id == "ART_PERSIST_01"

    approvals = store2.list_approvals("RUN_PERSIST_01")
    assert len(approvals) == 1
    assert approvals[0].decision == ApprovalDecision.APPROVED


def test_multi_tenant_workspace_scoping(tmp_path: Path) -> None:
    """Verifies that runs are isolated by workspace_id."""
    db_file = tmp_path / "apollo_workspaces.db"
    store = RunStore(database_url=f"sqlite:///{db_file}")

    run_a = ResearchRun(
        run_id="RUN_ALPHA",
        user_id="usr_alpha",
        workspace_id="ws_alpha",
        company_name="Alpha Corp",
        objective="Alpha research",
    )
    run_b = ResearchRun(
        run_id="RUN_BETA",
        user_id="usr_beta",
        workspace_id="ws_beta",
        company_name="Beta Corp",
        objective="Beta research",
    )

    store.save_run(run_a)
    store.save_run(run_b)

    # Scoped queries
    alpha_runs = store.list_runs(workspace_id="ws_alpha")
    assert len(alpha_runs) == 1
    assert alpha_runs[0].run_id == "RUN_ALPHA"

    beta_runs = store.list_runs(workspace_id="ws_beta")
    assert len(beta_runs) == 1
    assert beta_runs[0].run_id == "RUN_BETA"

    # All runs (admin)
    all_runs = store.list_runs()
    run_ids = [r.run_id for r in all_runs]
    assert "RUN_ALPHA" in run_ids
    assert "RUN_BETA" in run_ids


def test_cryptographic_token_generation_and_tamper_detection() -> None:
    """Verifies HMAC-SHA256 signature generation, validation, and tamper rejection."""
    user = User(
        user_id="usr_crypt_01",
        email="analyst@firm.com",
        name="Crypto Analyst",
        role=UserRole.ANALYST,
        active_workspace_id="ws_crypto",
    )

    token = create_access_token(user, expires_minutes=15)
    assert "." in token

    # Valid token
    payload = verify_access_token(token)
    assert payload is not None
    assert payload["sub"] == "usr_crypt_01"
    assert payload["role"] == "ANALYST"
    assert payload["workspace_id"] == "ws_crypto"

    # Tampered signature
    parts = token.split(".")
    tampered_sig = parts[0] + "." + parts[1][:-2] + "xx"
    assert verify_access_token(tampered_sig) is None

    # Tampered payload
    tampered_payload = "eyJuYW1lIjoiSGFja2VyIn0." + parts[1]
    assert verify_access_token(tampered_payload) is None

    # Expired token
    expired_token = create_access_token(user, expires_minutes=-5)
    assert verify_access_token(expired_token) is None


def test_auth_api_routes_and_workspace_lifecycle() -> None:
    """Verifies API endpoints for token exchange, user identity, and workspace creation."""
    client = TestClient(app)

    # 1. Login with dev default credentials
    res = client.post("/api/auth/token", json={})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["user_id"] == "usr_primary_analyst"
    token = data["access_token"]

    # 2. Authenticated user profile
    res_me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res_me.status_code == 200
    me_data = res_me.json()
    assert me_data["user"]["user_id"] == "usr_primary_analyst"
    assert len(me_data["workspaces"]) >= 1

    # 3. Create workspace
    res_ws = client.post(
        "/api/auth/workspaces",
        json={"name": "Hedge Fund Research Alpha"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_ws.status_code == 200
    new_ws = res_ws.json()
    assert new_ws["name"] == "Hedge Fund Research Alpha"
    assert new_ws["workspace_id"].startswith("ws_")


def test_workspace_isolation_in_api() -> None:
    """Verifies that analysts cannot see or access runs belonging to another workspace."""
    client = TestClient(app)

    # Token for Analyst in Workspace A
    user_a = User(
        user_id="usr_a",
        email="a@apollo.local",
        name="Analyst A",
        role=UserRole.ANALYST,
        active_workspace_id="ws_tenant_a",
    )
    token_a = create_access_token(user_a)

    # Token for Analyst in Workspace B
    user_b = User(
        user_id="usr_b",
        email="b@apollo.local",
        name="Analyst B",
        role=UserRole.ANALYST,
        active_workspace_id="ws_tenant_b",
    )
    token_b = create_access_token(user_b)

    # Analyst A creates a run in ws_tenant_a
    res = client.post(
        "/api/runs",
        json={"ticker_or_name": "MSFT", "objective": "Analyze MSFT"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 200
    run_a_id = res.json()["run"]["run_id"]
    assert res.json()["run"]["workspace_id"] == "ws_tenant_a"

    # Analyst A can view their run
    res_get_a = client.get(f"/api/runs/{run_a_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert res_get_a.status_code == 200

    # Analyst B in workspace B attempts to fetch Analyst A's run -> 403 Forbidden
    res_get_b = client.get(f"/api/runs/{run_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res_get_b.status_code == 403

    # Analyst B lists runs -> run_a_id must not appear
    res_list_b = client.get("/api/runs", headers={"Authorization": f"Bearer {token_b}"})
    assert res_list_b.status_code == 200
    b_run_ids = [r["run_id"] for r in res_list_b.json()]
    assert run_a_id not in b_run_ids

    # Admin user can access run across workspaces
    admin_user = User(
        user_id="usr_admin",
        email="admin@apollo.local",
        name="Admin User",
        role=UserRole.ADMIN,
        active_workspace_id="ws_admin",
    )
    token_admin = create_access_token(admin_user)
    res_get_admin = client.get(f"/api/runs/{run_a_id}", headers={"Authorization": f"Bearer {token_admin}"})
    assert res_get_admin.status_code == 200
