"""LangGraph StateGraph construction and compilation."""

import logging
from typing import Any
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from app.graph.nodes import (
    WorkflowContext,
    approve_plan_node,
    assemble_report_node,
    evaluate_gaps_node,
    normalize_request_node,
    plan_research_node,
    render_pdf_node,
    resolve_issuer_node,
    retrieve_evidence_node,
    route_followup_node,
    synthesize_sections_node,
)
from app.graph.routing import check_plan_approval, should_continue_research
from app.graph.state import ApolloWorkflowState

logger = logging.getLogger(__name__)


def build_research_graph(
    context: WorkflowContext,
    checkpointer: BaseCheckpointSaver | None = None,
    interrupt_for_approval: bool = True,
) -> Any:
    """Builds and compiles the Apollo LangGraph workflow."""
    builder = StateGraph(ApolloWorkflowState)

    # 1. Add nodes with context binding
    builder.add_node("normalize_request", lambda s: normalize_request_node(s, context))
    builder.add_node("resolve_issuer", lambda s: resolve_issuer_node(s, context))
    builder.add_node("plan_research", lambda s: plan_research_node(s, context))
    builder.add_node("approve_plan", lambda s: approve_plan_node(s, context))
    builder.add_node("retrieve_evidence", lambda s: retrieve_evidence_node(s, context))
    builder.add_node("evaluate_gaps", lambda s: evaluate_gaps_node(s, context))
    builder.add_node("route_followup", lambda s: route_followup_node(s, context))
    builder.add_node("synthesize_sections", lambda s: synthesize_sections_node(s, context))
    builder.add_node("assemble_report", lambda s: assemble_report_node(s, context))
    builder.add_node("render_pdf", lambda s: render_pdf_node(s, context))

    # 2. Add linear and conditional edges
    builder.add_edge(START, "normalize_request")
    builder.add_edge("normalize_request", "resolve_issuer")
    builder.add_edge("resolve_issuer", "plan_research")
    builder.add_edge("plan_research", "approve_plan")

    if interrupt_for_approval:
        builder.add_conditional_edges(
            "approve_plan",
            check_plan_approval,
            {
                "approved": "retrieve_evidence",
                "pending": END,
            },
        )
    else:
        builder.add_edge("approve_plan", "retrieve_evidence")

    builder.add_edge("retrieve_evidence", "evaluate_gaps")

    builder.add_conditional_edges(
        "evaluate_gaps",
        should_continue_research,
        {
            "followup": "route_followup",
            "synthesize": "synthesize_sections",
        },
    )

    builder.add_edge("route_followup", "evaluate_gaps")
    builder.add_edge("synthesize_sections", "assemble_report")
    builder.add_edge("assemble_report", "render_pdf")
    builder.add_edge("render_pdf", END)

    saver = checkpointer if checkpointer is not None else MemorySaver()
    compiled_graph = builder.compile(checkpointer=saver)
    return compiled_graph
