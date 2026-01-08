"""Clause data models."""

from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field


class ClauseType(str):
    """Common clause types found in contracts."""
    PRICING = "pricing"
    PAYMENT = "payment"
    TERMINATION = "termination"
    RENEWAL = "renewal"
    AUTO_RENEWAL = "auto_renewal"
    SERVICE_LEVEL = "service_level"
    LIABILITY = "liability"
    INDEMNIFICATION = "indemnification"
    CONFIDENTIALITY = "confidentiality"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    DISPUTE_RESOLUTION = "dispute_resolution"
    FORCE_MAJEURE = "force_majeure"
    WARRANTY = "warranty"
    DELIVERY = "delivery"
    PENALTIES = "penalties"
    DISCOUNTS = "discounts"
    VOLUME_COMMITMENT = "volume_commitment"
    EXCLUSIVITY = "exclusivity"
    OTHER = "other"


class ExtractedEntities(BaseModel):
    """Entities extracted from clause text."""
    currency: Optional[str] = Field(None, description="Currency mentioned (USD, EUR, etc.)")
    rates: List[float] = Field(default_factory=list, description="Numerical rates or prices")
    dates: List[str] = Field(default_factory=list, description="Dates mentioned (ISO format)")
    percentages: List[float] = Field(default_factory=list, description="Percentage values")
    amounts: List[float] = Field(default_factory=list, description="Monetary amounts")
    parties: List[str] = Field(default_factory=list, description="Parties mentioned")
    durations: List[str] = Field(default_factory=list, description="Time durations mentioned")


class Clause(BaseModel):
    """
    Semantic clause unit extracted from contract.

    Cosmos DB Container: clauses
    Partition Key: contract_id

    This is the PRIMARY RAG SURFACE for AI reasoning.
    """
    id: str = Field(..., description="Unique clause identifier")
    type: Literal["clause"] = "clause"
    contract_id: str = Field(..., description="Parent contract ID (partition key)")
    clause_type: str = Field(..., description="Classified clause type")
    clause_subtype: Optional[str] = Field(None, description="More specific classification")

    # Text content
    original_text: str = Field(..., description="Original clause text from contract")
    normalized_summary: str = Field(..., description="Clean, concise summary for AI prompts")

    # Location in original document
    page_number: Optional[int] = Field(None, description="Page number in original document")
    section_number: Optional[str] = Field(None, description="Section number (e.g., '3.2.1')")
    start_position: Optional[int] = Field(None, description="Character start position in full text")
    end_position: Optional[int] = Field(None, description="Character end position in full text")

    # Extracted structured data
    entities: ExtractedEntities = Field(default_factory=ExtractedEntities, description="Extracted entities")

    # Risk signals for rule-based detection
    risk_signals: List[str] = Field(default_factory=list, description="Identified risk patterns")

    # Vector embedding for RAG
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")

    # Metadata
    extraction_confidence: Optional[float] = Field(None, description="Confidence score for extraction (0-1)")
    extracted_at: datetime = Field(default_factory=datetime.utcnow, description="Extraction timestamp")
    partition_key: str = Field(..., description="Cosmos DB partition key (contract_id)")

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "id": "clause_001",
                "type": "clause",
                "contract_id": "contract_001",
                "clause_type": "pricing",
                "clause_subtype": "price_adjustment",
                "original_text": "Prices shall remain fixed for the duration of the agreement...",
                "normalized_summary": "Pricing is fixed with no escalation mechanism.",
                "entities": {
                    "currency": "USD",
                    "rates": [],
                    "dates": []
                },
                "risk_signals": ["no_price_escalation"],
                "partition_key": "contract_001"
            }
        }

    def model_post_init(self, __context) -> None:
        """Ensure partition_key matches contract_id."""
        if self.partition_key != self.contract_id:
            self.partition_key = self.contract_id
