"""Azure Function: Get Contract Document

Generate a temporary SAS URL for viewing the original uploaded contract document.
"""

import json

import azure.functions as func

from shared.db import ContractRepository, get_cosmos_client
from shared.services.storage_service import StorageService
from shared.utils.exceptions import ContractNotFoundError, StorageError
from shared.utils.logging import setup_logging

logger = setup_logging(__name__)


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Get a temporary URL to view the original contract document.

    Route: GET /api/get_document/{contract_id}
    Query Parameters:
        - expiry_hours: Hours until URL expires (default: 1, max: 24)

    Returns:
    - 200: JSON with document URL
    - 404: Contract not found or no document available
    - 500: Server error
    """
    logger.info("get_document function triggered")

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

        # Get expiry hours from query params (default 1 hour, max 24)
        try:
            expiry_hours = int(req.params.get("expiry_hours", "1"))
            expiry_hours = min(max(expiry_hours, 1), 24)  # Clamp between 1-24
        except ValueError:
            expiry_hours = 1

        logger.info(f"Getting document URL for contract: {contract_id} (expiry: {expiry_hours}h)")

        # Get contract from Cosmos DB
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)
        contract = contract_repo.get_by_contract_id(contract_id)

        if not contract:
            logger.warning(f"Contract not found: {contract_id}")
            return func.HttpResponse(
                json.dumps({"error": f"Contract '{contract_id}' not found"}),
                status_code=404,
                mimetype="application/json",
            )

        # Check if contract has a blob_uri
        if not contract.blob_uri:
            logger.warning(f"Contract has no document: {contract_id}")
            return func.HttpResponse(
                json.dumps({"error": "Contract document not available"}),
                status_code=404,
                mimetype="application/json",
            )

        # Generate SAS URL for temporary access
        storage_service = StorageService()
        sas_url = storage_service.generate_sas_url(contract.blob_uri, expiry_hours=expiry_hours)

        logger.info(f"Document URL generated for contract {contract_id}")

        return func.HttpResponse(
            json.dumps({
                "contract_id": contract_id,
                "document_url": sas_url,
                "filename": contract.original_filename or "contract",
                "content_type": contract.file_type or "application/octet-stream",
                "expires_in_hours": expiry_hours,
            }),
            status_code=200,
            mimetype="application/json",
        )

    except ContractNotFoundError as e:
        logger.error(f"Contract not found: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=404,
            mimetype="application/json",
        )

    except StorageError as e:
        logger.error(f"Storage error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to generate document URL", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )

    except Exception as e:
        logger.error(f"Unexpected error in get_document: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json",
        )
