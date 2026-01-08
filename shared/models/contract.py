"""Contract data models."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum


class ContractSource(str, Enum):
    """Source of contract data."""
    UPLOAD = "upload"
    MANUAL = "manual"


class ContractStatus(str, Enum):
    """Processing status of contract."""
    UPLOADED = "uploaded"
    EXTRACTING_TEXT = "extracting_text"
    TEXT_EXTRACTED = "text_extracted"
    EXTRACTING_CLAUSES = "extracting_clauses"
    CLAUSES_EXTRACTED = "clauses_extracted"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class Contract(BaseModel):
    """
    Contract metadata and processing status.

    Cosmos DB Container: contracts
    Partition Key: contract_id
    """
    id: str = Field(..., description="Unique contract identifier (same as contract_id for Cosmos)")
    type: Literal["contract"] = "contract"
    contract_id: str = Field(..., description="Contract ID (partition key)")
    contract_name: str = Field(..., description="Name or title of the contract")
    source: ContractSource = Field(..., description="How contract data was provided")
    file_type: Optional[str] = Field(None, description="Original file type (pdf, docx, etc.)")
    language: str = Field(default="en", description="Contract language")
    counterparty: Optional[str] = Field(None, description="Other party to the contract")
    start_date: Optional[str] = Field(None, description="Contract start date (ISO format)")
    end_date: Optional[str] = Field(None, description="Contract end date (ISO format)")
    contract_value_estimate: Optional[float] = Field(None, description="Estimated contract value in USD")
    status: ContractStatus = Field(..., description="Current processing status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    partition_key: str = Field(..., description="Cosmos DB partition key (same as contract_id)")

    # Storage references
    blob_uri: Optional[str] = Field(None, description="Azure Blob Storage URI for original file")
    extracted_text_uri: Optional[str] = Field(None, description="URI for extracted text")

    # Processing metadata
    error_message: Optional[str] = Field(None, description="Error message if processing failed")
    processing_duration_seconds: Optional[float] = Field(None, description="Total processing time")

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "id": "contract_001",
                "type": "contract",
                "contract_id": "contract_001",
                "contract_name": "Master Services Agreement",
                "source": "upload",
                "file_type": "pdf",
                "language": "en",
                "counterparty": "Acme Corp",
                "start_date": "2022-01-01",
                "end_date": "2025-12-31",
                "contract_value_estimate": 1200000.0,
                "status": "analyzed",
                "partition_key": "contract_001"
            }
        }

    def model_post_init(self, __context) -> None:
        """Ensure partition_key matches contract_id."""
        if self.partition_key != self.contract_id:
            self.partition_key = self.contract_id
        if self.id != self.contract_id:
            self.id = self.contract_id
