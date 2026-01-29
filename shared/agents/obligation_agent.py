"""Obligation Extraction Agent for extracting contractual obligations."""

import json
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from openai import AzureOpenAI

from ..db import ClauseRepository, get_cosmos_client
from ..db.repositories.obligation_repository import ObligationRepository
from ..models.clause import Clause
from ..models.contract import Contract
from ..models.obligation import (
    Obligation,
    ObligationExtractionResult,
    ObligationPriority,
    ObligationStatus,
    ObligationSummary,
    ObligationType,
    RecurrencePattern,
    ResponsibleParty,
)
from ..utils.config import get_settings
from ..utils.logging import setup_logging
from .base_agent import AgentStatus, BaseAgent

logger = setup_logging(__name__)
settings = get_settings()


class ObligationExtractionAgent(BaseAgent):
    """
    AI Agent for extracting contractual obligations from contract clauses.

    This agent analyzes contract clauses to identify and extract:
    - Payment obligations (amounts, due dates, schedules)
    - Delivery obligations (deliverables, deadlines)
    - Notice obligations (renewal notices, termination notices)
    - Reporting obligations (reports, certifications)
    - Compliance obligations (insurance, audits, certifications)
    - Performance obligations (SLAs, response times)
    """

    agent_name: str = "obligation_extraction_agent"
    agent_version: str = "1.0"

    def __init__(self, contract_id: str, contract: Optional[Contract] = None):
        """
        Initialize the Obligation Extraction Agent.

        Args:
            contract_id: ID of the contract to analyze
            contract: Optional contract object with metadata
        """
        super().__init__(contract_id)
        self.contract = contract
        self._openai_client: Optional[AzureOpenAI] = None
        self._clause_repo: Optional[ClauseRepository] = None
        self._obligation_repo: Optional[ObligationRepository] = None

    @property
    def openai_client(self) -> AzureOpenAI:
        """Get or create Azure OpenAI client."""
        if self._openai_client is None:
            self._openai_client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            )
        return self._openai_client

    @property
    def clause_repo(self) -> ClauseRepository:
        """Get or create clause repository."""
        if self._clause_repo is None:
            cosmos_client = get_cosmos_client()
            self._clause_repo = ClauseRepository(cosmos_client.clauses_container)
        return self._clause_repo

    @property
    def obligation_repo(self) -> ObligationRepository:
        """Get or create obligation repository."""
        if self._obligation_repo is None:
            cosmos_client = get_cosmos_client()
            self._obligation_repo = ObligationRepository(cosmos_client.obligations_container)
        return self._obligation_repo

    def get_required_inputs(self) -> List[str]:
        """Return list of required input data types."""
        return ["clauses"]

    async def execute(self) -> ObligationExtractionResult:
        """
        Execute obligation extraction.

        Returns:
            ObligationExtractionResult with extracted obligations and summary
        """
        logger.info(f"[{self.agent_name}] Starting obligation extraction for contract {self.contract_id}")

        # Step 1: Get all clauses for the contract
        clauses = self.clause_repo.get_all_by_partition(self.contract_id)

        if not clauses:
            self.add_warning("No clauses found for contract")
            return self._create_empty_result()

        logger.info(f"[{self.agent_name}] Retrieved {len(clauses)} clauses")

        # Step 2: Clear existing obligations (for re-extraction)
        existing_count = self.obligation_repo.delete_by_contract(self.contract_id)
        if existing_count > 0:
            logger.info(f"[{self.agent_name}] Cleared {existing_count} existing obligations")

        # Step 3: Extract obligations using AI
        extracted_obligations = await self._extract_obligations_with_ai(clauses)

        logger.info(f"[{self.agent_name}] Extracted {len(extracted_obligations)} obligations")

        # Step 4: Store obligations in database
        if extracted_obligations:
            stored_obligations = self.obligation_repo.bulk_create(extracted_obligations)
            logger.info(f"[{self.agent_name}] Stored {len(stored_obligations)} obligations")
        else:
            stored_obligations = []

        # Step 5: Generate summary
        summary = self.obligation_repo.get_summary(self.contract_id)

        # Create result
        result = ObligationExtractionResult(
            contract_id=self.contract_id,
            obligations=stored_obligations,
            summary=summary,
            extraction_metadata={
                "total_clauses_analyzed": len(clauses),
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "agent_version": self.agent_version,
            },
        )

        logger.info(f"[{self.agent_name}] Extraction complete: {len(stored_obligations)} obligations")

        return result

    async def _extract_obligations_with_ai(self, clauses: List[Clause]) -> List[Obligation]:
        """
        Extract obligations from clauses using GPT.

        Processes clauses in batches to avoid token limits.

        Args:
            clauses: List of clauses to analyze

        Returns:
            List of extracted Obligation objects
        """
        # Process in batches of 40 clauses to avoid token limits
        BATCH_SIZE = 40
        all_obligations: List[Obligation] = []

        # Split clauses into batches
        batches = [clauses[i:i + BATCH_SIZE] for i in range(0, len(clauses), BATCH_SIZE)]
        logger.info(f"[{self.agent_name}] Processing {len(clauses)} clauses in {len(batches)} batches")

        system_prompt = self._build_system_prompt()

        for batch_num, batch in enumerate(batches, 1):
            try:
                logger.info(f"[{self.agent_name}] Processing batch {batch_num}/{len(batches)} ({len(batch)} clauses)...")

                user_prompt = self._build_user_prompt(batch)

                response = self.openai_client.chat.completions.create(
                    model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                    extra_body={"max_completion_tokens": 8000},
                )

                response_text = response.choices[0].message.content
                finish_reason = response.choices[0].finish_reason

                if not response_text:
                    logger.warning(f"[{self.agent_name}] Batch {batch_num}: Empty response (finish_reason: {finish_reason})")
                    self.add_warning(f"Batch {batch_num}: Empty GPT response")
                    continue

                if finish_reason == "length":
                    logger.warning(f"[{self.agent_name}] Batch {batch_num}: Response truncated (finish_reason: length)")
                    self.add_warning(f"Batch {batch_num}: Response may be incomplete")

                logger.info(f"[{self.agent_name}] Batch {batch_num}: Response length {len(response_text)}")

                analysis_result = json.loads(response_text)
                batch_obligations = self._parse_obligations(analysis_result)

                logger.info(f"[{self.agent_name}] Batch {batch_num}: Extracted {len(batch_obligations)} obligations")
                all_obligations.extend(batch_obligations)

            except json.JSONDecodeError as e:
                logger.error(f"[{self.agent_name}] Batch {batch_num}: Failed to parse response: {str(e)}")
                self.add_warning(f"Batch {batch_num}: Parse error - {str(e)}")
            except Exception as e:
                logger.error(f"[{self.agent_name}] Batch {batch_num}: Extraction failed: {str(e)}")
                self.add_warning(f"Batch {batch_num}: Error - {str(e)}")

        logger.info(f"[{self.agent_name}] Total obligations extracted from all batches: {len(all_obligations)}")
        return all_obligations

    def _build_system_prompt(self) -> str:
        """Build the system prompt for obligation extraction."""
        return """You are an expert contract analyst specializing in extracting contractual obligations.

Your task is to identify and extract ALL obligations from the contract clauses provided. An obligation is
any commitment, requirement, or duty that one party must fulfill.

**Types of Obligations to Extract:**

1. **Payment Obligations** - Payment amounts, schedules, due dates, fees
2. **Delivery Obligations** - Deliverables, deadlines, milestones
3. **Notice Obligations** - Required notices (renewal, termination, changes)
4. **Reporting Obligations** - Reports, certifications, documentation
5. **Compliance Obligations** - Insurance, audits, certifications, regulatory
6. **Performance Obligations** - SLAs, response times, availability
7. **Renewal Obligations** - Actions required for renewal
8. **Termination Obligations** - Actions required upon termination
9. **Insurance Obligations** - Insurance coverage requirements
10. **Audit Obligations** - Audit cooperation, record keeping
11. **Confidentiality Obligations** - Data protection, non-disclosure

**For Each Obligation, Extract:**
- Type of obligation
- Title (short, descriptive)
- Description (full details)
- Due date (specific date if mentioned, or relative like "within 30 days of X")
- Is it recurring? (yes/no)
- Recurrence pattern (daily, weekly, monthly, quarterly, annually)
- Who is responsible (which party)
- Amount (if monetary)
- Currency (if monetary)
- Priority (critical, high, medium, low)
- Source clause ID(s)
- The original text from which this was extracted

**Output Format:**
Return a JSON object with this structure:
{
  "obligations": [
    {
      "obligation_type": "payment|delivery|notice|reporting|compliance|performance|renewal|termination|insurance|audit|confidentiality|other",
      "title": "Short descriptive title",
      "description": "Full description of the obligation",
      "due_date": "YYYY-MM-DD or null if not specified",
      "effective_date": "YYYY-MM-DD or null",
      "is_recurring": true/false,
      "recurrence_pattern": "none|daily|weekly|monthly|quarterly|semi_annually|annually|custom",
      "responsible_party_name": "Party name",
      "responsible_party_role": "service_provider|client|vendor|buyer|seller|licensor|licensee|landlord|tenant",
      "is_our_organization": false,
      "amount": 0.0 or null,
      "currency": "USD" or appropriate currency,
      "priority": "critical|high|medium|low",
      "source_clause_ids": ["clause_id_1"],
      "extracted_text": "Original text from clause",
      "confidence": 0.0-1.0
    }
  ],
  "extraction_notes": "Any notes about the extraction process"
}

**Important Rules:**
- Extract ALL obligations, even implied ones
- Be specific about dates and amounts
- Include the source clause IDs for traceability
- If a party name is not explicit, use the role (e.g., "Service Provider", "Client")
- Set is_our_organization to false by default (system can override later)
- Confidence should reflect how clearly the obligation is stated
"""

    def _build_user_prompt(self, clauses: List[Clause]) -> str:
        """Build the user prompt with clause content."""
        # Get contract metadata if available
        contract_info = ""
        if self.contract:
            contract_info = f"""
**Contract Information:**
- Contract ID: {self.contract_id}
- Title: {getattr(self.contract, 'title', 'Unknown')}
- Parties: {getattr(self.contract, 'parties', ['Unknown'])}
- Contract Type: {getattr(self.contract, 'contract_type', 'Unknown')}
- Start Date: {getattr(self.contract, 'start_date', 'Unknown')}
- End Date: {getattr(self.contract, 'end_date', 'Unknown')}
"""

        # Format clauses
        clauses_text = self._format_clauses_for_prompt(clauses)

        prompt = f"""Analyze the following contract clauses and extract ALL contractual obligations.

{contract_info}

**Contract Clauses:**
{clauses_text}

**Your Task:**
1. Read through ALL clauses carefully
2. Identify EVERY obligation (payment, delivery, notice, reporting, compliance, performance, etc.)
3. Extract specific details (dates, amounts, parties, recurrence)
4. Link each obligation to its source clause(s)
5. Return the complete list in JSON format

Be thorough - missing obligations could lead to missed deadlines or compliance issues."""

        return prompt

    def _format_clauses_for_prompt(self, clauses: List[Clause]) -> str:
        """Format clauses for the AI prompt."""
        formatted = []

        for clause in clauses:
            clause_text = f"""
--- Clause ID: {clause.id} ---
Type: {clause.clause_type}
Section: {clause.section_number or 'N/A'}
Text: {clause.original_text}
Summary: {clause.normalized_summary or 'N/A'}
"""
            formatted.append(clause_text)

        return "\n".join(formatted)

    def _parse_obligations(self, analysis_result: Dict[str, Any]) -> List[Obligation]:
        """
        Parse AI response into Obligation objects.

        Args:
            analysis_result: Parsed JSON response from GPT

        Returns:
            List of Obligation objects
        """
        obligations = []

        for idx, item in enumerate(analysis_result.get("obligations", [])):
            try:
                obligation = self._create_obligation_from_item(item, idx)
                if obligation:
                    obligations.append(obligation)
            except Exception as e:
                logger.error(f"[{self.agent_name}] Failed to parse obligation: {str(e)}")
                self.add_warning(f"Failed to parse obligation {idx}: {str(e)}")

        return obligations

    def _create_obligation_from_item(self, item: Dict[str, Any], index: int) -> Optional[Obligation]:
        """
        Create an Obligation object from a parsed item.

        Args:
            item: Dictionary with obligation data
            index: Index for generating unique ID

        Returns:
            Obligation object or None if parsing fails
        """
        # Generate unique ID
        obligation_id = f"obl_{self.contract_id}_{uuid.uuid4().hex[:8]}"

        # Map obligation type
        obligation_type = self._map_obligation_type(item.get("obligation_type", "other"))

        # Parse dates
        due_date = self._parse_date(item.get("due_date"))
        effective_date = self._parse_date(item.get("effective_date"))

        # Map recurrence pattern
        recurrence_pattern = self._map_recurrence_pattern(item.get("recurrence_pattern", "none"))

        # Create responsible party
        responsible_party = ResponsibleParty(
            party_name=item.get("responsible_party_name", "Unknown Party"),
            party_role=item.get("responsible_party_role", "unknown"),
            is_our_organization=item.get("is_our_organization", False),
        )

        # Map priority
        priority = self._map_priority(item.get("priority", "medium"))

        # Create obligation (handle None values explicitly for required string fields)
        obligation = Obligation(
            id=obligation_id,
            contract_id=self.contract_id,
            partition_key=self.contract_id,
            obligation_type=obligation_type,
            title=item.get("title") or "Untitled Obligation",
            description=item.get("description") or "",
            due_date=due_date,
            effective_date=effective_date,
            is_recurring=item.get("is_recurring", False),
            recurrence_pattern=recurrence_pattern,
            responsible_party=responsible_party,
            amount=item.get("amount"),
            currency=item.get("currency") or "USD",
            priority=priority,
            clause_ids=item.get("source_clause_ids") or [],
            extracted_text=item.get("extracted_text"),
            extraction_confidence=item.get("confidence") or 0.7,
        )

        return obligation

    def _map_obligation_type(self, type_str: str) -> ObligationType:
        """Map string to ObligationType enum."""
        mapping = {
            "payment": ObligationType.PAYMENT,
            "delivery": ObligationType.DELIVERY,
            "notice": ObligationType.NOTICE,
            "reporting": ObligationType.REPORTING,
            "compliance": ObligationType.COMPLIANCE,
            "performance": ObligationType.PERFORMANCE,
            "renewal": ObligationType.RENEWAL,
            "termination": ObligationType.TERMINATION,
            "insurance": ObligationType.INSURANCE,
            "audit": ObligationType.AUDIT,
            "confidentiality": ObligationType.CONFIDENTIALITY,
        }
        return mapping.get(type_str.lower(), ObligationType.OTHER)

    def _map_recurrence_pattern(self, pattern_str: str) -> RecurrencePattern:
        """Map string to RecurrencePattern enum."""
        mapping = {
            "none": RecurrencePattern.NONE,
            "daily": RecurrencePattern.DAILY,
            "weekly": RecurrencePattern.WEEKLY,
            "monthly": RecurrencePattern.MONTHLY,
            "quarterly": RecurrencePattern.QUARTERLY,
            "semi_annually": RecurrencePattern.SEMI_ANNUALLY,
            "annually": RecurrencePattern.ANNUALLY,
            "custom": RecurrencePattern.CUSTOM,
        }
        return mapping.get(pattern_str.lower(), RecurrencePattern.NONE)

    def _map_priority(self, priority_str: str) -> ObligationPriority:
        """Map string to ObligationPriority enum."""
        mapping = {
            "critical": ObligationPriority.CRITICAL,
            "high": ObligationPriority.HIGH,
            "medium": ObligationPriority.MEDIUM,
            "low": ObligationPriority.LOW,
        }
        return mapping.get(priority_str.lower(), ObligationPriority.MEDIUM)

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None

        try:
            # Try ISO format first
            return date.fromisoformat(date_str)
        except ValueError:
            pass

        # Try common formats
        formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue

        logger.warning(f"[{self.agent_name}] Could not parse date: {date_str}")
        return None

    def _create_empty_result(self) -> ObligationExtractionResult:
        """Create an empty result when no clauses are found."""
        return ObligationExtractionResult(
            contract_id=self.contract_id,
            obligations=[],
            summary=ObligationSummary(
                contract_id=self.contract_id,
                total_obligations=0,
            ),
            extraction_metadata={
                "error": "No clauses found",
                "extraction_timestamp": datetime.utcnow().isoformat(),
            },
        )
