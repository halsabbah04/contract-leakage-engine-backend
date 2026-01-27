"""Azure Function: List Contracts

List all contracts with optional filtering.
"""

import json

import azure.functions as func

from shared.db import ContractRepository, get_cosmos_client
from shared.models.contract import ContractStatus
from shared.utils.exceptions import DatabaseError
from shared.utils.logging import setup_logging

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
        status_param = req.params.get("status")
        limit = int(req.params.get("limit", "50"))

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
                    json.dumps(
                        {
                            "error": f"Invalid status: {status_param}",
                            "valid_statuses": [s.value for s in ContractStatus],
                        }
                    ),
                    status_code=400,
                    mimetype="application/json",
                )
        else:
            contracts = contract_repo.get_recent_contracts(limit)

        logger.info(f"Found {len(contracts)} contracts")

        # Build response with all contract fields needed by frontend
        response_data = {
            "contracts": [
                {
                    "id": c.id,
                    "type": c.type,
                    "contract_id": c.contract_id,
                    "contract_name": c.contract_name,
                    "status": c.status.value if hasattr(c.status, "value") else c.status,
                    "source": c.source.value if hasattr(c.source, "value") else c.source,
                    "file_type": c.file_type,
                    "language": c.language,
                    "counterparty": c.counterparty,
                    "start_date": c.start_date.isoformat() if c.start_date else None,
                    "end_date": c.end_date.isoformat() if c.end_date else None,
                    "contract_value_estimate": c.contract_value_estimate,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                    "upload_date": c.upload_date.isoformat() if c.upload_date else None,
                    "partition_key": c.partition_key,
                    "blob_uri": c.blob_uri,
                    "extracted_text_uri": c.extracted_text_uri,
                    "clause_ids": c.clause_ids,
                    "error_message": c.error_message,
                    "processing_duration_seconds": c.processing_duration_seconds,
                }
                for c in contracts[:limit]
            ],
            "total_count": len(contracts),
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
        logger.error(f"Unexpected error in list_contracts: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
