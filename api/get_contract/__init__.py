"""Azure Function: Get Contract

Retrieve contract details by ID.
"""

import json

import azure.functions as func

from shared.db import ContractRepository, get_cosmos_client
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get contract details by ID.

    Route: GET /api/get_contract/{contract_id}

    Returns:
    - 200: Contract details
    - 400: Missing contract_id
    - 404: Contract not found
    - 500: Server error
    """
    logger.info("get_contract function triggered")

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

        logger.info(f"Fetching contract: {contract_id}")

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

        logger.info(f"Successfully retrieved contract {contract_id}")

        # Return response matching GetContractResponse type
        return func.HttpResponse(
            json.dumps({"contract": contract.model_dump(mode="json")}, default=str),
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
        logger.error(f"Unexpected error in get_contract: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
