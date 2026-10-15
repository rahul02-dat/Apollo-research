"""Comprehensive Security and Reliability Hardening Test Suite for Apollo Research.

Validates:
1. Fail-closed production configuration and auth security.
2. Tenant and workspace authorization with multi-user isolation.
3. Fatal PostgreSQL checkpointer failures in production (no silent in-memory fallback).
4. Durable research state and evidence persistence across process instances.
5. Plugin execution deadline enforcement and fail-closed capability grants.
6. Evidence-based question completion criteria and cross-run claim isolation.
7. Financial analytics calculation lineage, annual/quarterly period isolation, and unit safety.
8. Accurate workflow terminal event emission (RUN_INCOMPLETE vs RUN_COMPLETED).
"""

import os
import time
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.api.auth import User, UserRole, create_access_token
from app.api.main import app
from app.config import Settings
from app.models.claims import Claim
from app.models.evidence import EvidenceRecord, EvidenceType, EvidenceValidationStatus
from app.models.research import QuestionStatus, ResearchItinerary, ResearchQuestion, ResearchRun, RunStatus
from app.models.sources import SourceDocument, SourceDocumentRef
from app.models.reports import FinalReport, SectionDraft
from app.persistence.checkpointer import get_checkpointer
from app.persistence.database import RunStore
from app.plugins.builtin.financial_analytics.plugin import FinancialAnalyticsPlugin
from app.plugins.execution import GuardedPluginExecutor, PluginTimeoutError
from app.plugins.manifest import PluginManifest
from app.plugins.policy import PluginPolicyGate, UnauthorizedCapabilityError
from app.services.evidence_registry import EvidenceRegistry
from app.services.gap_detection import GapDetectionService
from app.services.validation_service import ValidationService
from app.services.event_stream import event_broadcaster


# ==============================================================================
# 1. Configuration & Production Authentication Hardening
# ==============================================================================
def test_production_config_fail_closed_validation() -> None:
    """Production mode must reject unsafe defaults: default secret, REQUIRE_AUTH=False, and default SEC agent."""
    # Defect: Insecure default auth secret in production
    with pytest.raises(ValueError, match="Default or insecure AUTH_SECRET_KEY is prohibited in production"):
        Settings(
            APOLLO_ENV="production",
            REQUIRE_AUTH=True,
            AUTH_SECRET_KEY="default-secret-key-change-in-prod-min-32-chars",
            SEC_USER_AGENT="ApolloResearch user@organization.com",
        )

    # Defect: Short secret key (< 32 chars)
    with pytest.raises(ValueError, match="AUTH_SECRET_KEY must be at least 32 characters"):
        Settings(
            APOLLO_ENV="production",
            REQUIRE_AUTH=True,
            AUTH_SECRET_KEY="short-secret",
            SEC_USER_AGENT="ApolloResearch user@organization.com",
        )

    # Defect: REQUIRE_AUTH=False in production
    with pytest.raises(ValueError, match="REQUIRE_AUTH cannot be disabled in production"):
        Settings(
            APOLLO_ENV="production",
            REQUIRE_AUTH=False,
            AUTH_SECRET_KEY="a-sufficiently-long-production-cryptographic-secret-key",
            SEC_USER_AGENT="ApolloResearch user@organization.com",
        )

    # Defect: Placeholder SEC User-Agent in production
    with pytest.raises(ValueError, match="Default SEC_USER_AGENT is prohibited in production"):
        Settings(
            APOLLO_ENV="production",
            REQUIRE_AUTH=True,
            AUTH_SECRET_KEY="a-sufficiently-long-production-cryptographic-secret-key",
            SEC_USER_AGENT="ApolloResearch user@example.com",
        )

    # Valid production settings pass
    prod_valid = Settings(
        APOLLO_ENV="production",
        REQUIRE_AUTH=True,
        AUTH_SECRET_KEY="a-sufficiently-long-production-cryptographic-secret-key",
        SEC_USER_AGENT="ApolloCompliance sec-team@enterprise.org",
    )
    assert prod_valid.is_production is True


def test_production_login_rejects_email_only_and_unauthenticated() -> None:
    """In production, email-only login and empty login body must be strictly rejected."""
    client = TestClient(app)

    with patch("app.config.settings.APOLLO_ENV", "production"):
        # 1. Empty body in production
        res_empty = client.post("/api/auth/token", json={})
        assert res_empty.status_code == 401
        assert "Production authentication requires an API key" in res_empty.json()["detail"]

        # 2. Email-only login in production
        res_email = client.post("/api/auth/token", json={"email": "analyst@apollo.local"})
        assert res_email.status_code == 401
        assert "Email-only login is disabled in production" in res_email.json()["detail"]


# ==============================================================================
# 2. Tenant Authorization, Multi-User Isolation & Path Traversal
# ==============================================================================
def test_multi_user_workspace_isolation() -> None:
    """Verifies complete data isolation across users in distinct workspaces."""
    client = TestClient(app)

    user_tenant_1 = User(
        user_id="usr_t1",
        email="analyst1@corp1.com",
        name="Analyst Tenant 1",
        role=UserRole.ANALYST,
        active_workspace_id="ws_tenant_1",
    )
    token_1 = create_access_token(user_tenant_1)

    user_tenant_2 = User(
        user_id="usr_t2",
        email="analyst2@corp2.com",
        name="Analyst Tenant 2",
        role=UserRole.ANALYST,
        active_workspace_id="ws_tenant_2",
    )
    token_2 = create_access_token(user_tenant_2)

    # 1. Tenant 1 creates a research run
    create_res = client.post(
        "/api/runs",
        json={"ticker_or_name": "AAPL", "objective": "Analyze Apple financial liquidity"},
        headers={"Authorization": f"Bearer {token_1}"},
    )
    assert create_res.status_code == 200
    run_1_id = create_res.json()["run"]["run_id"]

    # 2. Tenant 2 tries to fetch Tenant 1's run -> 403 Forbidden
    res_run_t2 = client.get(
        f"/api/runs/{run_1_id}",
        headers={"Authorization": f"Bearer {token_2}"},
    )
    assert res_run_t2.status_code == 403

    # 3. Tenant 2 tries to fetch evidence for Tenant 1's run -> 403 Forbidden
    res_ev_t2 = client.get(
        f"/api/runs/{run_1_id}/evidence",
        headers={"Authorization": f"Bearer {token_2}"},
    )
    assert res_ev_t2.status_code == 403

    # 4. Tenant 2 tries to fetch approvals for Tenant 1's run -> 403 Forbidden
    res_appr_t2 = client.get(
        f"/api/runs/{run_1_id}/approvals",
        headers={"Authorization": f"Bearer {token_2}"},
    )
    assert res_appr_t2.status_code == 403

    # 5. Tenant 2 tries to submit approval for Tenant 1's run -> 403 Forbidden
    res_post_appr_t2 = client.post(
        f"/api/runs/{run_1_id}/approvals",
        json={"decision": "APPROVED"},
        headers={"Authorization": f"Bearer {token_2}"},
    )
    assert res_post_appr_t2.status_code == 403


def test_pdf_report_path_traversal_prevention() -> None:
    """Verifies that malicious path traversal attempts on report endpoints are blocked."""
    client = TestClient(app)
    user = User(
        user_id="usr_traversal_test",
        email="sec@apollo.local",
        name="Security Analyst",
        role=UserRole.ANALYST,
        active_workspace_id="ws_default",
    )
    token = create_access_token(user)

    # Attempting directory traversal
    traversal_filenames = [
        "../../../../etc/passwd",
        "..%2F..%2F..%2Fetc%2Fpasswd",
        "/etc/passwd",
        "nested/../../secret.txt",
    ]

    for bad_file in traversal_filenames:
        res = client.get(
            f"/api/reports/pdf/{bad_file}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code in (400, 404), f"Failed to reject path traversal: {bad_file}"


# ==============================================================================
# 3. PostgreSQL Checkpoint Failures Fatal in Production
# ==============================================================================
def test_postgres_checkpoint_failure_fatal_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """When postgres checkpointer fails in production, it must raise a fatal error, never fall back to MemorySaver."""
    monkeypatch.setattr("app.config.settings.APOLLO_ENV", "production")

    with pytest.raises(RuntimeError, match="Fatal PostgreSQL checkpointer initialization failure in production"):
        get_checkpointer("postgresql://invalid:invalid@localhost:5432/bad_db")


def test_in_memory_checkpointer_prohibited_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production mode must forbid volatile memory checkpointer."""
    monkeypatch.setattr("app.config.settings.APOLLO_ENV", "production")

    with pytest.raises(RuntimeError, match="In-memory checkpointing is prohibited in production"):
        get_checkpointer(database_url="memory")


# ==============================================================================
# 4. Durable State & Evidence Persistence Across Processes
# ==============================================================================
def test_durable_evidence_persistence_across_process_instances(tmp_path: pytest.TempPathFactory) -> None:
    """Verifies that research state, sources, and evidence survive process restart."""
    db_file = tmp_path / "test_durable_research.db"

    # Process Instance 1: Create store, save source & evidence
    store1 = RunStore(db_path=db_file)
    registry1 = EvidenceRegistry(run_id="run_durable_123", store=store1)

    src = SourceDocument(
        source_id="src_dur_001",
        run_id="run_durable_123",
        issuer_cik="0000320193",
        accession_number="0000320193-23-000106",
        form_type="10-K",
        filed_at="2023-11-03",
        period_of_report="2023-09-30",
        title="Apple Inc. 10-K",
        source_url="https://sec.gov/Archives/edgar/data/320193/test.htm",
    )
    registry1.add_source(src)

    ev = EvidenceRecord(
        evidence_id="ev_dur_001",
        run_id="run_durable_123",
        source_id=src.source_id,
        locator="Item 8 - Note 1",
        excerpt="Total revenue was $383,285 million in fiscal 2023.",
        fact_name="Revenues",
        value=Decimal("383285000000"),
        unit="USD",
        period_end="2023-09-30",
        fiscal_period="FY2023",
        validation_status=EvidenceValidationStatus.VALID,
    )
    registry1.add_evidence(ev)

    # Process Instance 2: Brand new store and registry from the same DB file
    store2 = RunStore(db_path=db_file)
    registry2 = EvidenceRegistry(run_id="run_durable_123", store=store2)

    # Evidence and sources must be fully hydrated from database
    persisted_ev = registry2.get_evidence("ev_dur_001")
    assert persisted_ev is not None
    assert persisted_ev.fact_name == "Revenues"
    assert persisted_ev.value == Decimal("383285000000")
    assert persisted_ev.unit == "USD"

    persisted_src = registry2.get_source("src_dur_001")
    assert persisted_src is not None
    assert persisted_src.form_type == "10-K"

    # Cross-run isolation in registry
    assert len(registry2.list_for_run("run_durable_123")) == 1
    assert len(registry2.list_for_run("other_run_999")) == 0


# ==============================================================================
# 5. Plugin Execution Deadlines & Fail-Closed Capability Grants
# ==============================================================================
def test_plugin_execution_deadline_timeout() -> None:
    """Plugin exceeding execution deadline must raise PluginTimeoutError and terminate."""
    manifest = PluginManifest(
        plugin_id="slow_plugin",
        display_name="Slow Plugin",
        version="1.0",
        plugin_type="financial_analytics",
        capabilities=["test.capability"],
    )
    gate = PluginPolicyGate()
    gate.grant_capabilities("slow_plugin", ["test.capability"])
    executor = GuardedPluginExecutor(policy_gate=gate, default_timeout=0.2)

    mock_plugin = MagicMock()
    mock_plugin.manifest = manifest

    def slow_func() -> str:
        time.sleep(1.0)
        return "finished"

    with pytest.raises(PluginTimeoutError, match="exceeded deadline"):
        executor.execute(mock_plugin, "test.capability", slow_func, timeout=0.1)


def test_plugin_fail_closed_capability_policy() -> None:
    """Ungranted capabilities in fail-closed policy mode must raise UnauthorizedCapabilityError."""
    manifest = PluginManifest(
        plugin_id="untrusted_plugin",
        display_name="Untrusted Plugin",
        version="1.0",
        plugin_type="financial_analytics",
        capabilities=["network.unrestricted"],
    )
    gate = PluginPolicyGate(fail_closed=True)
    executor = GuardedPluginExecutor(policy_gate=gate)

    mock_plugin = MagicMock()
    mock_plugin.manifest = manifest

    with pytest.raises(UnauthorizedCapabilityError, match="not granted under fail-closed capability policy"):
        executor.execute(mock_plugin, "network.unrestricted", lambda: "pwned")


# ==============================================================================
# 6. Evidence-Based Question Completion & Claim Isolation
# ==============================================================================
def test_evidence_based_question_completion_criteria() -> None:
    """A research question with expected_evidence criteria must not be marked supported if criteria are unfulfilled."""
    import uuid
    run_id = f"run_crit_{uuid.uuid4().hex[:8]}"
    registry = EvidenceRegistry(run_id=run_id)

    q = ResearchQuestion(
        question_id="Q_CLOUD_REV",
        section_id="sec_1",
        category="segment_performance",
        question="What were Microsoft Cloud revenues?",
        priority=1,
        expected_evidence=["RevenueFromContractWithCustomerExcludingAssessedTax"],
    )

    # Case A: No evidence registered -> question is not supported (GAP / UNANSWERED)
    assessment, updated_qs = GapDetectionService.evaluate_coverage(run_id, [q], registry)
    assert assessment.supported_count == 0
    assert updated_qs[0].status != QuestionStatus.SUPPORTED

    # Case B: Register unrelated evidence without the expected criteria
    registry.add_evidence(EvidenceRecord(
        evidence_id=f"ev_unrelated_{uuid.uuid4().hex[:6]}",
        run_id=run_id,
        source_id="src_dummy",
        locator="Item 1",
        excerpt="General disclosure about company products.",
        evidence_type=EvidenceType.NARRATIVE_PASSAGE,
        validation_status=EvidenceValidationStatus.VALID,
        question_ids=["Q_CLOUD_REV"],
    ))
    assessment_unrelated, updated_qs_unrelated = GapDetectionService.evaluate_coverage(run_id, [q], registry)
    assert assessment_unrelated.supported_count == 0
    assert updated_qs_unrelated[0].status != QuestionStatus.SUPPORTED

    # Case C: Register evidence satisfying the expected criteria
    matched_ev_id = f"ev_matched_{uuid.uuid4().hex[:6]}"
    registry.add_evidence(EvidenceRecord(
        evidence_id=matched_ev_id,
        run_id=run_id,
        source_id="src_dummy",
        locator="Item 8 Note 19",
        excerpt="Cloud revenue under RevenueFromContractWithCustomerExcludingAssessedTax was $111B.",
        fact_name="RevenueFromContractWithCustomerExcludingAssessedTax",
        value=Decimal("111000000000"),
        unit="USD",
        evidence_type=EvidenceType.NUMERIC_FACT,
        validation_status=EvidenceValidationStatus.VALID,
        question_ids=["Q_CLOUD_REV"],
    ))
    assessment_satisfied, updated_qs_satisfied = GapDetectionService.evaluate_coverage(run_id, [q], registry)
    assert assessment_satisfied.supported_count == 1
    assert updated_qs_satisfied[0].status == QuestionStatus.SUPPORTED
    assert matched_ev_id in updated_qs_satisfied[0].evidence_ids


def test_cross_run_evidence_claim_validation_rejection() -> None:
    """Claims citing evidence from another research run must be rejected to prevent cross-run contamination."""
    import uuid
    run_id = f"run_current_{uuid.uuid4().hex[:8]}"
    foreign_run_id = f"run_foreign_{uuid.uuid4().hex[:8]}"
    foreign_ev_id = f"ev_foreign_{uuid.uuid4().hex[:6]}"

    registry = EvidenceRegistry(run_id=run_id)

    # Evidence belonging to a previous / separate run
    foreign_ev = EvidenceRecord(
        evidence_id=foreign_ev_id,
        run_id=foreign_run_id,
        source_id="src_foreign",
        locator="Item 8",
        excerpt="Foreign company revenue data.",
        fact_name="Revenues",
        value=Decimal("500000000"),
        validation_status=EvidenceValidationStatus.VALID,
    )
    registry.add_evidence(foreign_ev)

    claim = Claim(
        claim_id="clm_001",
        section_id="sec_1",
        text="Reported revenue of $500M",
        evidence_ids=[foreign_ev_id],
    )

    result = ValidationService.validate_claims([claim], registry, run_id=run_id)
    assert result.is_valid is False
    assert "clm_001" in result.unsupported_claims
    assert any(f"cross-run evidence_id '{foreign_ev_id}'" in err for err in result.errors)


# ==============================================================================
# 7. Financial Analytics: Annual/Quarterly Isolation, Units, and Lineage
# ==============================================================================
def test_financial_analytics_annual_quarterly_isolation_and_deduplication() -> None:
    """Verifies that quarterly records are excluded from annual series, duplicate periods deduplicated, and lineage recorded."""
    plugin = FinancialAnalyticsPlugin()

    records = [
        # Annual FY2022
        EvidenceRecord(
            evidence_id="ev_rev_2022",
            source_id="src_dummy",
            locator="Item 8",
            fact_name="Revenues",
            value=Decimal("100000000"),
            unit="USD",
            period_start="2022-01-01",
            period_end="2022-12-31",
            fiscal_period="FY2022",
        ),
        # Quarterly Q1 2023 (should be excluded from annual series)
        EvidenceRecord(
            evidence_id="ev_rev_q1_2023",
            source_id="src_dummy",
            locator="Item 8",
            fact_name="Revenues",
            value=Decimal("28000000"),
            unit="USD",
            period_start="2023-01-01",
            period_end="2023-03-31",
            fiscal_period="Q1",
        ),
        # Duplicate Annual FY2023 (first)
        EvidenceRecord(
            evidence_id="ev_rev_2023_v1",
            source_id="src_dummy",
            locator="Item 8",
            fact_name="Revenues",
            value=Decimal("120000000"),
            unit="USD",
            period_start="2023-01-01",
            period_end="2023-12-31",
            fiscal_period="FY2023",
            metadata={"extracted_at": "2024-01-01T00:00:00Z"},
        ),
        # Duplicate Annual FY2023 (more recent extraction)
        EvidenceRecord(
            evidence_id="ev_rev_2023_v2",
            source_id="src_dummy",
            locator="Item 8",
            fact_name="Revenues",
            value=Decimal("120000000"),
            unit="USD",
            period_start="2023-01-01",
            period_end="2023-12-31",
            fiscal_period="FY2023",
            metadata={"extracted_at": "2024-02-01T00:00:00Z"},
        ),
        # Operating income with matching annual period
        EvidenceRecord(
            evidence_id="ev_op_2023",
            source_id="src_dummy",
            locator="Item 8",
            fact_name="OperatingIncomeLoss",
            value=Decimal("30000000"),
            unit="USD",
            period_start="2023-01-01",
            period_end="2023-12-31",
            fiscal_period="FY2023",
        ),
    ]

    result = plugin.compute_metrics(records)

    # 1. Quarterly period (Q1) must NOT be in revenue_series
    rev_series = result["trends"]["revenue_series"]
    assert len(rev_series) == 2  # FY2022 and FY2023 only
    periods = [s["period"] for s in rev_series]
    assert "2023-03-31" not in periods
    assert "2022-12-31" in periods
    assert "2023-12-31" in periods

    # 2. Duplicate period was deduplicated deterministically
    assert len([s for s in rev_series if s["period"] == "2023-12-31"]) == 1

    # 3. YoY Growth computation and calculation lineage
    yoy_growth = result["ratios"]["revenue_yoy_growth"]
    assert yoy_growth["value"] == 20.0
    assert yoy_growth["formula"] == "((latest_revenue - prior_revenue) / abs(prior_revenue)) * 100"
    assert "lineage" in yoy_growth

    # 4. Operating Margin lineage
    op_margin = result["ratios"]["operating_margin"]
    assert op_margin["value"] == 25.0
    assert op_margin["formula"] == "(operating_income / revenue) * 100"
    assert op_margin["lineage"]["operating_income_evidence_id"] == "ev_op_2023"


def test_financial_analytics_rejects_unit_mismatches() -> None:
    """Verifies that comparing mismatched currency units prevents invalid ratio calculations."""
    plugin = FinancialAnalyticsPlugin()

    records = [
        # Revenue in USD
        EvidenceRecord(
            evidence_id="ev_rev_usd",
            source_id="src_dummy",
            locator="Item 8",
            fact_name="Revenues",
            value=Decimal("100000000"),
            unit="USD",
            period_start="2023-01-01",
            period_end="2023-12-31",
            fiscal_period="FY2023",
        ),
        # Operating income in EUR
        EvidenceRecord(
            evidence_id="ev_op_eur",
            source_id="src_dummy",
            locator="Item 8",
            fact_name="OperatingIncomeLoss",
            value=Decimal("20000000"),
            unit="EUR",
            period_start="2023-01-01",
            period_end="2023-12-31",
            fiscal_period="FY2023",
        ),
    ]

    result = plugin.compute_metrics(records)

    # Operating margin should not be calculated due to unit mismatch (USD vs EUR)
    assert "operating_margin" not in result["ratios"]


# ==============================================================================
# 8. Workflow Terminal Events for Incomplete Reports
# ==============================================================================
def test_render_pdf_node_emits_run_incomplete_event() -> None:
    """An incomplete report must emit RUN_INCOMPLETE terminal event, not RUN_COMPLETED."""
    from app.graph.nodes import render_pdf_node
    from app.plugins.builtin.pdf_exporter.plugin import PDFExporterPlugin

    published_events = []

    def mock_publish(run_id: str, event_type: str, message: str, payload: dict | None = None) -> None:
        published_events.append((event_type, message, payload))

    report = FinalReport(
        report_id="rpt_incomplete_test",
        run_id="run_incomplete_test",
        ticker="TEST",
        cik="0000000000",
        company_name="Test Company",
        objective="Analyze test company",
        status=RunStatus.INCOMPLETE,
        executive_summary="Incomplete report summary",
        sections=[
            SectionDraft(
                section_id="sec_1",
                title="Overview",
                narrative="Incomplete overview due to missing required facts.",
                claims=[],
            )
        ],
    )

    mock_context = MagicMock()
    mock_pdf_plugin = PDFExporterPlugin()
    mock_context.plugin_registry.get_typed_plugin.return_value = mock_pdf_plugin
    mock_context.plugin_registry.executor.execute.side_effect = lambda plugin, cap, func, *args, **kwargs: func(*args, **kwargs)

    state = {
        "final_report": report,
        "run": ResearchRun(
            run_id="run_incomplete_test",
            ticker="TEST",
            cik="0000000000",
            company_name="Test Company",
            objective="Analyze test company",
            status=RunStatus.INCOMPLETE,
        ),
    }

    with patch.object(event_broadcaster, "publish", side_effect=mock_publish):
        render_pdf_node(state, mock_context)

    # Verify terminal event
    event_types = [e[0] for e in published_events]
    assert "RUN_INCOMPLETE" in event_types, f"Expected RUN_INCOMPLETE event, found: {event_types}"
    assert "RUN_COMPLETED" not in event_types, "RUN_COMPLETED must not be emitted for an INCOMPLETE report"
