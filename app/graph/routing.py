"""LangGraph Conditional Routing Logic."""

import logging
from typing import Literal
from app.graph.state import ApolloWorkflowState

logger = logging.getLogger(__name__)


def check_plan_approval(state: ApolloWorkflowState) -> Literal["approved", "pending"]:
    """Determines whether the research plan has been approved by the user."""
    if state.get("plan_approved", False):
        return "approved"
    return "pending"


def should_continue_research(state: ApolloWorkflowState) -> Literal["followup", "synthesize"]:
    """Determines whether to trigger another targeted follow-up or proceed to synthesis."""
    run = state["run"]
    coverage = state.get("coverage")

    if not coverage:
        return "synthesize"

    # If all questions are supported, proceed to synthesis
    if coverage.is_fully_supported:
        logger.info("All research questions supported. Transitioning to synthesis.")
        return "synthesize"

    # If gaps exist and follow-up budget is not exhausted, follow up
    if coverage.gap_count > 0 and run.followup_round < run.max_followup_rounds:
        logger.info(
            "Gaps detected (%d gaps). Follow-up round %d of %d.",
            coverage.gap_count, run.followup_round + 1, run.max_followup_rounds,
        )
        return "followup"

    # Follow-up budget exhausted
    logger.info("Follow-up limit reached (%d rounds). Proceeding to synthesis with unresolved gaps.", run.max_followup_rounds)
    return "synthesize"
