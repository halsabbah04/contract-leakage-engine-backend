"""Leakage finding data models."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum


class LeakageCategory(str, Enum):
    """Categories of commercial leakage."""
    PRICING = "pricing"
    RENEWAL = "renewal"
    TERMINATION = "termination"
    SERVICE_CREDIT = "service_credit"
    VOLUME_DISCOUNT = "volume_discount"
    PENALTY = "penalty"
    AUTO_RENEWAL = "auto_renewal"
    LIABILITY_CAP = "liability_cap"
    PAYMENT_TERMS = "payment_terms"
    DELIVERY = "delivery"
    COMPLIANCE = "compliance"
    OTHER = "other"


class Severity(str, Enum):
    """Severity level of finding."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DetectionMethod(str, Enum):
    """How the finding was detected."""
    RULE = "rule"
    AI = "ai"
    HYBRID = "hybrid"


class EstimatedImpact(BaseModel):
    """Financial impact estimation."""
    currency: str = Field(default="USD", description="Currency code")
    value: Optional[float] = Field(None, description="Estimated monetary impact")
    value_min: Optional[float] = Field(None, description="Minimum estimated impact")
    value_max: Optional[float] = Field(None, description="Maximum estimated impact")
    confidence: Optional[float] = Field(None, description="Confidence in estimate (0-1)")
    calculation_method: Optional[str] = Field(None, description="How impact was calculated")


class Assumptions(BaseModel):
    """Assumptions used in impact calculation."""
    inflation_rate: Optional[float] = Field(None, description="Assumed inflation rate")
    remaining_years: Optional[float] = Field(None, description="Years remaining in contract")
    annual_volume: Optional[float] = Field(None, description="Assumed annual volume")
    probability: Optional[float] = Field(None, description="Probability of occurrence (0-1)")
    custom_parameters: Dict[str, Any] = Field(default_factory=dict, description="Custom calculation parameters")


class LeakageFinding(BaseModel):
    """
    Detected commercial leakage risk.

    Cosmos DB Container: leakage_findings
    Partition Key: contract_id
    """
    id: str = Field(..., description="Unique finding identifier")
    type: Literal["finding"] = "finding"
    contract_id: str = Field(..., description="Parent contract ID (partition key)")
    clause_ids: List[str] = Field(..., description="Related clause IDs")

    # Classification
    leakage_category: LeakageCategory = Field(..., description="Category of leakage")
    risk_type: str = Field(..., description="Specific risk type (e.g., 'missing_escalation')")

    # Detection metadata
    detection_method: DetectionMethod = Field(..., description="How finding was detected")
    rule_id: Optional[str] = Field(None, description="Rule ID if rule-based detection")

    # Severity and confidence
    severity: Severity = Field(..., description="Severity level")
    confidence: float = Field(..., description="Confidence score (0-1)")

    # Explanation
    explanation: str = Field(..., description="Plain-language explanation of the issue")
    business_impact_summary: Optional[str] = Field(None, description="Summary of business impact")
    recommended_action: Optional[str] = Field(None, description="Suggested remediation action")

    # Financial impact
    assumptions: Assumptions = Field(default_factory=Assumptions, description="Assumptions used")
    estimated_impact: EstimatedImpact = Field(default_factory=EstimatedImpact, description="Financial impact")

    # Vector embedding for finding similarity search
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")

    # User interaction
    user_dismissed: bool = Field(default=False, description="Whether user dismissed this finding")
    user_notes: Optional[str] = Field(None, description="User's notes or comments")

    # Metadata
    detected_at: datetime = Field(default_factory=datetime.utcnow, description="Detection timestamp")
    partition_key: str = Field(..., description="Cosmos DB partition key (contract_id)")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "id": "finding_001",
                "type": "finding",
                "contract_id": "contract_001",
                "clause_ids": ["clause_001"],
                "leakage_category": "pricing",
                "risk_type": "missing_escalation",
                "detection_method": "rule",
                "severity": "high",
                "confidence": 0.95,
                "explanation": "The contract fixes pricing for a multi-year term without escalation, which may lead to revenue erosion due to inflation.",
                "assumptions": {
                    "inflation_rate": 0.03,
                    "remaining_years": 2
                },
                "estimated_impact": {
                    "currency": "USD",
                    "value": 72000
                },
                "partition_key": "contract_001"
            }
        }

    def model_post_init(self, __context) -> None:
        """Ensure partition_key matches contract_id."""
        if self.partition_key != self.contract_id:
            self.partition_key = self.contract_id
