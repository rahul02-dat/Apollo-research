"""Acceptance Test AT-06: Human Approval and Resumable LangGraph State."""

from typing import Any
import pytest
from langgraph.checkpoint.memory import MemorySaver
from app.graph.nodes import WorkflowContext
from app.graph.workflow import build_research_graph
from app.models.research import ResearchRun, RunStatus
from app.plugins.registry import PluginRegistry
from app.services.evidence_registry import EvidenceRegistry


def test_at06_human_approval_pause_and_resume(
    plugin_registry: PluginRegistry,
    fake_source: Any,
) -> None:
    plugin_registry.register(fake_source, overwrite=True)
    ev_registry = EvidenceRegistry()
    ctx = WorkflowContext(
        plugin_registry=plugin_registry,
        evidence_registry=ev_registry,
        source_plugin_id="fake_source",
        model_plugin_id="mock",
    )

    checkpointer = MemorySaver()
    graph = build_research_graph(ctx, checkpointer=checkpointer, interrupt_for_approval=True)

    thread_id = "THREAD_APPROVAL_TEST_01"
    config = {"configurable": {"thread_id": thread_id}}

    initial_run = ResearchRun(
        run_id="RUN_AT06",
        company_name="MSFT",
        ticker="MSFT",
        objective="Analyze performance",
    )

    # 1. First execution: runs through plan_research and pauses at approve_plan
    state_step1 = graph.invoke(
        {"run": initial_run, "plan_approved": False, "current_step": "init"},
        config=config,
    )

    # Must be paused awaiting approval
    assert state_step1["run"].status == RunStatus.AWAITING_APPROVAL
    assert state_step1["itinerary"] is not None
    assert len(state_step1["itinerary"].sections) > 0

    # Retrieve checkpointed state using thread_id to ensure persistence
    checkpoint_tuple = checkpointer.get_tuple(config)
    assert checkpoint_tuple is not None
    saved_state = checkpoint_tuple.checkpoint["channel_values"]
    assert saved_state["run"].status == RunStatus.AWAITING_APPROVAL

    # 2. Resuming execution with user approval using the same thread_id
    state_step2 = graph.invoke(
        {"plan_approved": True},
        config=config,
    )

    # Workflow must have resumed and finished through synthesis and report generation
    assert state_step2["current_step"] in ["render_pdf", "assemble_report"]
    assert state_step2["final_report"] is not None
    assert len(state_step2["final_report"].sections) > 0
    assert state_step2["report_artifact"] is not None
