"""Workflow Execution and Orchestration Manager."""

import logging
import threading
import uuid
from typing import Any
from app.config import settings
from app.graph.nodes import WorkflowContext
from app.graph.workflow import build_research_graph
from app.models.approvals import ApprovalCheckpoint, ApprovalDecision, ApprovalEvent
from app.models.reports import FinalReport, ReportArtifact
from app.models.research import ResearchItinerary, ResearchRun, RunStatus
from app.persistence.checkpointer import get_checkpointer
from app.persistence.database import RunStore, run_store
from app.plugins.builtin import register_builtin_plugins
from app.plugins.registry import PluginRegistry
from app.services.event_stream import event_broadcaster
from app.services.evidence_registry import EvidenceRegistry

logger = logging.getLogger(__name__)


class WorkflowManager:
    """Manages LangGraph executions, background runs, and state transitions."""

    def __init__(
        self,
        plugin_registry: PluginRegistry | None = None,
        store: RunStore | None = None,
    ) -> None:
        self.plugin_registry = plugin_registry or PluginRegistry()
        register_builtin_plugins(self.plugin_registry)

        self.store = store or run_store
        self._contexts: dict[str, WorkflowContext] = {}
        self._checkpointers: dict[str, Any] = {}
        self._lock = threading.Lock()

    def get_or_create_context(self, run_id: str, source_plugin_id: str = "sec_edgar") -> WorkflowContext:
        with self._lock:
            if run_id not in self._contexts:
                ev_registry = EvidenceRegistry()
                ctx = WorkflowContext(
                    plugin_registry=self.plugin_registry,
                    evidence_registry=ev_registry,
                    source_plugin_id=source_plugin_id,
                    model_plugin_id=settings.DEFAULT_LLM_PROVIDER,
                )
                self._contexts[run_id] = ctx
            return self._contexts[run_id]

    def create_run(self, ticker_or_name: str, objective: str, source_plugin_id: str = "sec_edgar") -> tuple[ResearchRun, ResearchItinerary]:
        """Creates a research run, normalizes the request, resolves the issuer, and plans the itinerary."""
        run_id = f"RUN_{uuid.uuid4().hex[:12].upper()}"
        initial_run = ResearchRun(
            run_id=run_id,
            company_name=ticker_or_name,
            ticker=ticker_or_name.upper() if len(ticker_or_name) <= 5 and ticker_or_name.isalpha() else None,
            objective=objective,
            status=RunStatus.PLANNING,
            max_followup_rounds=settings.MAX_FOLLOWUP_ROUNDS,
        )

        ctx = self.get_or_create_context(run_id, source_plugin_id=source_plugin_id)
        checkpointer = get_checkpointer()
        self._checkpointers[run_id] = checkpointer

        # Build graph
        graph = build_research_graph(ctx, checkpointer=checkpointer, interrupt_for_approval=True)

        config = {"configurable": {"thread_id": run_id}}
        initial_state = {
            "run": initial_run,
            "plan_approved": False,
            "current_step": "init",
        }

        # Run up to approval checkpoint
        event_broadcaster.publish(run_id, "RUN_INITIATED", f"Initiating research run for '{ticker_or_name}'", {"objective": objective})
        final_state = graph.invoke(initial_state, config=config)

        run = final_state["run"]
        itinerary = final_state["itinerary"]

        self.store.save_run(run)
        if itinerary:
            self.store.save_itinerary(itinerary)

        logger.info("Created run %s for issuer %s (CIK: %s)", run.run_id, run.company_name, run.cik)
        return run, itinerary

    def approve_and_execute(
        self,
        run_id: str,
        decision: ApprovalDecision = ApprovalDecision.APPROVED,
        feedback: str | None = None,
        async_execution: bool = False,
    ) -> ResearchRun:
        """Records approval decision and resumes research workflow execution."""
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError(f"Run '{run_id}' not found.")

        event = ApprovalEvent(
            event_id=f"APP_{uuid.uuid4().hex[:8].upper()}",
            run_id=run_id,
            checkpoint=ApprovalCheckpoint.PLAN_APPROVAL,
            decision=decision,
            feedback=feedback,
        )
        self.store.add_approval(event)

        if decision == ApprovalDecision.REJECTED:
            event_broadcaster.publish(run_id, "RUN_REJECTED", "Research plan rejected by user.", {"feedback": feedback})
            updated_run = run.model_copy(update={"status": RunStatus.FAILED, "error_message": "Plan rejected by user."})
            self.store.save_run(updated_run)
            return updated_run

        # Execute resume logic
        if async_execution:
            event_broadcaster.publish(run_id, "RUN_RESUMED", "Workflow resumed in background async worker.")
            thread = threading.Thread(target=self._execute_workflow, args=(run_id,))
            thread.daemon = True
            thread.start()
            updated_run = run.model_copy(update={"status": RunStatus.RESEARCHING})
            self.store.save_run(updated_run)
            return updated_run
        else:
            return self._execute_workflow(run_id)

    def _execute_workflow(self, run_id: str) -> ResearchRun:
        ctx = self.get_or_create_context(run_id)
        checkpointer = self._checkpointers.get(run_id) or get_checkpointer()

        graph = build_research_graph(ctx, checkpointer=checkpointer, interrupt_for_approval=True)
        config = {"configurable": {"thread_id": run_id}}

        # Resume graph with approved state
        resume_state = {
            "plan_approved": True,
        }

        try:
            logger.info("Resuming research workflow for run %s", run_id)
            final_state = graph.invoke(resume_state, config=config)

            final_run = final_state["run"]
            self.store.save_run(final_run)

            if "final_report" in final_state and final_state["final_report"]:
                self.store.save_report(final_state["final_report"])

            if "report_artifact" in final_state and final_state["report_artifact"]:
                self.store.save_artifact(final_state["report_artifact"])

            if "itinerary" in final_state and final_state["itinerary"]:
                self.store.save_itinerary(final_state["itinerary"])

            logger.info("Workflow completed for run %s with status %s", run_id, final_run.status.value)
            return final_run
        except Exception as e:
            logger.exception("Workflow execution failed for run %s: %s", run_id, e)
            event_broadcaster.publish(run_id, "RUN_FAILED", f"Workflow execution failed: {e}")
            run = self.store.get_run(run_id)
            if run:
                failed_run = run.model_copy(update={"status": RunStatus.FAILED, "error_message": str(e)})
                self.store.save_run(failed_run)
                return failed_run
            raise


# Global workflow manager instance
workflow_manager = WorkflowManager()
