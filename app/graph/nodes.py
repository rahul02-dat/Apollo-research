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
from app.services.event_stream import event_broadcaster
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
    event_broadcaster.publish(
        run.run_id,
        "NORMALIZE_REQUEST",
        f"Normalized research objective for {normalized_run.company_name or 'issuer'}",
        {"objective": normalized_run.objective},
    )
    return {
        "run": normalized_run,
        "current_step": "normalize_request",
    }


def resolve_issuer_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    source_plugin = context.plugin_registry.get_typed_plugin(context.source_plugin_id, SourceConnector)
    resolved_run = context.apollo.resolve_issuer(run, source_plugin)
    event_broadcaster.publish(
        run.run_id,
        "RESOLVE_ISSUER",
        f"Resolved issuer {resolved_run.company_name} (CIK: {resolved_run.cik})",
        {"cik": resolved_run.cik, "ticker": resolved_run.ticker, "company_name": resolved_run.company_name},
    )
    return {
        "run": resolved_run,
        "current_step": "resolve_issuer",
    }


def plan_research_node(state: ApolloWorkflowState, context: WorkflowContext) -> ApolloWorkflowState:
    run = state["run"]
    itinerary = context.apollo.plan_research(run)
    updated_run = run.model_copy(update={"status": RunStatus.AWAITING_APPROVAL})
    event_broadcaster.publish(
        run.run_id,
        "PLAN_PROPOSED",
        f"Formulated research itinerary with {len(itinerary.sections)} sections and {len(itinerary.questions)} inquiry dimensions",
        {
            "sections": [s.title for s in itinerary.sections],
            "questions": [q.question for q in itinerary.questions],
        },
    )
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
        event_broadcaster.publish(
            run.run_id,
            "APPROVAL_RECEIVED",
            "Research plan approved by analyst; initiating autonomous SEC retrieval",
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

    event_broadcaster.publish(
        run.run_id,
        "ATHENA_RETRIEVAL_STARTED",
        f"Athena retrieving primary-source SEC filings for CIK {run.cik}",
    )

    context.athena.retrieve_initial_evidence(
        cik=run.cik or "0000000000",
        questions=itinerary.questions,
        source_plugin_id=context.source_plugin_id,
    )

    evidence_count = len(context.evidence_registry.list_for_run(run.run_id))
    sources = context.evidence_registry.list_sources_for_run(run.run_id)
    event_broadcaster.publish(
        run.run_id,
        "EVIDENCE_EXTRACTED",
        f"Athena extracted {evidence_count} evidence records from {len(sources)} SEC source filings",
        {"evidence_count": evidence_count, "source_count": len(sources)},
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

    unanswered = assessment.unanswered_count
    gaps = assessment.gap_count
    event_broadcaster.publish(
        run.run_id,
        "HERMES_EVALUATING",
        f"Hermes gap analysis: {len(itinerary.questions) - unanswered}/{len(itinerary.questions)} questions answered, {gaps} gaps identified (Round {run.followup_round}/{run.max_followup_rounds})",
        {"unanswered": unanswered, "gaps": gaps, "supported": assessment.supported_count},
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
        event_broadcaster.publish(
            run.run_id,
            "GAP_DETECTED",
            f"Hermes routing follow-up search for '{next_gap.question_id}': {next_gap.reason}",
            {"question_id": next_gap.question_id, "filing_types": next_gap.follow_up.filing_types},
        )
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
    event_broadcaster.publish(
        run.run_id,
        "SYNTHESIS_STARTED",
        f"Synthesizing {len(itinerary.sections)} report sections using {context.model_plugin_id} and financial analytics",
    )

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
    total_claims = sum(len(s.claims) for s in final_report.sections)
    event_broadcaster.publish(
        run.run_id,
        "VALIDATION_COMPLETED",
        f"Report assembled with deterministic validation status: {final_report.status.value}. Verified {total_claims} factual claims",
        {"status": final_report.status.value, "claim_count": total_claims},
    )

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

    event_broadcaster.publish(
        report.run_id,
        "PDF_GENERATED",
        f"Generated ReportLab PDF artifact: {artifact.file_path}",
        {"artifact_id": artifact.artifact_id, "file_path": artifact.file_path, "file_size_bytes": artifact.file_size_bytes},
    )
    terminal_event = (
        "RUN_COMPLETED" if report.status == RunStatus.COMPLETE
        else "RUN_INCOMPLETE" if report.status == RunStatus.INCOMPLETE
        else "RUN_TERMINATED"
    )
    terminal_message = (
        f"Research run {report.run_id} completed successfully!"
        if report.status == RunStatus.COMPLETE
        else f"Research run {report.run_id} finished with incomplete validation coverage."
        if report.status == RunStatus.INCOMPLETE
        else f"Research run {report.run_id} finished with status {report.status.value}."
    )
    event_broadcaster.publish(
        report.run_id,
        terminal_event,
        terminal_message,
        {"status": report.status.value},
    )

    return {
        "report_artifact": artifact,
        "current_step": "render_pdf",
    }

