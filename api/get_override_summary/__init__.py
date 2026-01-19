"""Azure Function: Get Override Summary

Retrieve aggregate statistics of user overrides for a contract.
"""

import json

import azure.functions as func

from shared.db import OverrideRepository, get_cosmos_client
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get override summary statistics for a contract.

    Route: GET /api/overrides/{contract_id}/summary

    Returns:
    - 200: Override summary with counts by action type
    - 400: Invalid request
    - 500: Server error
    """
    logger.info("get_override_summary function triggered")

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

        logger.info(f"Fetching override summary for contract: {contract_id}")

        # Initialize repository
        cosmos_client = get_cosmos_client()
        override_repo = OverrideRepository(cosmos_client.overrides_container)

        # Get summary
        summary = override_repo.get_summary(contract_id)

        logger.info(f"Summary generated: {summary.total_overrides} total overrides")

        # Build response
        response_data = {
            "contract_id": contract_id,
            "summary": summary.model_dump(mode="json"),
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
        logger.error(f"Unexpected error in get_override_summary: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
