"""Apollo LangGraph Nodes."""

import logging
from typing import Any
from app.agents.apollo import ApolloOrchestrator
from app.agents.athena import AthenaResearchAgent
from app.agents.hermes import HermesAnalysisAgent
from app.graph.state import ApolloWorkflowState
from app.models.approvals import ApprovalCheckpoint, ApprovalDecision, ApprovalEvent
from app.models.reports import ReportArtifact
from app.models.research import RunStatus
from app.plugins.contracts import ModelProvider, ReportExporter, SourceConnector, SynthesisStrategy
from app.plugins.registry import PluginRegistry
from app.services.evidence_registry import EvidenceRegistry
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)


class WorkflowContext:
    """Dependency container for workflow execution."""

    def __init__(
        self,
        plugin_registry: PluginRegistry,
        evidence_registry: EvidenceRegistry | None = None,
        source_plugin_id: str = "sec_edgar",
        model_plugin_id: str = "ollama",
    ) -> None:
        self.plugin_registry = plugin_registry
        self.evidence_registry = evidence_registry or EvidenceRegistry()
        self.source_plugin_id = source_plugin_id
        self.model_plugin_id = model_plugin_id

        self.apollo = ApolloOrchestrator(self.plugin_registry)
        self.athena = AthenaResearchAgent(self.plugin_registry, self.evidence_registry)
        self.hermes = HermesAnalysisAgent(self.evidence_registry)


def normalize_request_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    normalized_run = context.apollo.normalize_request(run)
    return {
        "run": normalized_run,
        "current_step": "normalize_request",
    }


def resolve_issuer_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    source_plugin = context.plugin_registry.get_typed_plugin(context.source_plugin_id, SourceConnector)
    resolved_run = context.apollo.resolve_issuer(run, source_plugin)
    return {
        "run": resolved_run,
        "current_step": "resolve_issuer",
    }


def plan_research_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    itinerary = context.apollo.plan_research(run)
    updated_run = run.model_copy(update={"status": RunStatus.AWAITING_APPROVAL})
    return {
        "run": updated_run,
        "itinerary": itinerary,
        "current_step": "plan_research",
    }


def approve_plan_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    """Approval checkpoint node. If already approved, transitions to RESEARCHING."""
    run = state["run"]
    is_approved = state.get("plan_approved", False)

    if is_approved:
        updated_run = run.model_copy(update={"status": RunStatus.RESEARCHING})
        approval_events = list(state.get("approval_events", []))
        approval_events.append(
            ApprovalEvent(
                event_id=f"APP_PLAN_{run.run_id[:8]}",
                run_id=run.run_id,
                checkpoint=ApprovalCheckpoint.PLAN_APPROVAL,
                decision=ApprovalDecision.APPROVED,
            )
        )
        return {
            "run": updated_run,
            "approval_events": approval_events,
            "current_step": "approve_plan",
        }

    # Not yet approved
    return {
        "current_step": "awaiting_plan_approval",
    }


def retrieve_evidence_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    itinerary = state["itinerary"]
    assert itinerary is not None, "Itinerary is required for retrieval"

    context.athena.retrieve_initial_evidence(
        cik=run.cik or "0000000000",
        questions=itinerary.questions,
        source_plugin_id=context.source_plugin_id,
    )

    return {
        "current_step": "retrieve_evidence",
    }


def evaluate_gaps_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    itinerary = state["itinerary"]
    assert itinerary is not None

    assessment, updated_questions = context.hermes.evaluate_coverage(
        run_id=run.run_id,
        questions=itinerary.questions,
        current_round=run.followup_round,
        max_rounds=run.max_followup_rounds,
    )

    updated_itinerary = itinerary.model_copy(update={"questions": updated_questions})
    return {
        "coverage": assessment,
        "itinerary": updated_itinerary,
        "current_step": "evaluate_gaps",
    }


def route_followup_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    coverage = state.get("coverage")
    assert coverage is not None

    next_gap = context.hermes.identify_next_followup(coverage)
    if next_gap:
        context.athena.retrieve_followup_evidence(
            cik=run.cik or "0000000000",
            follow_up=next_gap.follow_up,
            target_question_id=next_gap.question_id,
            source_plugin_id=context.source_plugin_id,
        )

    updated_run = run.model_copy(update={"followup_round": run.followup_round + 1})
    return {
        "run": updated_run,
        "current_step": "route_followup",
    }


def synthesize_sections_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    itinerary = state["itinerary"]
    assert itinerary is not None

    updated_run = run.model_copy(update={"status": RunStatus.SYNTHESIZING})

    synthesis_plugin = context.plugin_registry.get_typed_plugin("financial_synthesis", SynthesisStrategy)
    model_plugin = context.plugin_registry.get_typed_plugin(context.model_plugin_id, ModelProvider)

    report_service = ReportService(context.evidence_registry, synthesis_plugin, model_plugin)
    drafts = report_service.synthesize_sections(updated_run, itinerary)

    return {
        "run": updated_run,
        "section_drafts": drafts,
        "current_step": "synthesize_sections",
    }


def assemble_report_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    itinerary = state["itinerary"]
    drafts = state["section_drafts"]
    assert itinerary is not None

    synthesis_plugin = context.plugin_registry.get_typed_plugin("financial_synthesis", SynthesisStrategy)
    model_plugin = context.plugin_registry.get_typed_plugin(context.model_plugin_id, ModelProvider)

    report_service = ReportService(context.evidence_registry, synthesis_plugin, model_plugin)
    final_report = report_service.assemble_report(run, itinerary, drafts)

    updated_run = run.model_copy(update={"status": final_report.status})

    return {
        "run": updated_run,
        "final_report": final_report,
        "current_step": "assemble_report",
    }


def render_pdf_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    report = state["final_report"]
    assert report is not None

    pdf_exporter = context.plugin_registry.get_typed_plugin("pdf", ReportExporter)
    artifact = context.plugin_registry.executor.execute(
        pdf_exporter,
        "report.pdf.export",
        pdf_exporter.export,
        report,
    )

    return {
        "report_artifact": artifact,
        "current_step": "render_pdf",
    }
