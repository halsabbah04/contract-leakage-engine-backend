"""Obligation data models for contract obligations tracking."""

from datetime import datetime, date
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ObligationType(str, Enum):
    """Types of contractual obligations."""

    PAYMENT = "payment"
    DELIVERY = "delivery"
    NOTICE = "notice"
    REPORTING = "reporting"
    COMPLIANCE = "compliance"
    PERFORMANCE = "performance"
    RENEWAL = "renewal"
    TERMINATION = "termination"
    INSURANCE = "insurance"
    AUDIT = "audit"
    CONFIDENTIALITY = "confidentiality"
    OTHER = "other"


class ObligationStatus(str, Enum):
    """Status of an obligation."""

    UPCOMING = "upcoming"  # Not yet due
    DUE_SOON = "due_soon"  # Due within 30 days
    OVERDUE = "overdue"  # Past due date
    COMPLETED = "completed"  # Fulfilled
    WAIVED = "waived"  # Waived by counterparty
    NOT_APPLICABLE = "not_applicable"  # No longer applies


class ObligationPriority(str, Enum):
    """Priority level of an obligation."""

    CRITICAL = "critical"  # Must not be missed
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecurrencePattern(str, Enum):
    """Recurrence pattern for recurring obligations."""

    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMI_ANNUALLY = "semi_annually"
    ANNUALLY = "annually"
    CUSTOM = "custom"


class ResponsibleParty(BaseModel):
    """Party responsible for fulfilling an obligation."""

    party_name: str = Field(..., description="Name of the responsible party")
    party_role: str = Field(..., description="Role (e.g., 'service_provider', 'client')")
    is_our_organization: bool = Field(default=False, description="Whether this is our organization")


class Obligation(BaseModel):
    """
    A contractual obligation extracted from a contract.

    Cosmos DB Container: obligations
    Partition Key: contract_id
    """

    id: str = Field(..., description="Unique obligation identifier")
    type: Literal["obligation"] = "obligation"
    contract_id: str = Field(..., description="Parent contract ID (partition key)")

    # Classification
    obligation_type: ObligationType = Field(..., description="Type of obligation")
    title: str = Field(..., description="Short title/summary of the obligation")
    description: str = Field(..., description="Full description of the obligation")

    # Timing
    due_date: Optional[date] = Field(None, description="Due date for the obligation")
    effective_date: Optional[date] = Field(None, description="When the obligation becomes effective")
    end_date: Optional[date] = Field(None, description="When the obligation expires")

    # Recurrence
    is_recurring: bool = Field(default=False, description="Whether this obligation recurs")
    recurrence_pattern: RecurrencePattern = Field(
        default=RecurrencePattern.NONE, description="Recurrence pattern"
    )
    recurrence_end_date: Optional[date] = Field(None, description="When recurrence ends")
    next_occurrence: Optional[date] = Field(None, description="Next occurrence date for recurring")

    # Responsibility
    responsible_party: ResponsibleParty = Field(..., description="Party responsible for this obligation")

    # Financial (if applicable)
    amount: Optional[float] = Field(None, description="Monetary amount if applicable")
    currency: str = Field(default="USD", description="Currency code")

    # Status and priority
    status: ObligationStatus = Field(default=ObligationStatus.UPCOMING, description="Current status")
    priority: ObligationPriority = Field(default=ObligationPriority.MEDIUM, description="Priority level")

    # Source
    clause_ids: List[str] = Field(default_factory=list, description="Source clause IDs")
    extracted_text: Optional[str] = Field(None, description="Original text from which this was extracted")

    # Tracking
    reminder_days_before: int = Field(default=30, description="Days before due date to send reminder")
    notes: Optional[str] = Field(None, description="Additional notes")

    # AI confidence
    extraction_confidence: float = Field(default=0.0, description="Confidence in extraction (0-1)")

    # Metadata
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    partition_key: str = Field(..., description="Cosmos DB partition key (contract_id)")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        json_schema_extra = {
            "example": {
                "id": "obligation_001",
                "type": "obligation",
                "contract_id": "contract_001",
                "obligation_type": "payment",
                "title": "Quarterly Service Fee Payment",
                "description": "Payment of BHD 37,500 due quarterly on the first day of each quarter",
                "due_date": "2026-04-01",
                "is_recurring": True,
                "recurrence_pattern": "quarterly",
                "responsible_party": {
                    "party_name": "Al Hawaj Trading",
                    "party_role": "client",
                    "is_our_organization": False,
                },
                "amount": 37500,
                "currency": "BHD",
                "status": "upcoming",
                "priority": "high",
                "clause_ids": ["clause_015"],
                "extraction_confidence": 0.95,
                "partition_key": "contract_001",
            }
        }

    def model_post_init(self, __context) -> None:
        """Ensure partition_key matches contract_id and calculate status."""
        if self.partition_key != self.contract_id:
            self.partition_key = self.contract_id

        # Auto-calculate status based on due date
        if self.due_date and self.status not in [ObligationStatus.COMPLETED, ObligationStatus.WAIVED]:
            today = date.today()
            days_until_due = (self.due_date - today).days

            if days_until_due < 0:
                self.status = ObligationStatus.OVERDUE
            elif days_until_due <= 30:
                self.status = ObligationStatus.DUE_SOON
            else:
                self.status = ObligationStatus.UPCOMING


class ObligationSummary(BaseModel):
    """Summary of obligations for a contract."""

    contract_id: str = Field(..., description="Contract ID")
    total_obligations: int = Field(default=0, description="Total number of obligations")
    by_type: dict = Field(default_factory=dict, description="Count by obligation type")
    by_status: dict = Field(default_factory=dict, description="Count by status")
    by_responsible_party: dict = Field(default_factory=dict, description="Count by responsible party")

    # Key dates
    upcoming_count: int = Field(default=0, description="Number of upcoming obligations")
    due_soon_count: int = Field(default=0, description="Number due within 30 days")
    overdue_count: int = Field(default=0, description="Number of overdue obligations")

    # Financial summary
    total_payment_obligations: float = Field(default=0.0, description="Total payment obligations")
    our_payment_obligations: float = Field(default=0.0, description="Our payment obligations")
    their_payment_obligations: float = Field(default=0.0, description="Counterparty payment obligations")
    currency: str = Field(default="USD", description="Primary currency for payment obligations")

    # Party names for display
    our_organization_name: Optional[str] = Field(None, description="Name of our organization")
    counterparty_name: Optional[str] = Field(None, description="Name of the counterparty")

    # Next action items
    next_due_date: Optional[date] = Field(None, description="Next upcoming due date")
    next_obligation_title: Optional[str] = Field(None, description="Title of next obligation")

    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Summary generation timestamp")


class ObligationExtractionResult(BaseModel):
    """Result of obligation extraction for a contract."""

    contract_id: str = Field(..., description="Contract ID")
    obligations: List[Obligation] = Field(default_factory=list, description="Extracted obligations")
    summary: ObligationSummary = Field(..., description="Summary of extracted obligations")
    extraction_metadata: dict = Field(default_factory=dict, description="Extraction metadata")
