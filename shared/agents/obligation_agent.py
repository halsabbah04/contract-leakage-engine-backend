"""Obligation Extraction Agent for extracting contractual obligations."""

import asyncio
import json
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

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
from ..utils.async_helpers import RateLimiter, retry_with_backoff
from .base_agent import AgentStatus, BaseAgent

logger = setup_logging(__name__)
settings = get_settings()

# Global rate limiter for OpenAI API calls (60 requests per minute)
_openai_rate_limiter = RateLimiter(max_requests=60, time_window=60.0)


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

    def __init__(
        self,
        contract_id: str,
        contract: Optional[Contract] = None,
        contract_metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the Obligation Extraction Agent.

        Args:
            contract_id: ID of the contract to analyze
            contract: Optional contract object with metadata
            contract_metadata: Optional metadata including currency and party names
        """
        super().__init__(contract_id)
        self.contract = contract
        self.contract_metadata = contract_metadata or {}
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

    # Clause types that typically contain obligations
    OBLIGATION_CLAUSE_TYPES = {
        "payment", "payment_terms", "pricing",
        "delivery", "service_level", "sla",
        "termination", "renewal", "auto_renewal",
        "notice", "reporting",
        "compliance", "audit", "insurance",
        "liability", "indemnification",
        "confidentiality", "intellectual_property",
        "penalty", "penalties",
        "warranty", "performance",
    }

    # Keywords that indicate obligation presence
    OBLIGATION_KEYWORDS = [
        "shall", "must", "will", "required", "obligated",
        "within", "days", "deadline", "due", "notice",
        "pay", "deliver", "report", "submit", "provide",
        "maintain", "ensure", "comply", "certify", "renew",
        "terminate", "notify", "respond", "complete",
    ]

    async def execute(self) -> ObligationExtractionResult:
        """
        Execute obligation extraction.

        Returns:
            ObligationExtractionResult with extracted obligations and summary
        """
        logger.info(f"[{self.agent_name}] Starting obligation extraction for contract {self.contract_id}")

        # Step 1: Get all clauses for the contract
        all_clauses = self.clause_repo.get_all_by_partition(self.contract_id)

        if not all_clauses:
            self.add_warning("No clauses found for contract")
            return self._create_empty_result()

        logger.info(f"[{self.agent_name}] Retrieved {len(all_clauses)} total clauses")

        # Step 2: Pre-filter clauses to only those likely to contain obligations
        relevant_clauses = self._filter_relevant_clauses(all_clauses)
        logger.info(f"[{self.agent_name}] Filtered to {len(relevant_clauses)} relevant clauses (from {len(all_clauses)})")

        if not relevant_clauses:
            self.add_warning("No relevant clauses found for obligation extraction")
            return self._create_empty_result()

        # Step 3: Clear existing obligations (for re-extraction)
        existing_count = self.obligation_repo.delete_by_contract(self.contract_id)
        if existing_count > 0:
            logger.info(f"[{self.agent_name}] Cleared {existing_count} existing obligations")

        # Step 4: Extract obligations using AI (with parallel batch processing)
        extracted_obligations = await self._extract_obligations_with_ai(relevant_clauses)

        logger.info(f"[{self.agent_name}] Extracted {len(extracted_obligations)} obligations")

        # Step 5: Store obligations in database
        if extracted_obligations:
            stored_obligations = self.obligation_repo.bulk_create(extracted_obligations)
            logger.info(f"[{self.agent_name}] Stored {len(stored_obligations)} obligations")
        else:
            stored_obligations = []

        # Step 6: Generate summary (pass counterparty for better party identification)
        counterparty = self.contract_metadata.get("counterparty")
        summary = self.obligation_repo.get_summary(self.contract_id, counterparty=counterparty)

        # Create result
        result = ObligationExtractionResult(
            contract_id=self.contract_id,
            obligations=stored_obligations,
            summary=summary,
            extraction_metadata={
                "total_clauses": len(all_clauses),
                "relevant_clauses_analyzed": len(relevant_clauses),
                "extraction_timestamp": datetime.utcnow().isoformat(),
                "agent_version": self.agent_version,
            },
        )

        logger.info(f"[{self.agent_name}] Extraction complete: {len(stored_obligations)} obligations")

        return result

    def _filter_relevant_clauses(self, clauses: List[Clause]) -> List[Clause]:
        """
        Filter clauses to only those likely to contain obligations.

        Args:
            clauses: All clauses from the contract

        Returns:
            Filtered list of relevant clauses
        """
        relevant = []

        for clause in clauses:
            # Check 1: Clause type is in obligation-related types
            clause_type = (clause.clause_type or "").lower()
            if clause_type in self.OBLIGATION_CLAUSE_TYPES:
                relevant.append(clause)
                continue

            # Check 2: Clause text contains obligation keywords
            text = (clause.original_text or "").lower()
            if any(keyword in text for keyword in self.OBLIGATION_KEYWORDS):
                relevant.append(clause)
                continue

        return relevant

    async def _extract_obligations_with_ai(self, clauses: List[Clause]) -> List[Obligation]:
        """
        Extract obligations from clauses using GPT.

        Processes clauses in batches with parallel execution for speed.

        Args:
            clauses: List of clauses to analyze

        Returns:
            List of extracted Obligation objects
        """
        # Optimized batch size and concurrency
        BATCH_SIZE = 50
        MAX_CONCURRENT_BATCHES = 8  # Increased from 5 to 8 for better throughput

        # Split clauses into batches
        batches = [clauses[i:i + BATCH_SIZE] for i in range(0, len(clauses), BATCH_SIZE)]
        logger.info(f"[{self.agent_name}] Processing {len(clauses)} clauses in {len(batches)} batches (max {MAX_CONCURRENT_BATCHES} concurrent)")

        system_prompt = self._build_system_prompt()
        all_obligations: List[Obligation] = []

        # Use semaphore for controlled concurrency - more efficient than sequential groups
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_BATCHES)

        async def _process_with_semaphore(batch, batch_num):
            """Process a batch with semaphore control."""
            async with semaphore:
                return await self._process_single_batch(batch, batch_num, len(batches), system_prompt)

        # Create all tasks upfront for fully parallel execution
        tasks = [
            _process_with_semaphore(batch, batch_num)
            for batch_num, batch in enumerate(batches, start=1)
        ]

        logger.info(f"[{self.agent_name}] Starting parallel batch processing with semaphore control...")

        # Execute all batches with controlled concurrency
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect results
        for batch_num, result in enumerate(results, start=1):
            if isinstance(result, Exception):
                logger.error(f"[{self.agent_name}] Batch {batch_num}: Failed with exception: {str(result)}")
                self.add_warning(f"Batch {batch_num}: Error - {str(result)}")
            elif result:
                all_obligations.extend(result)

        logger.info(f"[{self.agent_name}] Total obligations extracted from all batches: {len(all_obligations)}")
        return all_obligations

    async def _process_single_batch(
        self, batch: List[Clause], batch_num: int, total_batches: int, system_prompt: str
    ) -> List[Obligation]:
        """
        Process a single batch of clauses with rate limiting and retry logic.

        Args:
            batch: List of clauses to process
            batch_num: Current batch number
            total_batches: Total number of batches
            system_prompt: The system prompt for GPT

        Returns:
            List of extracted obligations from this batch
        """
        async def _make_api_call():
            # Acquire rate limiter token before making API call
            await _openai_rate_limiter.acquire()

            logger.info(f"[{self.agent_name}] Batch {batch_num}/{total_batches}: Processing {len(batch)} clauses...")

            user_prompt = self._build_user_prompt(batch)

            # Run the synchronous OpenAI call in a thread pool to not block
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.1,  # Low temperature for more consistent extraction
                    response_format={"type": "json_object"},
                    extra_body={"max_completion_tokens": 8000},
                )
            )

            response_text = response.choices[0].message.content
            finish_reason = response.choices[0].finish_reason

            if not response_text:
                logger.warning(f"[{self.agent_name}] Batch {batch_num}: Empty response (finish_reason: {finish_reason})")
                self.add_warning(f"Batch {batch_num}: Empty GPT response")
                return []

            if finish_reason == "length":
                logger.warning(f"[{self.agent_name}] Batch {batch_num}: Response truncated (finish_reason: length)")
                self.add_warning(f"Batch {batch_num}: Response may be incomplete")

            logger.info(f"[{self.agent_name}] Batch {batch_num}: Response length {len(response_text)}")

            analysis_result = json.loads(response_text)
            batch_obligations = self._parse_obligations(analysis_result)

            logger.info(f"[{self.agent_name}] Batch {batch_num}: Extracted {len(batch_obligations)} obligations")
            return batch_obligations

        try:
            # Use retry logic with exponential backoff for API calls
            return await retry_with_backoff(
                _make_api_call,
                max_retries=3,
                initial_delay=2.0,
                backoff_factor=2.0,
                exceptions=(Exception,)
            )
        except Exception as e:
            logger.error(f"[{self.agent_name}] Batch {batch_num}: Failed after all retries: {str(e)}")
            self.add_warning(f"Batch {batch_num}: Failed after retries - {str(e)}")
            return []

        except json.JSONDecodeError as e:
            logger.error(f"[{self.agent_name}] Batch {batch_num}: Failed to parse response: {str(e)}")
            self.add_warning(f"Batch {batch_num}: Parse error - {str(e)}")
            return []
        except Exception as e:
            logger.error(f"[{self.agent_name}] Batch {batch_num}: Extraction failed: {str(e)}")
            self.add_warning(f"Batch {batch_num}: Error - {str(e)}")
            return []

    def _build_system_prompt(self) -> str:
        """Build the system prompt for obligation extraction."""
        # Get contract currency and party names from metadata
        contract_currency = self.contract_metadata.get("contract_currency", "USD")
        party_names = self.contract_metadata.get("party_names", [])
        counterparty = self.contract_metadata.get("counterparty")

        # Build party context
        party_context = ""
        if party_names:
            party_context = f"\n\nPARTIES IN CONTRACT: {', '.join(party_names)}"
            if counterparty:
                party_context += f"\nCounterparty: {counterparty}"

        return f"""Extract ALL contractual obligations. Output JSON only.

Types: payment, delivery, notice, reporting, compliance, performance, renewal, termination, insurance, audit, confidentiality, other

CONTRACT CURRENCY: {contract_currency}{party_context}

JSON format:
{{"obligations":[{{
  "obligation_type":"<type>",
  "title":"Short title",
  "description":"Details",
  "due_date":"YYYY-MM-DD or null",
  "effective_date":"YYYY-MM-DD or null",
  "is_recurring":true/false,
  "recurrence_pattern":"none|daily|weekly|monthly|quarterly|semi_annually|annually",
  "responsible_party_name":"Party name",
  "responsible_party_role":"service_provider|client|vendor|buyer|seller|other",
  "is_our_organization":false,
  "amount":number or null,
  "currency":"{contract_currency}",
  "priority":"critical|high|medium|low",
  "source_clause_ids":["clause_id"],
  "extracted_text":"Quote from clause",
  "confidence":0.0-1.0
}}]}}

Rules:
- Extract all obligations with clause IDs
- CRITICAL: Use currency "{contract_currency}" for ALL monetary obligations unless explicitly stated otherwise in the clause text
- CRITICAL: Use ACTUAL party names from the PARTIES list above. Do NOT use generic terms like "service provider", "client", "vendor" when specific party names are available.
  * Example: If parties are "Zain Bahrain B.S.C. (Zain)" and "Bahrain Economic Development Board (EDB)", use ONLY "Zain" and "EDB"
  * ALWAYS use the abbreviation in parentheses if available (e.g., "EDB" not "Bahrain Economic Development Board")
  * If no abbreviation exists, use the shortest form of the company name
  * For generic references like "Either Party", "The Parties", "Both Parties" - determine which SPECIFIC party from the list the obligation applies to based on context
  * BE CONSISTENT: Use the same exact party name throughout (e.g., always "EDB", never mix "EDB" and "Bahrain Economic Development Board")
  * Only use "Both Parties" if obligation truly applies to both parties equally
- CRITICAL: Extract monetary amounts EXACTLY as stated in the clause text. Do NOT infer or calculate amounts.
- Set is_our_organization=false by default"""

    def _build_user_prompt(self, clauses: List[Clause]) -> str:
        """Build the user prompt with clause content."""
        # Format clauses compactly
        clauses_text = self._format_clauses_for_prompt(clauses)

        prompt = f"""Extract all obligations from these clauses. Return JSON.

CLAUSES:
{clauses_text}

Extract obligations with: type, title, description, dates, amounts, responsible party, priority, source clause IDs."""

        return prompt

    def _format_clauses_for_prompt(self, clauses: List[Clause]) -> str:
        """Format clauses compactly for the AI prompt."""
        formatted = []

        for clause in clauses:
            # Compact format: ID | Type | Text
            clause_text = f"[{clause.id}] ({clause.clause_type}) {clause.original_text}"
            formatted.append(clause_text)

        return "\n\n".join(formatted)

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

        # Create responsible party with normalized name
        raw_party_name = item.get("responsible_party_name", "Unknown Party")
        normalized_party_name = self._normalize_party_name(raw_party_name)
        responsible_party = ResponsibleParty(
            party_name=normalized_party_name,
            party_role=item.get("responsible_party_role", "unknown"),
            is_our_organization=item.get("is_our_organization", False),
        )

        # Map priority
        priority = self._map_priority(item.get("priority", "medium"))

        # Get contract currency from metadata (fallback to USD only if not provided)
        default_currency = self.contract_metadata.get("contract_currency", "USD")

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
            currency=item.get("currency") or default_currency,
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

    def _normalize_party_name(self, party_name: str) -> str:
        """
        Normalize party names to reduce fragmentation.

        Args:
            party_name: Raw party name from AI extraction

        Returns:
            Normalized party name
        """
        if not party_name:
            return "Unknown Party"

        name = party_name.strip()
        name_lower = name.lower()

        # Generic party references that should be kept as-is
        generic_parties = {
            "both parties", "either party", "each party", "the parties",
            "all parties", "neither party", "any party"
        }

        # Check if it's a generic reference
        for generic in generic_parties:
            if generic in name_lower:
                # Capitalize properly
                return generic.title()

        # Remove common suffixes/prefixes in parentheses for normalization
        # e.g., "Zain Bahrain B.S.C. (Zain)" -> "Zain"
        # e.g., "Bahrain Economic Development Board (EDB)" -> "EDB"
        import re

        # Extract short name from parentheses if present at the end
        paren_match = re.search(r'\(([^)]+)\)\s*$', name)
        if paren_match:
            short_name = paren_match.group(1).strip()
            # If short name looks like an abbreviation or simple name, use it
            if len(short_name) <= 20 and not any(x in short_name.lower() for x in ['requesting', 'provisioning', 'confirmation', 'applicable']):
                return short_name

        # Handle "X and/or Y" patterns - these should generally be kept but cleaned
        if " and/or " in name_lower or " or " in name_lower:
            # Keep as-is but clean up
            return name

        # Handle role-based names at the end like "(requesting Party)"
        role_pattern = re.search(r'\s*\([^)]*(?:party|requesting|receiving|disclosing|breaching|affected)[^)]*\)\s*$', name, re.IGNORECASE)
        if role_pattern:
            # Remove the role suffix
            cleaned = name[:role_pattern.start()].strip()
            if cleaned:
                return self._normalize_party_name(cleaned)  # Recursively normalize

        return name

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
