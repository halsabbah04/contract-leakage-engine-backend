"""Azure Function: Get Findings

Retrieve leakage findings for a contract.
"""

import json

import azure.functions as func

from shared.db import ContractRepository, FindingRepository, get_cosmos_client
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get findings for a contract with optional filtering.

    Route: GET /api/get_findings/{contract_id}

    Query Parameters:
    - severity: Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)
    - category: Filter by category
    - limit: Maximum number of findings to return
    - offset: Number of findings to skip (for pagination)

    Returns:
    - 200: Findings list with summary
    - 400: Missing contract_id
    - 404: Contract not found
    - 500: Server error
    """
    logger.info("get_findings function triggered")

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

        # Get optional query parameters
        severity = req.params.get("severity")
        category = req.params.get("category")
        limit_str = req.params.get("limit")
        offset_str = req.params.get("offset")

        limit = int(limit_str) if limit_str else None
        offset = int(offset_str) if offset_str else None

        logger.info(f"Fetching findings for contract: {contract_id}")

        # Initialize repositories
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)
        finding_repo = FindingRepository(cosmos_client.findings_container)

        # Verify contract exists
        contract = contract_repo.get_by_contract_id(contract_id)
        if not contract:
            logger.warning(f"Contract not found: {contract_id}")
            return func.HttpResponse(
                json.dumps({"error": f"Contract '{contract_id}' not found"}),
                status_code=404,
                mimetype="application/json",
            )

        # Get active findings
        findings = finding_repo.get_active_findings(contract_id)
        logger.info(f"Found {len(findings)} active findings")

        # Apply filtering
        if severity:
            findings = [f for f in findings if f.severity.upper() == severity.upper()]
        if category:
            findings = [f for f in findings if f.leakage_category == category]

        total_count = len(findings)

        # Calculate summary before pagination
        summary = {
            "total_findings": total_count,
            "by_severity": {
                "CRITICAL": len([f for f in findings if f.severity.upper() == "CRITICAL"]),
                "HIGH": len([f for f in findings if f.severity.upper() == "HIGH"]),
                "MEDIUM": len([f for f in findings if f.severity.upper() == "MEDIUM"]),
                "LOW": len([f for f in findings if f.severity.upper() == "LOW"]),
            },
            "by_category": {},
        }

        # Count by category
        for finding in findings:
            cat = finding.leakage_category
            if cat not in summary["by_category"]:
                summary["by_category"][cat] = 0
            summary["by_category"][cat] += 1

        # Calculate total estimated impact and determine currency from findings
        findings_with_impact = [
            f for f in findings
            if f.estimated_impact and f.estimated_impact.value is not None and f.estimated_impact.value > 0
        ]

        if findings_with_impact:
            total_impact = sum(f.estimated_impact.value for f in findings_with_impact)
            # Use currency from first finding with impact
            currency = findings_with_impact[0].estimated_impact.currency or "USD"
            summary["total_estimated_impact"] = {
                "amount": total_impact,
                "currency": currency,
            }
        else:
            # No financial impact calculated - don't include in summary
            summary["total_estimated_impact"] = {
                "amount": 0,
                "currency": "USD",
            }

        # Apply pagination
        if offset:
            findings = findings[offset:]
        if limit:
            findings = findings[:limit]

        logger.info(f"Returning {len(findings)} findings (total: {total_count})")

        # Return response matching GetFindingsResponse type
        response_data = {
            "contract_id": contract_id,
            "findings": [finding.model_dump(mode="json", exclude={"embedding"}) for finding in findings],
            "total_count": total_count,
            "summary": summary,
        }

        if limit:
            response_data["limit"] = limit
        if offset:
            response_data["offset"] = offset

        return func.HttpResponse(
            json.dumps(response_data, default=str),
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
        logger.error(f"Unexpected error in get_findings: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
