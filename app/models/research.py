"""Research Run and Itinerary models."""

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class RunStatus(str, Enum):
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    RESEARCHING = "RESEARCHING"
    SYNTHESIZING = "SYNTHESIZING"
    VALIDATING = "VALIDATING"
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    FAILED = "FAILED"


class QuestionStatus(str, Enum):
    UNANSWERED = "UNANSWERED"
    SUPPORTED = "SUPPORTED"
    GAP = "GAP"
    UNRESOLVED = "UNRESOLVED"


class ResearchQuestion(BaseModel):
    question_id: str
    section_id: str
    question: str
    expected_evidence: list[str] = Field(default_factory=list)
    required_source_types: list[str] = Field(default_factory=lambda: ["SEC_FILING"])
    evidence_ids: list[str] = Field(default_factory=list)
    status: QuestionStatus = QuestionStatus.UNANSWERED
    unresolved_reason: str | None = None


class SectionDefinition(BaseModel):
    section_id: str
    title: str
    description: str
    question_ids: list[str] = Field(default_factory=list)


class ResearchItinerary(BaseModel):
    itinerary_id: str
    run_id: str
    company_name: str
    ticker: str
    cik: str
    sections: list[SectionDefinition] = Field(default_factory=list)
    questions: list[ResearchQuestion] = Field(default_factory=list)


class ResearchRun(BaseModel):
    run_id: str
    requested_by: str = "analyst"
    user_id: str = "usr_primary_analyst"
    workspace_id: str = "ws_default"
    company_name: str
    ticker: str | None = None
    cik: str | None = None
    objective: str
    reporting_start: str | None = None
    reporting_end: str | None = None
    status: RunStatus = RunStatus.PLANNING
    followup_round: int = 0
    max_followup_rounds: int = 3
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str | None = None
