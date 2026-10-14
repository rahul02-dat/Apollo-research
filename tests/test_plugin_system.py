"""Acceptance Tests AT-13, AT-14, AT-15, AT-16, AT-17: Plugin System Architecture."""

from typing import Any
import pytest
from app.models.reports import FinalReport, SectionDraft
from app.models.research import ResearchRun, RunStatus
from app.models.sources import SourceDocumentRef, SourceQuery
from app.plugins.manifest import PluginManifest
from app.plugins.policy import (
    IncompatiblePluginError,
    PluginPolicyError,
    PluginPolicyGate,
    UnauthorizedCapabilityError,
)
from app.plugins.registry import PluginRegistrationError, PluginRegistry
from app.plugins.execution import GuardedPluginExecutor, PluginExecutionError


def test_at13_plugin_contract_and_manifest_validation() -> None:
    registry = PluginRegistry()

    # 1. Invalid manifest: empty plugin_id
    class BadManifestPlugin:
        manifest = PluginManifest(
            plugin_id="",
            display_name="Bad Plugin",
            version="1.0.0",
            api_version="1.0",
            plugin_type="source_connector",
        )

    with pytest.raises(PluginPolicyError):
        registry.register(BadManifestPlugin())

    # 2. Incompatible API version
    class IncompatibleVersionPlugin:
        manifest = PluginManifest(
            plugin_id="bad_version",
            display_name="Old Plugin",
            version="1.0.0",
            api_version="0.1",  # Incompatible with host 1.0
            plugin_type="source_connector",
        )

    with pytest.raises(IncompatiblePluginError):
        registry.register(IncompatibleVersionPlugin())

    # 3. Missing required method for contract type
    class MissingMethodSourcePlugin:
        manifest = PluginManifest(
            plugin_id="missing_method",
            display_name="Incomplete Source",
            version="1.0.0",
            api_version="1.0",
            plugin_type="source_connector",
        )
        # Missing search, fetch, resolve_issuer, get_company_facts

    with pytest.raises(PluginRegistrationError):
        registry.register(MissingMethodSourcePlugin())


def test_at14_plugin_substitution(fake_source: Any, sample_html_content: bytes) -> None:
    """AT-14: Replacing SEC source with fake source without modifying graph or agent code."""
    registry = PluginRegistry()
    registry.register(fake_source)

    # Resolve issuer and search filings via registry lookup
    plugin = registry.get_plugin("fake_source")
    assert plugin.manifest.plugin_id == "fake_source"

    resolved = plugin.resolve_issuer("MSFT")
    assert resolved["cik"] == "0000789019"

    refs = plugin.search(SourceQuery(query_id="Q1", issuer_cik="0000789019"))
    assert len(refs) == 1
    assert refs[0].plugin_id == "fake_source"

    doc = plugin.fetch(refs[0])
    assert doc == sample_html_content


def test_at15_plugin_permission_enforcement() -> None:
    """AT-15: Plugin cannot execute undeclared or ungranted capabilities."""
    gate = PluginPolicyGate()
    executor = GuardedPluginExecutor(gate)

    manifest = PluginManifest(
        plugin_id="restricted_plugin",
        display_name="Restricted Plugin",
        version="1.0.0",
        api_version="1.0",
        plugin_type="source_connector",
        capabilities=["sec.filings.search"],  # Only declared search
    )

    class MockPlugin:
        def __init__(self, m: PluginManifest) -> None:
            self.manifest = m

        def allowed_op(self) -> str:
            return "ok"

        def unauthorized_op(self) -> str:
            return "should_not_run"

    p = MockPlugin(manifest)

    # Declared capability succeeds
    result = executor.execute(p, "sec.filings.search", p.allowed_op)
    assert result == "ok"

    # Undeclared capability MUST be rejected by policy
    with pytest.raises(UnauthorizedCapabilityError):
        executor.execute(p, "sec.facts.fetch", p.unauthorized_op)


def test_at16_plugin_failure_containment() -> None:
    """AT-16: Malformed/failing plugin output is contained without corrupting state."""
    executor = GuardedPluginExecutor()

    manifest = PluginManifest(
        plugin_id="failing_plugin",
        display_name="Failing Plugin",
        version="1.0.0",
        api_version="1.0",
        plugin_type="document_extractor",
        capabilities=["documents.html.extract"],
    )

    class CrashingPlugin:
        def __init__(self, m: PluginManifest) -> None:
            self.manifest = m

        def crash(self) -> None:
            raise ValueError("Corrupt file format encountered in third-party parser")

    plugin = CrashingPlugin(manifest)

    with pytest.raises(PluginExecutionError) as exc_info:
        executor.execute(plugin, "documents.html.extract", plugin.crash)

    assert exc_info.value.plugin_id == "failing_plugin"
    assert "Corrupt file format" in str(exc_info.value)


def test_at17_exporter_substitution(fake_exporter: Any) -> None:
    """AT-17: Second exporter can consume validated report model without synthesis modifications."""
    registry = PluginRegistry()
    registry.register(fake_exporter)

    report = FinalReport(
        report_id="RPT_TEST_17",
        run_id="RUN_TEST_17",
        company_name="APPLE INC",
        ticker="AAPL",
        cik="0000320193",
        objective="Analyze performance",
        status=RunStatus.COMPLETE,
        executive_summary="Summary of Apple performance.",
        sections=[],
        bibliography=[],
        unresolved_limitations=[],
        is_complete=True,
    )

    exporter = registry.get_plugin("markdown_exporter")
    artifact = exporter.export(report)

    assert artifact.format == "MARKDOWN"
    assert artifact.is_complete is True
    assert artifact.run_id == "RUN_TEST_17"
