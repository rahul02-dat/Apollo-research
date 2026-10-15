"""Evidence and Source Registry Repository with Run Scoping and Durable Persistence."""

import hashlib
import logging
from typing import Any
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.models.sources import SourceDocument
from app.persistence.database import run_store

logger = logging.getLogger(__name__)


class EvidenceRegistry:
    """In-memory and durable repository for sources and evidence records."""

    def __init__(self, run_id: str | None = None, store: Any = None) -> None:
        self.run_id = run_id
        self.store = store if store is not None else run_store
        self._sources: dict[str, SourceDocument] = {}
        self._evidence: dict[str, EvidenceRecord] = {}
        self._question_to_evidence: dict[str, list[str]] = {}
        self._run_to_sources: dict[str, list[str]] = {}
        self._run_to_evidence: dict[str, list[str]] = {}

        # Hydrate from durable store if run_id is supplied
        if self.store and self.run_id:
            try:
                for s in self.store.list_sources_for_run(self.run_id):
                    self.add_source(s, run_id=self.run_id)
                for e in self.store.list_evidence_for_run(self.run_id):
                    self.add_evidence(e, run_id=self.run_id)
            except Exception as ex:
                logger.warning("Error pre-populating evidence registry for run %s: %s", self.run_id, ex)

    def add_source(self, source: SourceDocument, run_id: str | None = None) -> SourceDocument:
        """Adds a normalized source document record, updating durable store."""
        target_run_id = run_id or source.run_id or self.run_id
        if target_run_id and not source.run_id:
            source.run_id = target_run_id

        self._sources[source.source_id] = source
        if target_run_id:
            if target_run_id not in self._run_to_sources:
                self._run_to_sources[target_run_id] = []
            if source.source_id not in self._run_to_sources[target_run_id]:
                self._run_to_sources[target_run_id].append(source.source_id)

        if self.store and target_run_id:
            try:
                self.store.save_source(source, run_id=target_run_id, workspace_id=source.workspace_id)
            except Exception as e:
                logger.error("Failed to save source to store: %s", e)

        logger.info("Registered source document: %s (%s) for run: %s", source.source_id, source.title, target_run_id)
        return source

    def get_source(self, source_id: str) -> SourceDocument | None:
        if source_id in self._sources:
            return self._sources[source_id]
        if self.store:
            return self.store.get_source(source_id)
        return None

    def list_sources(self) -> list[SourceDocument]:
        return list(self._sources.values())

    def list_sources_for_run(self, run_id: str | None = None) -> list[SourceDocument]:
        target_run_id = run_id or self.run_id
        if not target_run_id:
            return self.list_sources()

        source_ids = self._run_to_sources.get(target_run_id, [])
        if source_ids:
            return [self._sources[sid] for sid in source_ids if sid in self._sources]

        # Check in memory by matching run_id attribute
        in_mem = [s for s in self._sources.values() if s.run_id == target_run_id]
        if in_mem:
            return in_mem

        # Check durable store
        if self.store:
            persisted = self.store.list_sources_for_run(target_run_id)
            for s in persisted:
                self._sources[s.source_id] = s
            return persisted

        return []

    def add_evidence(self, record: EvidenceRecord, run_id: str | None = None) -> EvidenceRecord:
        """Registers a normalized evidence record, updating durable store."""
        target_run_id = run_id or record.run_id or self.run_id
        if target_run_id and not record.run_id:
            record.run_id = target_run_id

        self._evidence[record.evidence_id] = record

        if target_run_id:
            if target_run_id not in self._run_to_evidence:
                self._run_to_evidence[target_run_id] = []
            if record.evidence_id not in self._run_to_evidence[target_run_id]:
                self._run_to_evidence[target_run_id].append(record.evidence_id)

        for qid in record.question_ids:
            if qid not in self._question_to_evidence:
                self._question_to_evidence[qid] = []
            if record.evidence_id not in self._question_to_evidence[qid]:
                self._question_to_evidence[qid].append(record.evidence_id)

        if self.store and target_run_id:
            try:
                self.store.save_evidence(record, run_id=target_run_id, workspace_id=record.workspace_id)
            except Exception as e:
                logger.error("Failed to save evidence to store: %s", e)

        return record

    def add_evidence_batch(self, records: list[EvidenceRecord], run_id: str | None = None) -> list[EvidenceRecord]:
        return [self.add_evidence(r, run_id=run_id) for r in records]

    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        if evidence_id in self._evidence:
            return self._evidence[evidence_id]
        if self.store:
            return self.store.get_evidence(evidence_id)
        return None

    def list_evidence(self) -> list[EvidenceRecord]:
        return list(self._evidence.values())

    def list_for_run(self, run_id: str | None = None) -> list[EvidenceRecord]:
        target_run_id = run_id or self.run_id
        if not target_run_id:
            return self.list_evidence()

        evidence_ids = self._run_to_evidence.get(target_run_id, [])
        if evidence_ids:
            return [self._evidence[eid] for eid in evidence_ids if eid in self._evidence]

        # Check in memory by matching run_id attribute
        in_mem = [e for e in self._evidence.values() if e.run_id == target_run_id]
        if in_mem:
            return in_mem

        # Check durable store
        if self.store:
            persisted = self.store.list_evidence_for_run(target_run_id)
            for e in persisted:
                self._evidence[e.evidence_id] = e
            return persisted

        return []

    def get_evidence_for_question(self, question_id: str, run_id: str | None = None) -> list[EvidenceRecord]:
        target_run_id = run_id or self.run_id
        evidence_ids = self._question_to_evidence.get(question_id, [])
        records = [self._evidence[eid] for eid in evidence_ids if eid in self._evidence]
        if target_run_id:
            records = [r for r in records if r.run_id == target_run_id or r.run_id is None]
        return records

    def link_evidence_to_question(self, evidence_id: str, question_id: str) -> None:
        if evidence_id in self._evidence:
            record = self._evidence[evidence_id]
            if question_id not in record.question_ids:
                record.question_ids.append(question_id)
            if question_id not in self._question_to_evidence:
                self._question_to_evidence[question_id] = []
            if evidence_id not in self._question_to_evidence[question_id]:
                self._question_to_evidence[question_id].append(evidence_id)

    def clear(self) -> None:
        self._sources.clear()
        self._evidence.clear()
        self._question_to_evidence.clear()
        self._run_to_sources.clear()
        self._run_to_evidence.clear()

