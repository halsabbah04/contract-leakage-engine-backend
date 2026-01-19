"""Clause extraction service - orchestrates text segmentation and NLP analysis."""

from typing import Dict, List, Optional

from ..db import ClauseRepository, ContractRepository, get_cosmos_client
from ..models.clause import Clause
from ..models.contract import ContractStatus
from ..utils.exceptions import ClauseExtractionError
from ..utils.logging import setup_logging
from .nlp_service import NLPService
from .text_preprocessing_service import TextPreprocessingService, TextSegment

logger = setup_logging(__name__)


class ClauseExtractionService:
    """Service for extracting and storing contract clauses."""

    def __init__(self):
        """Initialize clause extraction service."""
        self.text_preprocessor = TextPreprocessingService()
        self.nlp_service = NLPService()
        logger.info("Clause extraction service initialized")

    def extract_clauses_from_contract(self, contract_id: str, contract_text: str) -> List[Clause]:
        """
        Extract clauses from contract text.

        Complete workflow:
        1. Preprocess text
        2. Segment into clauses
        3. Analyze each clause with NLP
        4. Create Clause objects
        5. Store in Cosmos DB

        Args:
            contract_id: Contract identifier
            contract_text: Full contract text

        Returns:
            List of extracted Clause objects

        Raises:
            ClauseExtractionError: If extraction fails
        """
        try:
            logger.info(f"Extracting clauses for contract {contract_id}")

            # Update contract status
            cosmos_client = get_cosmos_client()
            contract_repo = ContractRepository(cosmos_client.contracts_container)
            contract_repo.update_status(contract_id, ContractStatus.EXTRACTING_CLAUSES)

            # Step 1: Preprocess text
            logger.info("Step 1: Preprocessing text...")
            cleaned_text = self.text_preprocessor.preprocess_text(contract_text)

            # Step 2: Segment into clauses
            logger.info("Step 2: Segmenting into clauses...")
            segments = self.text_preprocessor.segment_by_clauses(cleaned_text)

            logger.info(f"Found {len(segments)} potential clauses")

            # Step 3: Analyze each segment with NLP
            logger.info("Step 3: Analyzing clauses with NLP...")
            clauses = []

            for i, segment in enumerate(segments):
                try:
                    clause = self._process_segment(segment, contract_id, i)
                    if clause:
                        clauses.append(clause)
                except Exception as e:
                    logger.error(f"Failed to process segment {i}: {str(e)}")
                    # Continue with other segments

            logger.info(f"Successfully processed {len(clauses)} clauses")

            # Step 4: Store clauses in Cosmos DB
            logger.info("Step 4: Storing clauses in database...")
            clause_repo = ClauseRepository(cosmos_client.clauses_container)
            created_clauses = clause_repo.bulk_create(clauses)

            logger.info(f"Stored {len(created_clauses)} clauses in database")

            # Step 5: Update contract status
            contract_repo.update_status(contract_id, ContractStatus.CLAUSES_EXTRACTED)

            return created_clauses

        except Exception as e:
            logger.error(f"Clause extraction failed: {str(e)}")
            self._mark_contract_failed(contract_id, f"Clause extraction failed: {str(e)}")
            raise ClauseExtractionError(f"Failed to extract clauses: {str(e)}")

    def _process_segment(self, segment: TextSegment, contract_id: str, index: int) -> Optional[Clause]:
        """
        Process a text segment into a Clause object.

        Args:
            segment: Text segment
            contract_id: Contract identifier
            index: Segment index

        Returns:
            Clause object or None if processing fails
        """
        try:
            # Analyze with NLP
            analysis = self.nlp_service.analyze_clause(segment.text)

            # Generate clause ID
            clause_id = f"clause_{contract_id}_{index:04d}"

            # Create Clause object
            clause = Clause(
                id=clause_id,
                contract_id=contract_id,
                partition_key=contract_id,
                clause_type=analysis["clause_type"],
                clause_subtype=None,  # Can be refined later
                original_text=segment.text,
                normalized_summary=analysis["normalized_summary"],
                page_number=None,
                section_number=segment.section_number,
                start_position=segment.start_position,
                end_position=segment.end_position,
                entities=analysis["entities"],
                risk_signals=analysis["risk_signals"],
                extraction_confidence=analysis.get("classification_confidence", 0.0),
                embedding=None,  # Will be added in Phase 5 (RAG)
            )

            return clause

        except Exception as e:
            logger.error(f"Failed to process segment {index}: {str(e)}")
            return None

    def reextract_clauses(self, contract_id: str, contract_text: str) -> List[Clause]:
        """
        Re-extract clauses (delete old ones first).

        Args:
            contract_id: Contract identifier
            contract_text: Contract text

        Returns:
            List of newly extracted clauses
        """
        try:
            logger.info(f"Re-extracting clauses for contract {contract_id}")

            # Delete existing clauses
            cosmos_client = get_cosmos_client()
            clause_repo = ClauseRepository(cosmos_client.clauses_container)

            existing_clauses = clause_repo.get_by_contract_id(contract_id)
            for clause in existing_clauses:
                clause_repo.delete(clause.id, contract_id)

            logger.info(f"Deleted {len(existing_clauses)} existing clauses")

            # Extract new clauses
            return self.extract_clauses_from_contract(contract_id, contract_text)

        except Exception as e:
            logger.error(f"Re-extraction failed: {str(e)}")
            raise ClauseExtractionError(f"Failed to re-extract clauses: {str(e)}")

    def get_clauses_by_type(self, contract_id: str, clause_type: str) -> List[Clause]:
        """
        Get all clauses of a specific type.

        Args:
            contract_id: Contract identifier
            clause_type: Type to filter by

        Returns:
            List of clauses
        """
        cosmos_client = get_cosmos_client()
        clause_repo = ClauseRepository(cosmos_client.clauses_container)
        return clause_repo.get_by_clause_type(contract_id, clause_type)

    def get_risky_clauses(self, contract_id: str) -> List[Clause]:
        """
        Get clauses with risk signals.

        Args:
            contract_id: Contract identifier

        Returns:
            List of clauses with risk signals
        """
        cosmos_client = get_cosmos_client()
        clause_repo = ClauseRepository(cosmos_client.clauses_container)

        all_clauses = clause_repo.get_by_contract_id(contract_id)

        # Filter clauses with risk signals
        risky_clauses = [c for c in all_clauses if c.risk_signals]

        logger.info(f"Found {len(risky_clauses)} clauses with risk signals")
        return risky_clauses

    def analyze_single_clause(self, clause_text: str) -> dict:
        """
        Analyze a single clause without storing.

        Useful for testing or manual analysis.

        Args:
            clause_text: Clause text

        Returns:
            Analysis dictionary
        """
        return self.nlp_service.analyze_clause(clause_text)

    def get_clause_statistics(self, contract_id: str) -> dict:
        """
        Get statistics about extracted clauses.

        Args:
            contract_id: Contract identifier

        Returns:
            Dictionary of statistics
        """
        cosmos_client = get_cosmos_client()
        clause_repo = ClauseRepository(cosmos_client.clauses_container)

        clauses = clause_repo.get_by_contract_id(contract_id)

        # Count by type
        type_counts: Dict[str, int] = {}
        for clause in clauses:
            type_counts[clause.clause_type] = type_counts.get(clause.clause_type, 0) + 1

        # Count risk signals
        total_risk_signals = sum(len(c.risk_signals) for c in clauses)
        clauses_with_risks = sum(1 for c in clauses if c.risk_signals)

        # Average confidence
        avg_confidence = sum(c.extraction_confidence or 0 for c in clauses) / len(clauses) if clauses else 0

        stats = {
            "total_clauses": len(clauses),
            "clause_types": type_counts,
            "total_risk_signals": total_risk_signals,
            "clauses_with_risk_signals": clauses_with_risks,
            "average_extraction_confidence": avg_confidence,
            "most_common_type": (max(type_counts, key=lambda k: type_counts[k]) if type_counts else None),
        }

        return stats

    def _mark_contract_failed(self, contract_id: str, error_message: str):
        """Mark contract as failed (best effort)."""
        try:
            cosmos_client = get_cosmos_client()
            contract_repo = ContractRepository(cosmos_client.contracts_container)
            contract_repo.update_status(contract_id, ContractStatus.FAILED, error_message)
        except Exception as e:
            logger.error(f"Failed to mark contract as failed: {str(e)}")
