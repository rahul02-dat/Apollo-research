"""Durable Application Persistence Repository with SQLite WAL mode and multi-tenancy."""

import json
import logging
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from app.config import settings
from app.models.approvals import ApprovalEvent
from app.models.reports import FinalReport, ReportArtifact
from app.models.research import ResearchItinerary, ResearchRun, RunStatus

logger = logging.getLogger(__name__)


class RunStore:
    """Thread-safe persistent repository for Apollo research runs, itineraries, reports, and multi-tenant workspaces."""

    def __init__(self, db_url: str | None = None, database_url: str | None = None) -> None:
        self.db_url = database_url or db_url or settings.DATABASE_URL
        self._local = threading.local()
        self._lock = threading.Lock()

        # In-memory fast cache
        self._runs: dict[str, ResearchRun] = {}
        self._itineraries: dict[str, ResearchItinerary] = {}
        self._reports: dict[str, FinalReport] = {}
        self._artifacts: dict[str, ReportArtifact] = {}
        self._approvals: dict[str, list[ApprovalEvent]] = {}

        # Resolve SQLite file path
        if self.db_url.startswith("sqlite:///"):
            self._sqlite_path = self.db_url.replace("sqlite:///", "")
        else:
            self._sqlite_path = "./apollo_research.db"

        if self._sqlite_path != ":memory:":
            db_file = Path(self._sqlite_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

        self._init_schema()
        self._load_from_db()

    def _get_conn(self) -> sqlite3.Connection:
        """Returns a thread-local SQLite connection configured with WAL mode."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            conn = sqlite3.connect(self._sqlite_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            if self._sqlite_path != ":memory:":
                conn.execute("PRAGMA journal_mode=WAL;")
                conn.execute("PRAGMA synchronous=NORMAL;")
            self._local.conn = conn
        return self._local.conn

    def _init_schema(self) -> None:
        """Initializes tables for runs, itineraries, reports, artifacts, approvals, users, and workspaces."""
        with self._lock:
            conn = self._get_conn()
            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS runs (
                        run_id TEXT PRIMARY KEY,
                        user_id TEXT,
                        workspace_id TEXT,
                        requested_by TEXT,
                        company_name TEXT,
                        ticker TEXT,
                        cik TEXT,
                        objective TEXT,
                        status TEXT,
                        created_at TEXT,
                        updated_at TEXT,
                        error_message TEXT,
                        data_json TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_user ON runs (user_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_workspace ON runs (workspace_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_created ON runs (created_at DESC);")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS itineraries (
                        run_id TEXT PRIMARY KEY,
                        itinerary_id TEXT,
                        data_json TEXT
                    );
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS reports (
                        run_id TEXT PRIMARY KEY,
                        report_id TEXT,
                        data_json TEXT
                    );
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS artifacts (
                        run_id TEXT PRIMARY KEY,
                        artifact_id TEXT,
                        data_json TEXT
                    );
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS approvals (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT,
                        user_id TEXT,
                        event_data_json TEXT
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_approvals_run ON approvals (run_id);")

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        email TEXT UNIQUE,
                        name TEXT,
                        role TEXT,
                        api_key TEXT,
                        active_workspace_id TEXT,
                        created_at TEXT
                    );
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS workspaces (
                        workspace_id TEXT PRIMARY KEY,
                        name TEXT,
                        owner_id TEXT,
                        created_at TEXT
                    );
                """)

                # Seed default verified user and workspace
                conn.execute("""
                    INSERT OR IGNORE INTO users (user_id, email, name, role, api_key, active_workspace_id, created_at)
                    VALUES ('usr_primary_analyst', 'analyst@apollo.local', 'Senior Financial Analyst', 'ANALYST', 'apollo_ak_live_analyst_01', 'ws_default', datetime('now'));
                """)
                conn.execute("""
                    INSERT OR IGNORE INTO workspaces (workspace_id, name, owner_id, created_at)
                    VALUES ('ws_default', 'Default Workspace', 'usr_primary_analyst', datetime('now'));
                """)

    def _load_from_db(self) -> None:
        """Pre-loads existing records from the database into in-memory cache for fast lookups."""
        try:
            conn = self._get_conn()
            # 1. Load runs
            cur = conn.execute("SELECT data_json FROM runs")
            for row in cur.fetchall():
                try:
                    data = json.loads(row["data_json"])
                    run = ResearchRun.model_validate(data)
                    self._runs[run.run_id] = run
                except Exception as e:
                    logger.warning("Error deserializing run from DB: %s", e)

            # 2. Load itineraries
            cur = conn.execute("SELECT data_json FROM itineraries")
            for row in cur.fetchall():
                try:
                    data = json.loads(row["data_json"])
                    itin = ResearchItinerary.model_validate(data)
                    self._itineraries[itin.run_id] = itin
                except Exception as e:
                    logger.warning("Error deserializing itinerary from DB: %s", e)

            # 3. Load reports
            cur = conn.execute("SELECT data_json FROM reports")
            for row in cur.fetchall():
                try:
                    data = json.loads(row["data_json"])
                    rpt = FinalReport.model_validate(data)
                    self._reports[rpt.run_id] = rpt
                except Exception as e:
                    logger.warning("Error deserializing report from DB: %s", e)

            # 4. Load artifacts
            cur = conn.execute("SELECT data_json FROM artifacts")
            for row in cur.fetchall():
                try:
                    data = json.loads(row["data_json"])
                    art = ReportArtifact.model_validate(data)
                    self._artifacts[art.run_id] = art
                except Exception as e:
                    logger.warning("Error deserializing artifact from DB: %s", e)

            # 5. Load approvals
            cur = conn.execute("SELECT run_id, event_data_json FROM approvals")
            for row in cur.fetchall():
                try:
                    data = json.loads(row["event_data_json"])
                    appr = ApprovalEvent.model_validate(data)
                    if appr.run_id not in self._approvals:
                        self._approvals[appr.run_id] = []
                    self._approvals[appr.run_id].append(appr)
                except Exception as e:
                    logger.warning("Error deserializing approval from DB: %s", e)

            logger.info("Loaded %d runs, %d reports from durable database (%s)", len(self._runs), len(self._reports), self._sqlite_path)
        except Exception as e:
            logger.warning("Could not pre-load records from DB: %s", e)

    # --- Run Methods ---
    def save_run(self, run: ResearchRun) -> None:
        self._runs[run.run_id] = run
        try:
            conn = self._get_conn()
            with self._lock, conn:
                conn.execute("""
                    INSERT INTO runs (
                        run_id, user_id, workspace_id, requested_by, company_name,
                        ticker, cik, objective, status, created_at, updated_at, error_message, data_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                        status = excluded.status,
                        updated_at = excluded.updated_at,
                        error_message = excluded.error_message,
                        data_json = excluded.data_json;
                """, (
                    run.run_id,
                    run.user_id,
                    run.workspace_id,
                    run.requested_by,
                    run.company_name,
                    run.ticker,
                    run.cik,
                    run.objective,
                    run.status.value,
                    run.created_at.isoformat(),
                    run.updated_at.isoformat(),
                    run.error_message,
                    run.model_dump_json(),
                ))
        except Exception as e:
            logger.error("Failed to persist run %s to SQLite: %s", run.run_id, e)

    def get_run(self, run_id: str) -> ResearchRun | None:
        return self._runs.get(run_id)

    def list_runs(self, user_id: str | None = None, workspace_id: str | None = None) -> list[ResearchRun]:
        runs = list(self._runs.values())
        if workspace_id:
            runs = [r for r in runs if r.workspace_id == workspace_id]
        if user_id:
            runs = [r for r in runs if r.user_id == user_id]
        return sorted(runs, key=lambda r: r.created_at, reverse=True)

    # --- Itinerary Methods ---
    def save_itinerary(self, itinerary: ResearchItinerary) -> None:
        self._itineraries[itinerary.run_id] = itinerary
        try:
            conn = self._get_conn()
            with self._lock, conn:
                conn.execute("""
                    INSERT INTO itineraries (run_id, itinerary_id, data_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET data_json = excluded.data_json;
                """, (itinerary.run_id, itinerary.itinerary_id, itinerary.model_dump_json()))
        except Exception as e:
            logger.error("Failed to persist itinerary for run %s: %s", itinerary.run_id, e)

    def get_itinerary(self, run_id: str) -> ResearchItinerary | None:
        return self._itineraries.get(run_id)

    # --- Report Methods ---
    def save_report(self, report: FinalReport) -> None:
        self._reports[report.run_id] = report
        try:
            conn = self._get_conn()
            with self._lock, conn:
                conn.execute("""
                    INSERT INTO reports (run_id, report_id, data_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET data_json = excluded.data_json;
                """, (report.run_id, report.report_id, report.model_dump_json()))
        except Exception as e:
            logger.error("Failed to persist report for run %s: %s", report.run_id, e)

    def get_report(self, run_id: str) -> FinalReport | None:
        return self._reports.get(run_id)

    # --- Artifact Methods ---
    def save_artifact(self, artifact: ReportArtifact) -> None:
        self._artifacts[artifact.run_id] = artifact
        try:
            conn = self._get_conn()
            with self._lock, conn:
                conn.execute("""
                    INSERT INTO artifacts (run_id, artifact_id, data_json)
                    VALUES (?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET data_json = excluded.data_json;
                """, (artifact.run_id, artifact.artifact_id, artifact.model_dump_json()))
        except Exception as e:
            logger.error("Failed to persist artifact for run %s: %s", artifact.run_id, e)

    def get_artifact(self, run_id: str) -> ReportArtifact | None:
        return self._artifacts.get(run_id)

    # --- Approval Methods ---
    def add_approval(self, event: ApprovalEvent) -> None:
        if event.run_id not in self._approvals:
            self._approvals[event.run_id] = []
        self._approvals[event.run_id].append(event)
        try:
            conn = self._get_conn()
            with self._lock, conn:
                conn.execute("""
                    INSERT INTO approvals (run_id, user_id, event_data_json)
                    VALUES (?, ?, ?)
                """, (event.run_id, getattr(event, "user_id", "analyst"), event.model_dump_json()))
        except Exception as e:
            logger.error("Failed to persist approval event for run %s: %s", event.run_id, e)

    def list_approvals(self, run_id: str) -> list[ApprovalEvent]:
        return self._approvals.get(run_id, [])

    save_approval = add_approval

    # --- User & Workspace Methods (Multi-Tenancy) ---
    def get_user(self, user_id: str) -> dict[str, Any] | None:
        try:
            conn = self._get_conn()
            cur = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if row:
                return dict(row)
        except Exception as e:
            logger.error("Error looking up user %s: %s", user_id, e)
        return None

    def get_user_by_api_key(self, api_key: str) -> dict[str, Any] | None:
        try:
            conn = self._get_conn()
            cur = conn.execute("SELECT * FROM users WHERE api_key = ?", (api_key,))
            row = cur.fetchone()
            if row:
                return dict(row)
        except Exception as e:
            logger.error("Error looking up user by API key: %s", e)
        return None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        try:
            conn = self._get_conn()
            cur = conn.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cur.fetchone()
            if row:
                return dict(row)
        except Exception as e:
            logger.error("Error looking up user by email %s: %s", email, e)
        return None

    def create_user(
        self,
        user_id: str,
        email: str,
        name: str,
        role: str = "ANALYST",
        api_key: str | None = None,
        active_workspace_id: str = "ws_default",
    ) -> dict[str, Any]:
        api_key = api_key or f"apollo_ak_{user_id[:8]}"
        conn = self._get_conn()
        with self._lock, conn:
            conn.execute("""
                INSERT INTO users (user_id, email, name, role, api_key, active_workspace_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (user_id, email, name, role, api_key, active_workspace_id))
        return {
            "user_id": user_id,
            "email": email,
            "name": name,
            "role": role,
            "api_key": api_key,
            "active_workspace_id": active_workspace_id,
        }

    def list_workspaces_for_user(self, user_id: str) -> list[dict[str, Any]]:
        try:
            conn = self._get_conn()
            cur = conn.execute("SELECT * FROM workspaces WHERE owner_id = ? OR workspace_id = 'ws_default'", (user_id,))
            return [dict(row) for row in cur.fetchall()]
        except Exception as e:
            logger.error("Error listing workspaces for %s: %s", user_id, e)
            return [{"workspace_id": "ws_default", "name": "Default Workspace"}]

    def create_workspace(self, workspace_id: str, name: str, owner_id: str) -> dict[str, Any]:
        conn = self._get_conn()
        with self._lock, conn:
            conn.execute("""
                INSERT INTO workspaces (workspace_id, name, owner_id, created_at)
                VALUES (?, ?, ?, datetime('now'))
            """, (workspace_id, name, owner_id))
        return {"workspace_id": workspace_id, "name": name, "owner_id": owner_id}


# Global store instance
run_store = RunStore()

