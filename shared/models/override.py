"""User Override Models

This module defines Pydantic models for user overrides on findings,
allowing users to accept, reject, adjust severity, and add notes.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel, Field


class FindingStatus(str, Enum):
    """Status of a finding after user review"""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    FALSE_POSITIVE = "false_positive"
    RESOLVED = "resolved"


class OverrideAction(str, Enum):
    """Types of override actions a user can perform"""

    CHANGE_SEVERITY = "change_severity"
    MARK_FALSE_POSITIVE = "mark_false_positive"
    ADD_NOTE = "add_note"
    ACCEPT = "accept"
    REJECT = "reject"
    RESOLVE = "resolve"


class UserOverride(BaseModel):
    """User override record for a finding

    Tracks user decisions and adjustments to AI findings with full audit trail.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    finding_id: str = Field(..., description="ID of the finding being overridden")
    contract_id: str = Field(..., description="Partition key - contract ID")
    action: OverrideAction = Field(..., description="Type of override action")
    user_email: str = Field(..., description="Email of user making the override")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the override was created")
    previous_value: Optional[str] = Field(None, description="Previous value (for severity changes)")
    new_value: Optional[str] = Field(None, description="New value (for severity changes)")
    notes: Optional[str] = Field(None, description="User notes or comments")
    reason: Optional[str] = Field(None, description="Reason for the override")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "override-abc-123",
                "finding_id": "finding-xyz-789",
                "contract_id": "contract-123",
                "action": "change_severity",
                "user_email": "john.doe@company.com",
                "timestamp": "2026-01-18T10:30:00Z",
                "previous_value": "CRITICAL",
                "new_value": "HIGH",
                "reason": "Reviewed with legal team, impact reassessed",
            }
        }


class OverrideSummary(BaseModel):
    """Summary of all overrides for a contract"""

    contract_id: str = Field(..., description="Contract ID")
    total_overrides: int = Field(..., description="Total number of overrides")
    by_action: Dict[str, int] = Field(..., description="Count of overrides by action type")
    accepted_count: int = Field(..., description="Number of accepted findings")
    rejected_count: int = Field(..., description="Number of rejected findings")
    false_positive_count: int = Field(..., description="Number of false positive findings")
    severity_changes: int = Field(..., description="Number of severity changes")

    class Config:
        json_schema_extra = {
            "example": {
                "contract_id": "contract-123",
                "total_overrides": 15,
                "by_action": {
                    "accept": 5,
                    "reject": 2,
                    "mark_false_positive": 3,
                    "change_severity": 4,
                    "add_note": 1,
                },
                "accepted_count": 5,
                "rejected_count": 2,
                "false_positive_count": 3,
                "severity_changes": 4,
            }
        }
