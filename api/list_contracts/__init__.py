"""Azure Function: List Contracts

List all contracts with optional filtering.
"""

import azure.functions as func
import json

from shared.models.contract import ContractStatus
from shared.db import get_cosmos_client, ContractRepository
from shared.utils.logging import setup_logging
from shared.utils.exceptions import DatabaseError

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    List contracts with optional filtering.

    Route: GET /api/list_contracts

    Query parameters:
    - status: Filter by status (optional)
    - limit: Maximum number of results (default: 50)

    Returns:
    - 200: List of contracts
    - 500: Server error
    """
    logger.info("list_contracts function triggered")

    try:
        # Get query parameters
        status_param = req.params.get('status')
        limit = int(req.params.get('limit', '50'))

        logger.info(f"Listing contracts (status={status_param}, limit={limit})")

        # Initialize repository
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)

        # Get contracts
        if status_param:
            try:
                status = ContractStatus(status_param)
                contracts = contract_repo.get_by_status(status)
            except ValueError:
                return func.HttpResponse(
                    json.dumps({
                        "error": f"Invalid status: {status_param}",
                        "valid_statuses": [s.value for s in ContractStatus]
                    }),
                    status_code=400,
                    mimetype="application/json"
                )
        else:
            contracts = contract_repo.get_recent_contracts(limit)

        logger.info(f"Found {len(contracts)} contracts")

        # Build response
        response_data = {
            "contracts": [
                {
                    "contract_id": c.contract_id,
                    "contract_name": c.contract_name,
                    "status": c.status,
                    "source": c.source,
                    "counterparty": c.counterparty,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "contract_value_estimate": c.contract_value_estimate
                }
                for c in contracts[:limit]
            ],
            "total": len(contracts),
            "filters": {
                "status": status_param,
                "limit": limit
            }
        }

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
        logger.error(f"Unexpected error in list_contracts: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
