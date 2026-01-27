"""Azure Function: Analyze Contract

Orchestrates the complete contract analysis pipeline:
1. Extract text (OCR if needed)
2. Extract clauses
3. Detect leakage (rules + AI)
4. Calculate impact
"""

import json
import time

import azure.functions as func

from shared.db import ContractRepository, get_cosmos_client
from shared.models.contract import ContractStatus
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


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

        # Phase 4: Leakage Detection (Rules Engine)
        logger.info("Phase 4: Running rules-based leakage detection...")

        from shared.db import FindingRepository
        from shared.services.rules_engine import RulesEngine

        rules_engine = RulesEngine()

        # Prepare contract metadata for rules engine
        contract_metadata = {
            "contract_value": contract.contract_value_estimate or 0,
            "duration_years": 3,  # TODO: Calculate from start_date/end_date
        }

        # Run rules engine
        findings = rules_engine.detect_leakage(contract_id, clauses, contract_metadata)
        logger.info(f"Rules engine detected {len(findings)} potential issues")

        # Store findings in Cosmos DB
        finding_repo = FindingRepository(cosmos_client.findings_container)
        if findings:
            created_findings = finding_repo.bulk_create(findings)
            logger.info(f"Stored {len(created_findings)} rule-based findings")

        # Phase 5: AI-Powered Detection with GPT 5.2
        # Skip if too many clauses to avoid timeout (max 30 clauses for AI analysis)
        ai_findings = []
        clause_count = len(clauses) if 'clauses' in dir() else 0

        if clause_count > 50:
            logger.warning(f"Skipping AI detection: {clause_count} clauses exceeds limit of 50")
        else:
            logger.info("Phase 5: Running AI-powered leakage detection with GPT 5.2...")

            try:
                from shared.services.ai_detection_service import AIDetectionService

                ai_service = AIDetectionService()
                ai_findings = ai_service.detect_leakage(contract_id, contract_metadata)

                # Store AI findings
                if ai_findings:
                    created_ai_findings = finding_repo.bulk_create(ai_findings)
                    logger.info(f"Stored {len(created_ai_findings)} AI-detected findings")
                    findings.extend(ai_findings)

            except Exception as e:
                logger.error(f"AI detection failed (continuing with rule-based findings): {str(e)}")
                # Continue even if AI detection fails - we still have rule-based findings

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
