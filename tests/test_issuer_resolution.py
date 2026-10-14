"""Acceptance Test AT-01: Issuer Resolution."""

from typing import Any
import pytest
from app.connectors.sec_edgar_client import SECResourceNotFoundError
from app.models.research import ResearchRun, RunStatus
from app.agents.apollo import ApolloOrchestrator
from app.plugins.registry import PluginRegistry


def test_at01_valid_issuer_resolution(plugin_registry: PluginRegistry, fake_source: Any) -> None:
    plugin_registry.register(fake_source, overwrite=True)
    apollo = ApolloOrchestrator(plugin_registry)

    run = ResearchRun(
        run_id="RUN_TEST_01",
        company_name="MSFT",
        ticker="MSFT",
        objective="Analyze annual results",
    )

    resolved = apollo.resolve_issuer(run, fake_source)
    assert resolved.cik == "0000789019"
    assert resolved.company_name == "MICROSOFT CORPORATION"
    assert resolved.ticker == "MSFT"


def test_at01_invalid_issuer_fails_safely(plugin_registry: PluginRegistry, fake_source: Any) -> None:
    plugin_registry.register(fake_source, overwrite=True)
    apollo = ApolloOrchestrator(plugin_registry)

    run = ResearchRun(
        run_id="RUN_TEST_INVALID",
        company_name="INVALID_TICKER_XYZ",
        ticker="XXXX",
        objective="Analyze invalid company",
    )

    with pytest.raises(SECResourceNotFoundError):
        apollo.resolve_issuer(run, fake_source)
