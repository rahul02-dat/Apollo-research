"""LangGraph Workflow State Definition."""

from typing import Annotated, Any, Sequence, TypedDict
from pydantic import BaseModel, Field
from app.models.approvals import ApprovalEvent
from app.models.gaps import CoverageAssessment
from app.models.reports import FinalReport, ReportArtifact, SectionDraft
from app.models.research import ResearchItinerary, ResearchRun


class ApolloWorkflowState(TypedDict, total=False):
    run: ResearchRun
    itinerary: ResearchItinerary | None
    plan_approved: bool
    coverage: CoverageAssessment | None
    section_drafts: list[SectionDraft]
    final_report: FinalReport | None
    report_artifact: ReportArtifact | None
    approval_events: list[ApprovalEvent]
    errors: list[str]
    current_step: str
