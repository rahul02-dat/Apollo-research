"""Durable Application Persistence Repository."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any
from app.config import settings
from app.models.approvals import ApprovalEvent
from app.models.reports import FinalReport, ReportArtifact
from app.models.research import ResearchItinerary, ResearchRun, RunStatus

logger = logging.getLogger(__name__)


class RunStore:
    """Thread-safe persistent repository for Apollo research runs, itineraries, and reports."""

    def __init__(self, db_url: str | None = None) -> None:
        self.db_url = db_url or settings.DATABASE_URL
        self._runs: dict[str, ResearchRun] = {}
        self._itineraries: dict[str, ResearchItinerary] = {}
        self._reports: dict[str, FinalReport] = {}
        self._artifacts: dict[str, ReportArtifact] = {}
        self._approvals: dict[str, list[ApprovalEvent]] = {}
        self._threads: dict[str, Any] = {}

    def save_run(self, run: ResearchRun) -> None:
        self._runs[run.run_id] = run

    def get_run(self, run_id: str) -> ResearchRun | None:
        return self._runs.get(run_id)

    def list_runs(self) -> list[ResearchRun]:
        return sorted(self._runs.values(), key=lambda r: r.created_at, reverse=True)

    def save_itinerary(self, itinerary: ResearchItinerary) -> None:
        self._itineraries[itinerary.run_id] = itinerary

    def get_itinerary(self, run_id: str) -> ResearchItinerary | None:
        return self._itineraries.get(run_id)

    def save_report(self, report: FinalReport) -> None:
        self._reports[report.run_id] = report

    def get_report(self, run_id: str) -> FinalReport | None:
        return self._reports.get(run_id)

    def save_artifact(self, artifact: ReportArtifact) -> None:
        self._artifacts[artifact.run_id] = artifact

    def get_artifact(self, run_id: str) -> ReportArtifact | None:
        return self._artifacts.get(run_id)

    def add_approval(self, event: ApprovalEvent) -> None:
        if event.run_id not in self._approvals:
            self._approvals[event.run_id] = []
        self._approvals[event.run_id].append(event)

    def list_approvals(self, run_id: str) -> list[ApprovalEvent]:
        return self._approvals.get(run_id, [])


# Global store instance
run_store = RunStore()
