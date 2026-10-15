"""Approval models and checkpoints."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class ApprovalCheckpoint(str, Enum):
    PLAN_APPROVAL = "PLAN_APPROVAL"
    SCOPE_EXPANSION = "SCOPE_EXPANSION"
    FINAL_REVIEW = "FINAL_REVIEW"


class ApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EDITED = "EDITED"


class ApprovalEvent(BaseModel):
    event_id: str
    run_id: str
    user_id: str | None = None
    workspace_id: str | None = None
    checkpoint: ApprovalCheckpoint
    decision: ApprovalDecision
    approver: str = "analyst"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    feedback: str | None = None
    context_data: dict[str, Any] = Field(default_factory=dict)

