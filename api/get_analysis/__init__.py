"""Azure Function: Get Analysis

Retrieve complete analysis results for a contract including clauses and findings.
"""

import azure.functions as func
import json
from typing import Optional

from shared.models.contract import Contract
from shared.models.clause import Clause
from shared.models.finding import LeakageFinding
from shared.models.session import AnalysisSession
from shared.db import get_cosmos_client, ContractRepository, ClauseRepository, FindingRepository, SessionRepository
from shared.utils.logging import setup_logging
from shared.utils.exceptions import ContractNotFoundError, DatabaseError

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get complete analysis results for a contract.

    Route: GET /api/get_analysis/{contract_id}

    Returns:
    - 200: Analysis results including contract, clauses, findings, and session
    - 404: Contract not found
    - 500: Server error
    """
    logger.info("get_analysis function triggered")

    try:
        # Get contract_id from route parameter
        contract_id = req.route_params.get('contract_id')

        if not contract_id:
            logger.warning("No contract_id provided")
            return func.HttpResponse(
                json.dumps({"error": "contract_id is required"}),
                status_code=400,
                mimetype="application/json"
            )

        logger.info(f"Fetching analysis for contract: {contract_id}")

        # Initialize repositories
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)
        clause_repo = ClauseRepository(cosmos_client.clauses_container)
        finding_repo = FindingRepository(cosmos_client.findings_container)
        session_repo = SessionRepository(cosmos_client.sessions_container)

        # Get contract
        contract = contract_repo.get_by_contract_id(contract_id)
        if not contract:
            logger.warning(f"Contract not found: {contract_id}")
            return func.HttpResponse(
                json.dumps({"error": f"Contract '{contract_id}' not found"}),
                status_code=404,
                mimetype="application/json"
            )

        # Get clauses
        clauses = clause_repo.get_by_contract_id(contract_id)
        logger.info(f"Found {len(clauses)} clauses")

        # Get active findings
        findings = finding_repo.get_active_findings(contract_id)
        logger.info(f"Found {len(findings)} active findings")

        # Get session (if exists)
        session = session_repo.get_by_contract_id(contract_id)

        # Build response
        response_data = {
            "contract": contract.model_dump(mode='json'),
            "clauses": [clause.model_dump(mode='json', exclude={'embedding'}) for clause in clauses],
            "findings": [finding.model_dump(mode='json', exclude={'embedding'}) for finding in findings],
            "session": session.model_dump(mode='json') if session else None,
            "summary": {
                "total_clauses": len(clauses),
                "total_findings": len(findings),
                "active_findings": len([f for f in findings if not f.user_dismissed]),
                "critical_findings": len([f for f in findings if f.severity == 'critical']),
                "high_findings": len([f for f in findings if f.severity == 'high']),
                "total_estimated_impact": sum([
                    f.estimated_impact.value for f in findings
                    if f.estimated_impact.value is not None and not f.user_dismissed
                ], 0.0)
            }
        }

        logger.info(f"Successfully retrieved analysis for contract {contract_id}")

        return func.HttpResponse(
            json.dumps(response_data, default=str),
            status_code=200,
            mimetype="application/json"
        )

    except DatabaseError as e:
        logger.error(f"Database error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Database error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )

    except Exception as e:
        logger.error(f"Unexpected error in get_analysis: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
