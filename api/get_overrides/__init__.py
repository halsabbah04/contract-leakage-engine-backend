"""Azure Function: Get Overrides

Retrieve all user overrides for a contract or specific finding.
"""

import json

import azure.functions as func

from shared.db import OverrideRepository, get_cosmos_client
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get all overrides for a contract, optionally filtered by finding_id.

    Route: GET /api/overrides/{contract_id}?finding_id=<optional>

    Query parameters:
    - finding_id (optional): Filter overrides by specific finding

    Returns:
    - 200: List of overrides
    - 400: Invalid request
    - 500: Server error
    """
    logger.info("get_overrides function triggered")

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

        # Get optional finding_id query parameter
        finding_id = req.params.get("finding_id")

        logger.info(f"Fetching overrides for contract: {contract_id}")
        if finding_id:
            logger.info(f"Filtering by finding_id: {finding_id}")

        # Initialize repository
        cosmos_client = get_cosmos_client()
        override_repo = OverrideRepository(cosmos_client.overrides_container)

        # Get overrides
        if finding_id:
            overrides = override_repo.get_by_finding(contract_id, finding_id)
        else:
            overrides = override_repo.get_by_contract(contract_id)

        logger.info(f"Found {len(overrides)} overrides")

        # Build response
        response_data = {
            "contract_id": contract_id,
            "overrides": [override.model_dump(mode="json") for override in overrides],
            "total_count": len(overrides),
        }

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
        logger.error(f"Unexpected error in get_overrides: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
