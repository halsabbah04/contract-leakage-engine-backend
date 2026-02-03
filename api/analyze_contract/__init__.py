"""Azure Function: Analyze Contract

Orchestrates the complete contract analysis pipeline:
1. Extract text (OCR if needed)
2. Extract clauses
3. Detect leakage (rules + AI) + Extract obligations (IN PARALLEL)
4. Calculate impact
"""

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple

import azure.functions as func

from shared.db import ContractRepository, get_cosmos_client
from shared.models.clause import Clause
from shared.models.contract import ContractStatus
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging
from shared.utils.async_helpers import (
    RateLimiter,
    retry_with_backoff,
    run_with_timeout,
    gather_with_progress,
    ProgressTracker
)

logger = setup_logging(__name__)

# Thread pool for running sync operations concurrently
# Increased from 4 to 12 to handle: 3 main agents + up to 8 obligation batches + buffer
_executor = ThreadPoolExecutor(max_workers=12)

# Rate limiter for OpenAI API (60 requests per minute = 1 per second)
_openai_rate_limiter = RateLimiter(max_requests=60, time_window=60.0)


def extract_contract_value_from_clauses(clauses: List[Clause]) -> Tuple[Optional[float], Optional[str]]:
    """
    Extract estimated contract value and currency from monetary entities in clauses.

    Uses a smart approach:
    1. Collect all monetary values from pricing/payment/service-level clauses (most likely to contain contract value)
    2. If no values from those, fall back to all clauses
    3. Use the MEDIAN of the top 3 values (to avoid outliers like insurance caps or penalties)
    4. Validate the value is within a reasonable range

    Args:
        clauses: List of extracted clauses with entities

    Returns:
        Tuple of (contract_value, currency) - both None if no monetary values found
    """
    # Maximum reasonable contract value (1 billion) - anything higher is likely an error
    MAX_REASONABLE_VALUE = 1_000_000_000
    # Minimum reasonable contract value - below this likely not the actual contract value
    MIN_REASONABLE_VALUE = 1_000

    # Preferred clause types for contract value extraction
    value_clause_types = {'pricing', 'payment', 'payment_terms', 'service_level', 'sla'}

    all_amounts: List[float] = []
    priority_amounts: List[float] = []
    extracted_currency: Optional[str] = None

    for clause in clauses:
        if clause.entities:
            # Get amounts from entities
            amounts = clause.entities.amounts if clause.entities.amounts else []
            for amount in amounts:
                if amount and MIN_REASONABLE_VALUE <= amount <= MAX_REASONABLE_VALUE:
                    all_amounts.append(amount)
                    # Track currency from first valid amount
                    if extracted_currency is None and clause.entities.currency:
                        extracted_currency = clause.entities.currency

                    # Prioritize amounts from pricing/payment clauses
                    if clause.clause_type and clause.clause_type.lower() in value_clause_types:
                        priority_amounts.append(amount)
                elif amount and amount > MAX_REASONABLE_VALUE:
                    logger.warning(f"Ignoring unreasonably large value: {amount:,.0f} (likely OCR error or insurance cap)")

    # Use priority amounts if available, otherwise all amounts
    candidate_amounts = priority_amounts if priority_amounts else all_amounts

    if not candidate_amounts:
        logger.info("No reasonable monetary values found in contract - financial impact will not be calculated")
        return None, None

    # Sort descending and take median of top 3 to avoid outliers
    candidate_amounts.sort(reverse=True)
    top_amounts = candidate_amounts[:3]

    if len(top_amounts) == 1:
        estimated_value = top_amounts[0]
    elif len(top_amounts) == 2:
        estimated_value = (top_amounts[0] + top_amounts[1]) / 2
    else:
        # Median of top 3
        estimated_value = top_amounts[1]

    final_currency = extracted_currency or "USD"
    logger.info(f"Extracted contract value: {final_currency} {estimated_value:,.2f} (from {len(candidate_amounts)} monetary values)")

    return estimated_value, final_currency


def calculate_contract_duration_years(contract) -> int:
    """
    Calculate contract duration in years from start/end dates.

    Args:
        contract: Contract object with start_date and end_date

    Returns:
        Duration in years (default 3 if dates not available)
    """
    try:
        if contract.start_date and contract.end_date:
            from datetime import datetime

            start = datetime.fromisoformat(contract.start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(contract.end_date.replace("Z", "+00:00"))
            years = (end - start).days / 365.25
            return max(1, int(years))
    except Exception:
        pass

    return 3  # Default to 3 years


async def run_rules_engine_async(
    contract_id: str,
    clauses: List[Clause],
    contract_metadata: Dict[str, Any],
    risk_profile: Any,
) -> List[Any]:
    """Run rules engine detection asynchronously with retry and timeout."""
    from shared.services.rules_engine import RulesEngine

    async def _run():
        loop = asyncio.get_event_loop()
        rules_engine = RulesEngine()

        # Run sync operation in thread pool
        findings = await loop.run_in_executor(
            _executor,
            lambda: rules_engine.detect_leakage(contract_id, clauses, contract_metadata, risk_profile)
        )
        logger.info(f"Rules engine detected {len(findings)} potential issues")
        return findings

    # Run with retry and 60s timeout
    return await retry_with_backoff(
        lambda: run_with_timeout(_run(), timeout=60.0, task_name="Rules Engine"),
        max_retries=2,
        initial_delay=2.0
    )


async def run_ai_detection_async(
    contract_id: str,
    contract_metadata: Dict[str, Any],
    clause_count: int,
) -> List[Any]:
    """Run AI detection asynchronously with retry, timeout, and rate limiting."""
    if clause_count > 50:
        logger.warning(f"Skipping AI detection: {clause_count} clauses exceeds limit of 50")
        return []

    async def _run():
        from shared.services.ai_detection_service import AIDetectionService

        # Acquire rate limiter token
        await _openai_rate_limiter.acquire()

        loop = asyncio.get_event_loop()
        ai_service = AIDetectionService()

        # Run sync operation in thread pool
        ai_findings = await loop.run_in_executor(
            _executor,
            lambda: ai_service.detect_leakage(contract_id, contract_metadata)
        )
        logger.info(f"AI detection found {len(ai_findings)} findings")
        return ai_findings

    try:
        # Run with retry and 120s timeout (AI detection can take longer)
        return await retry_with_backoff(
            lambda: run_with_timeout(_run(), timeout=120.0, task_name="AI Detection"),
            max_retries=2,
            initial_delay=3.0
        )
    except Exception as e:
        logger.error(f"AI detection failed after retries: {str(e)}")
        return []


async def run_obligation_extraction_async(
    contract_id: str,
    contract: Any,
    clauses: List[Clause],
    contract_metadata: Dict[str, Any]
) -> int:
    """Run obligation extraction asynchronously with retry and timeout."""
    async def _run():
        logger.info(f"[OBLIGATION] Starting obligation extraction for contract {contract_id}")

        from shared.agents.obligation_agent import ObligationExtractionAgent
        from shared.agents.base_agent import AgentStatus

        logger.info(f"[OBLIGATION] Imports successful, creating agent...")

        # Extract party names from contract and clauses
        party_names = set()
        if contract and contract.counterparty:
            party_names.add(contract.counterparty)

        # Extract party names from clause entities
        for clause in clauses:
            if clause.entities and clause.entities.parties:
                party_names.update(clause.entities.parties)

        # Create enriched metadata with currency and party information
        enriched_metadata = {
            **contract_metadata,
            "party_names": list(party_names),
            "counterparty": contract.counterparty if contract else None
        }

        logger.info(f"[OBLIGATION] Metadata: currency={contract_metadata.get('contract_currency')}, parties={list(party_names)}")

        obligation_agent = ObligationExtractionAgent(contract_id, contract, enriched_metadata)
        logger.info(f"[OBLIGATION] Agent created, running extraction...")

        agent_result = await obligation_agent.run()

        logger.info(f"[OBLIGATION] Agent completed with status: {agent_result.status}")

        if agent_result.status in [AgentStatus.COMPLETED, AgentStatus.PARTIAL] and agent_result.data:
            obligations_count = agent_result.data.summary.total_obligations
            logger.info(f"[OBLIGATION] Extracted {obligations_count} obligations")
            return obligations_count
        else:
            logger.warning(f"[OBLIGATION] Extraction completed with issues - Status: {agent_result.status}, Error: {agent_result.error}")
            return 0

    try:
        # Run with retry and 180s timeout (obligation extraction can be lengthy for large contracts)
        return await retry_with_backoff(
            lambda: run_with_timeout(_run(), timeout=180.0, task_name="Obligation Extraction"),
            max_retries=2,
            initial_delay=5.0
        )
    except Exception as e:
        logger.error(f"[OBLIGATION] Extraction failed with exception after retries: {str(e)}", exc_info=True)
        return 0


async def run_parallel_analysis(
    contract_id: str,
    contract: Any,
    clauses: List[Clause],
    contract_metadata: Dict[str, Any],
    risk_profile: Any,
) -> Tuple[List[Any], List[Any], int]:
    """
    Run rules detection, AI detection, and obligation extraction in parallel with progress tracking.

    Returns:
        Tuple of (rule_findings, ai_findings, obligations_count)
    """
    logger.info("Starting parallel analysis (Rules + AI + Obligations)...")

    # Create tasks for parallel execution
    tasks = [
        run_rules_engine_async(contract_id, clauses, contract_metadata, risk_profile),
        run_ai_detection_async(contract_id, contract_metadata, len(clauses)),
        run_obligation_extraction_async(contract_id, contract, clauses, contract_metadata)
    ]

    task_names = ["Rules Engine", "AI Detection", "Obligation Extraction"]

    # Run all tasks in parallel with progress tracking
    results = await gather_with_progress(tasks, task_names, return_exceptions=True)

    # Process results
    rule_findings = results[0] if not isinstance(results[0], Exception) else []
    ai_findings = results[1] if not isinstance(results[1], Exception) else []
    obligations_count = results[2] if not isinstance(results[2], Exception) else 0

    logger.info(f"[PARALLEL] Processed results: rules={len(rule_findings)}, ai={len(ai_findings)}, obligations={obligations_count}")

    # Log any exceptions
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error(f"{task_names[i]} failed with exception: {str(result)}", exc_info=result)

    logger.info(
        f"Parallel analysis complete: {len(rule_findings)} rule findings, "
        f"{len(ai_findings)} AI findings, {obligations_count} obligations"
    )

    return rule_findings, ai_findings, obligations_count


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Trigger complete analysis pipeline for a contract.

    Route: POST /api/analyze_contract/{contract_id}

    This orchestrates the entire analysis workflow:
    - Text extraction
    - Clause extraction
    - Leakage detection
    - Impact calculation

    Returns:
    - 202: Analysis started (asynchronous processing)
    - 404: Contract not found
    - 409: Analysis already in progress
    - 500: Server error
    """
    logger.info("analyze_contract function triggered")

    try:
        # Get contract_id from route parameter
        contract_id = req.route_params.get("contract_id")

        if not contract_id:
            logger.warning("No contract_id provided")
            return func.HttpResponse(
                json.dumps({"error": "contract_id is required"}),
                status_code=400,
                mimetype="application/json",
            )

        logger.info(f"Starting analysis for contract: {contract_id}")

        # Initialize repository
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)

        # Get contract
        contract = contract_repo.get_by_contract_id(contract_id)
        if not contract:
            logger.warning(f"Contract not found: {contract_id}")
            return func.HttpResponse(
                json.dumps({"error": f"Contract '{contract_id}' not found"}),
                status_code=404,
                mimetype="application/json",
            )

        # Check if analysis already in progress
        if contract.status in [
            ContractStatus.EXTRACTING_TEXT,
            ContractStatus.EXTRACTING_CLAUSES,
            ContractStatus.ANALYZING,
        ]:
            logger.warning(f"Analysis already in progress for contract {contract_id}")
            return func.HttpResponse(
                json.dumps(
                    {
                        "error": "Analysis already in progress",
                        "contract_id": contract_id,
                        "current_status": contract.status,
                    }
                ),
                status_code=409,
                mimetype="application/json",
            )

        # Record start time
        start_time = time.time()

        # Update status to analyzing
        contract_repo.update_status(contract_id, ContractStatus.ANALYZING)

        # Import services
        from shared.services.clause_extraction_service import ClauseExtractionService
        from shared.services.document_service import DocumentService

        # Phase 2: Text Extraction (if not already done)
        if contract.status == ContractStatus.UPLOADED:
            logger.info("Phase 2: Extracting text...")
            # Text extraction happens in upload_contract function
            # If we're here and status is UPLOADED, text needs extraction
            pass  # Skip if already extracted

        # Phase 3: Clause Extraction
        clauses = []  # Initialize clauses list
        if contract.status in [ContractStatus.TEXT_EXTRACTED, ContractStatus.UPLOADED]:
            logger.info("Phase 3: Extracting clauses...")

            # Get extracted text
            document_service = DocumentService()
            contract_text = document_service.get_extracted_text(contract_id)

            if contract_text:
                # Extract clauses
                clause_service = ClauseExtractionService()
                clauses = clause_service.extract_clauses_from_contract(contract_id, contract_text)
                logger.info(f"Extracted {len(clauses)} clauses")
            else:
                raise Exception("No extracted text found for contract")
        else:
            # If clauses were already extracted, fetch them from database
            logger.info("Phase 3: Fetching previously extracted clauses...")
            from shared.db import ClauseRepository
            clause_repo = ClauseRepository(cosmos_client.clauses_container)
            clauses = clause_repo.get_by_contract_id(contract_id)
            logger.info(f"Fetched {len(clauses)} previously extracted clauses")

        # Phase 4-6: PARALLEL EXECUTION of Rules + AI + Obligations
        logger.info("Phase 4-6: Running parallel analysis (Rules + AI + Obligations)...")

        from shared.db import FindingRepository
        from shared.services.risk_profile_service import RiskProfileService

        # Extract contract value and currency from clauses
        extracted_value, extracted_currency = extract_contract_value_from_clauses(clauses)

        # Use extracted value or fall back to contract estimate
        contract_value = contract.contract_value_estimate or extracted_value
        contract_currency = extracted_currency or "USD"
        duration_years = calculate_contract_duration_years(contract)

        if contract_value:
            logger.info(f"Contract value for impact calculation: {contract_currency} {contract_value:,.2f}")
        else:
            logger.info("No contract value found - financial impact calculations will be skipped")
        logger.info(f"Contract duration: {duration_years} years")

        # Build dynamic risk profile for contract-specific calculations
        risk_profile = None
        if contract_value and contract_value > 0:
            logger.info("Building dynamic risk profile for contract...")
            risk_profile_service = RiskProfileService()
            risk_profile = risk_profile_service.build_profile(
                contract_id=contract_id,
                clauses=clauses,
                contract_value=contract_value,
                currency=contract_currency,
                duration_years=duration_years,
                start_date=contract.start_date,
                end_date=contract.end_date,
            )
            logger.info(
                f"Risk profile built: tier={risk_profile.value_tier}, "
                f"complexity={risk_profile.complexity_level}, "
                f"inflation={risk_profile.inflation_rate:.1%}, "
                f"multiplier={risk_profile.base_risk_multiplier:.2f}"
            )

        # Prepare contract metadata for detection
        contract_metadata = {
            "contract_value": contract_value or 0,
            "contract_currency": contract_currency,
            "duration_years": duration_years,
        }

        # Run all analysis tasks in PARALLEL
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            rule_findings, ai_findings, obligations_extracted = loop.run_until_complete(
                run_parallel_analysis(
                    contract_id=contract_id,
                    contract=contract,
                    clauses=clauses,
                    contract_metadata=contract_metadata,
                    risk_profile=risk_profile,
                )
            )
        finally:
            loop.close()

        # Combine all findings
        findings = list(rule_findings)
        findings.extend(ai_findings)

        # Store all findings in Cosmos DB
        finding_repo = FindingRepository(cosmos_client.findings_container)
        if findings:
            created_findings = finding_repo.bulk_create(findings)
            logger.info(f"Stored {len(created_findings)} total findings")

        # Calculate duration
        duration = time.time() - start_time
        contract_repo.set_processing_duration(contract_id, duration)

        # Update status to analyzed
        contract_repo.update_status(contract_id, ContractStatus.ANALYZED)

        logger.info(f"Analysis completed for contract {contract_id} in {duration:.2f}s")

        # Count findings by severity
        findings_by_severity = {
            "CRITICAL": len([f for f in findings if f.severity.upper() == "CRITICAL"]),
            "HIGH": len([f for f in findings if f.severity.upper() == "HIGH"]),
            "MEDIUM": len([f for f in findings if f.severity.upper() == "MEDIUM"]),
            "LOW": len([f for f in findings if f.severity.upper() == "LOW"]),
        }

        # Return response matching AnalyzeContractResponse type
        return func.HttpResponse(
            json.dumps(
                {
                    "message": "Analysis completed successfully",
                    "contract_id": contract_id,
                    "session_id": f"session_{contract_id}",
                    "total_clauses_extracted": len(clauses) if 'clauses' in dir() else 0,
                    "total_findings": len(findings),
                    "findings_by_severity": findings_by_severity,
                    "total_obligations_extracted": obligations_extracted,
                    "processing_time_seconds": round(duration, 2),
                }
            ),
            status_code=200,
            mimetype="application/json",
        )

    except DatabaseError as e:
        logger.error(f"Database error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Database error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Unexpected error in analyze_contract: {str(e)}", exc_info=True)

        # Try to update contract status to failed
        try:
            cosmos_client = get_cosmos_client()
            contract_repo = ContractRepository(cosmos_client.contracts_container)
            contract_repo.update_status(
                req.route_params.get("contract_id"),
                ContractStatus.FAILED,
                error_message=str(e),
            )
        except (DatabaseError, Exception) as update_error:
            logger.error(f"Failed to update contract status to failed: {update_error}")

        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
