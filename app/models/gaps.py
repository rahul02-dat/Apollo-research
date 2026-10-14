"""Gap detection and follow-up models."""

from typing import Any
from pydantic import BaseModel, Field
from app.models.research import QuestionStatus


class FollowUpRequest(BaseModel):
    filing_types: list[str] = Field(default_factory=lambda: ["10-K", "10-Q"])
    target_sections: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)
    terms: list[str] = Field(default_factory=list)


class GapRequest(BaseModel):
    question_id: str
    status: QuestionStatus = QuestionStatus.GAP
    reason: str
    follow_up: FollowUpRequest
    attempt_round: int = 1


class CoverageAssessment(BaseModel):
    run_id: str
    evaluated_at: str
    total_questions: int
    supported_count: int
    gap_count: int
    unanswered_count: int
    unresolved_count: int
    gaps: list[GapRequest] = Field(default_factory=list)
    is_fully_supported: bool = False
