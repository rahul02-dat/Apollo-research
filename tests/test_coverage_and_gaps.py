"""Acceptance Tests AT-03, AT-04, AT-05: Question Coverage, Gap Recovery, and Bounded Autonomy."""

from typing import Any
import pytest
from app.agents.athena import AthenaResearchAgent
from app.agents.hermes import HermesAnalysisAgent
from app.models.research import QuestionStatus, ResearchQuestion
from app.plugins.registry import PluginRegistry
from app.services.evidence_registry import EvidenceRegistry


def test_at03_question_coverage(
    plugin_registry: PluginRegistry,
    evidence_registry: EvidenceRegistry,
    fake_source: Any,
) -> None:
    """AT-03: Every research question marked supported has at least one valid evidence record."""
    plugin_registry.register(fake_source, overwrite=True)
    athena = AthenaResearchAgent(plugin_registry, evidence_registry)
    hermes = HermesAnalysisAgent(evidence_registry)

    questions = [
        ResearchQuestion(
            question_id="Q_REV",
            section_id="SEC_PERF",
            question="What was total revenue?",
            expected_evidence=["Revenues"],
        )
    ]

    athena.retrieve_initial_evidence(
        cik="0000789019",
        questions=questions,
        source_plugin_id="fake_source",
    )

    assessment, evaluated_questions = hermes.evaluate_coverage(
        run_id="RUN_AT03",
        questions=questions,
        current_round=0,
        max_rounds=3,
    )

    assert assessment.supported_count == 1
    assert assessment.gap_count == 0
    assert evaluated_questions[0].status == QuestionStatus.SUPPORTED
    assert len(evaluated_questions[0].evidence_ids) >= 1

    # Verify every evidence_id resolves in registry
    for eid in evaluated_questions[0].evidence_ids:
        rec = evidence_registry.get_evidence(eid)
        assert rec is not None
        assert rec.validation_status == "VALID"


def test_at04_gap_recovery(
    plugin_registry: PluginRegistry,
    evidence_registry: EvidenceRegistry,
    fake_source: Any,
) -> None:
    """AT-04: Seeded missing evidence causes a targeted follow-up and subsequent reevaluation."""
    plugin_registry.register(fake_source, overwrite=True)
    athena = AthenaResearchAgent(plugin_registry, evidence_registry)
    hermes = HermesAnalysisAgent(evidence_registry)

    # Question Q_SEG is deliberately seeded with NO initial evidence linked to it
    question_supported = ResearchQuestion(
        question_id="Q_REV",
        section_id="SEC_PERF",
        question="What was total revenue?",
    )
    question_gap = ResearchQuestion(
        question_id="Q_SEG",
        section_id="SEC_SEG",
        question="What are segment revenues?",
    )

    questions = [question_supported, question_gap]

    # Initial retrieval: only link Q_REV, leaving Q_SEG unlinked
    athena.retrieve_initial_evidence(
        cik="0000789019",
        questions=[question_supported],
        source_plugin_id="fake_source",
    )

    # Hermes first evaluation: must detect Q_SEG as a GAP
    assessment_1, eval_q1 = hermes.evaluate_coverage(
        run_id="RUN_AT04",
        questions=questions,
        current_round=0,
        max_rounds=3,
    )

    assert assessment_1.gap_count == 1
    gap_item = hermes.identify_next_followup(assessment_1)
    assert gap_item is not None
    assert gap_item.question_id == "Q_SEG"
    assert "segment" in gap_item.reason.lower()

    # Athena targeted follow-up specifically targeting Q_SEG
    followup_records = athena.retrieve_followup_evidence(
        cik="0000789019",
        follow_up=gap_item.follow_up,
        target_question_id="Q_SEG",
        source_plugin_id="fake_source",
    )
    assert len(followup_records) > 0

    # Hermes second evaluation: Q_SEG must now be SUPPORTED
    assessment_2, eval_q2 = hermes.evaluate_coverage(
        run_id="RUN_AT04",
        questions=eval_q1,
        current_round=1,
        max_rounds=3,
    )

    assert assessment_2.gap_count == 0
    assert assessment_2.is_fully_supported is True
    q_seg_eval = next(q for q in eval_q2 if q.question_id == "Q_SEG")
    assert q_seg_eval.status == QuestionStatus.SUPPORTED
    assert len(q_seg_eval.evidence_ids) >= 1


def test_at05_bounded_autonomy(
    evidence_registry: EvidenceRegistry,
) -> None:
    """AT-05: Autonomous follow-up stops at max rounds and marks missing questions UNRESOLVED."""
    hermes = HermesAnalysisAgent(evidence_registry)

    # An impossible question that cannot be answered
    question_impossible = ResearchQuestion(
        question_id="Q_IMPOSSIBLE",
        section_id="SEC_UNKNOWN",
        question="What are the unannounced future product release dates?",
    )

    # Round 0 of 3: Should be GAP
    assessment_0, eval_0 = hermes.evaluate_coverage(
        run_id="RUN_AT05",
        questions=[question_impossible],
        current_round=0,
        max_rounds=3,
    )
    assert eval_0[0].status == QuestionStatus.GAP

    # Round 1 of 3: Should still be GAP
    assessment_1, eval_1 = hermes.evaluate_coverage(
        run_id="RUN_AT05",
        questions=[question_impossible],
        current_round=1,
        max_rounds=3,
    )
    assert eval_1[0].status == QuestionStatus.GAP

    # Round 3 of 3 (Budget reached): Must be marked UNRESOLVED
    assessment_3, eval_3 = hermes.evaluate_coverage(
        run_id="RUN_AT05",
        questions=[question_impossible],
        current_round=3,
        max_rounds=3,
    )
    assert assessment_3.unresolved_count == 1
    assert assessment_3.gap_count == 0
    assert eval_3[0].status == QuestionStatus.UNRESOLVED
    assert "limit reached" in eval_3[0].unresolved_reason.lower()
