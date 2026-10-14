"""Shared domain models for Apollo."""

from app.models.research import (
    ResearchRun,
    ResearchQuestion,
    ResearchItinerary,
    SectionDefinition,
    RunStatus,
    QuestionStatus,
)
from app.models.sources import SourceDocument, SourceQuery, SourceDocumentRef
from app.models.evidence import EvidenceRecord, EvidenceValidationStatus
from app.models.gaps import GapRequest, FollowUpRequest, CoverageAssessment
from app.models.claims import Claim, ClaimType, ClaimValidationResult
from app.models.reports import SectionDraft, FinalReport, ReportArtifact, BibliographyItem
from app.models.approvals import ApprovalEvent, ApprovalCheckpoint, ApprovalDecision

__all__ = [
    "ResearchRun",
    "ResearchQuestion",
    "ResearchItinerary",
    "SectionDefinition",
    "RunStatus",
    "QuestionStatus",
    "SourceDocument",
    "SourceQuery",
    "SourceDocumentRef",
    "EvidenceRecord",
    "EvidenceValidationStatus",
    "GapRequest",
    "FollowUpRequest",
    "CoverageAssessment",
    "Claim",
    "ClaimType",
    "ClaimValidationResult",
    "SectionDraft",
    "FinalReport",
    "ReportArtifact",
    "BibliographyItem",
    "ApprovalEvent",
    "ApprovalCheckpoint",
    "ApprovalDecision",
]
