"""Evidence and Source Registry Repository."""

import hashlib
import logging
from typing import Any
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.models.sources import SourceDocument

logger = logging.getLogger(__name__)


class EvidenceRegistry:
    """In-memory and durable repository for sources and evidence records."""

    def __init__(self) -> None:
        self._sources: dict[str, SourceDocument] = {}
        self._evidence: dict[str, EvidenceRecord] = {}
        self._question_to_evidence: dict[str, list[str]] = {}

    def add_source(self, source: SourceDocument) -> SourceDocument:
        """Adds a normalized source document record."""
        self._sources[source.source_id] = source
        logger.info("Registered source document: %s (%s)", source.source_id, source.title)
        return source

    def get_source(self, source_id: str) -> SourceDocument | None:
        return self._sources.get(source_id)

    def list_sources(self) -> list[SourceDocument]:
        return list(self._sources.values())

    def add_evidence(self, record: EvidenceRecord) -> EvidenceRecord:
        """Registers a normalized evidence record."""
        self._evidence[record.evidence_id] = record

        for qid in record.question_ids:
            if qid not in self._question_to_evidence:
                self._question_to_evidence[qid] = []
            if record.evidence_id not in self._question_to_evidence[qid]:
                self._question_to_evidence[qid].append(record.evidence_id)

        return record

    def add_evidence_batch(self, records: list[EvidenceRecord]) -> list[EvidenceRecord]:
        return [self.add_evidence(r) for r in records]

    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        return self._evidence.get(evidence_id)

    def list_evidence(self) -> list[EvidenceRecord]:
        return list(self._evidence.values())

    def get_evidence_for_question(self, question_id: str) -> list[EvidenceRecord]:
        evidence_ids = self._question_to_evidence.get(question_id, [])
        return [self._evidence[eid] for eid in evidence_ids if eid in self._evidence]

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
        self._sources.clear( )
        self._evidence.clear()
        self._question_to_evidence.clear()
