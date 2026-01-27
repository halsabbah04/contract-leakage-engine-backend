"""Azure Function: Get Clauses

Retrieve extracted clauses for a contract.
"""

import json

import azure.functions as func

from shared.db import ClauseRepository, ContractRepository, get_cosmos_client
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get clauses for a contract with optional filtering.

    Route: GET /api/get_clauses/{contract_id}

    Query Parameters:
    - clause_type: Filter by clause type
    - limit: Maximum number of clauses to return
    - offset: Number of clauses to skip (for pagination)

    Returns:
    - 200: Clauses list with metadata
    - 400: Missing contract_id
    - 404: Contract not found
    - 500: Server error
    """
    logger.info("get_clauses function triggered")

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
        clause_type = req.params.get("clause_type")
        limit_str = req.params.get("limit")
        offset_str = req.params.get("offset")

        limit = int(limit_str) if limit_str else None
        offset = int(offset_str) if offset_str else None

        logger.info(f"Fetching clauses for contract: {contract_id}")

        # Initialize repositories
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)
        clause_repo = ClauseRepository(cosmos_client.clauses_container)

        # Verify contract exists
        contract = contract_repo.get_by_contract_id(contract_id)
        if not contract:
            logger.warning(f"Contract not found: {contract_id}")
            return func.HttpResponse(
                json.dumps({"error": f"Contract '{contract_id}' not found"}),
                status_code=404,
                mimetype="application/json",
            )

        # Get clauses
        clauses = clause_repo.get_by_contract_id(contract_id)
        logger.info(f"Found {len(clauses)} clauses")

        # Apply filtering
        if clause_type:
            clauses = [c for c in clauses if c.clause_type == clause_type]

        total_count = len(clauses)

        # Apply pagination
        if offset:
            clauses = clauses[offset:]
        if limit:
            clauses = clauses[:limit]

        logger.info(f"Returning {len(clauses)} clauses (total: {total_count})")

        # Return response matching GetClausesResponse type
        response_data = {
            "contract_id": contract_id,
            "clauses": [clause.model_dump(mode="json", exclude={"embedding"}) for clause in clauses],
            "total_count": total_count,
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
        logger.error(f"Unexpected error in get_clauses: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
