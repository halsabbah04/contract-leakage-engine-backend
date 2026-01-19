"""Analysis session data models."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class UserAction(str):
    """Types of user actions."""

    DISMISSED = "dismissed"
    ACCEPTED = "accepted"
    MODIFIED = "modified"
    NOTED = "noted"


class FindingOverride(BaseModel):
    """User override for a specific finding."""

    finding_id: str = Field(..., description="ID of the finding being overridden")
    action: str = Field(..., description="Action taken (dismissed, accepted, modified)")
    reason: Optional[str] = Field(None, description="User's reason for the action")
    modified_impact: Optional[float] = Field(None, description="User-adjusted impact value")
    modified_assumptions: Optional[Dict[str, Any]] = Field(None, description="User-adjusted assumptions")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When action was taken")


class AnalysisSession(BaseModel):
    """
    User interaction and analysis session data.

    Cosmos DB Container: analysis_sessions
    Partition Key: contract_id
    """

    id: str = Field(..., description="Unique session identifier")
    type: Literal["session"] = "session"
    contract_id: str = Field(..., description="Contract being analyzed (partition key)")

    # User information
    user_role: Optional[str] = Field(None, description="Role of user (contract_manager, finance, etc.)")
    user_id: Optional[str] = Field(None, description="User identifier (if auth is implemented)")

    # Session data
    overrides: List[FindingOverride] = Field(default_factory=list, description="User overrides and actions")

    # Custom parameters
    custom_inflation_rate: Optional[float] = Field(None, description="User-specified inflation rate")
    custom_assumptions: Dict[str, Any] = Field(default_factory=dict, description="Other custom assumptions")

    # Session metadata
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation time")
    last_activity_at: datetime = Field(default_factory=datetime.utcnow, description="Last user activity")
    session_duration_seconds: Optional[float] = Field(None, description="Total session duration")

    # Export history
    exports: List[Dict[str, Any]] = Field(default_factory=list, description="Export actions taken")

    partition_key: str = Field(..., description="Cosmos DB partition key (contract_id)")

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "session_001",
                "type": "session",
                "contract_id": "contract_001",
                "user_role": "contract_manager",
                "overrides": [
                    {
                        "finding_id": "finding_001",
                        "action": "dismissed",
                        "reason": "Covered by side letter",
                    }
                ],
                "partition_key": "contract_001",
            }
        }

    def model_post_init(self, __context) -> None:
        """Ensure partition_key matches contract_id."""
        if self.partition_key != self.contract_id:
            self.partition_key = self.contract_id

    def add_override(self, override: FindingOverride) -> None:
        """Add a user override to the session."""
        self.overrides.append(override)
        self.last_activity_at = datetime.utcnow()

    def add_export(self, export_format: str, export_uri: Optional[str] = None) -> None:
        """Record an export action."""
        self.exports.append(
            {
                "format": export_format,
                "uri": export_uri,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        self.last_activity_at = datetime.utcnow()
