"""Azure Function: Upload Contract

Handles contract file upload (PDF/DOCX) and creates initial contract record.
"""

import azure.functions as func
import json
import uuid
from datetime import datetime
from typing import Optional

from shared.models.contract import Contract, ContractSource, ContractStatus
from shared.db import get_cosmos_client, ContractRepository
from shared.utils.config import get_settings
from shared.utils.logging import setup_logging
from shared.utils.exceptions import (
    FileUploadError,
    UnsupportedFileTypeError,
    FileSizeExceededError,
    DatabaseError
)

logger = setup_logging(__name__)
settings = get_settings()


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Upload contract file and create initial contract record.

    Expected request:
    - Method: POST
    - Content-Type: multipart/form-data
    - Body: file (PDF/DOCX), optional metadata (contract_name, counterparty, etc.)

    Returns:
    - 201: Contract created successfully with contract_id
    - 400: Bad request (invalid file, missing data)
    - 413: File too large
    - 500: Server error
    """
    logger.info("upload_contract function triggered")

    try:
        # Get file from request
        file = req.files.get('file')
        if not file:
            logger.warning("No file provided in request")
            return func.HttpResponse(
                json.dumps({"error": "No file provided. Please upload a PDF or DOCX file."}),
                status_code=400,
                mimetype="application/json"
            )

        # Validate file type
        filename = file.filename
        file_extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        if file_extension not in settings.ALLOWED_FILE_EXTENSIONS:
            logger.warning(f"Unsupported file type: {file_extension}")
            return func.HttpResponse(
                json.dumps({
                    "error": f"Unsupported file type: .{file_extension}",
                    "allowed_types": settings.ALLOWED_FILE_EXTENSIONS
                }),
                status_code=400,
                mimetype="application/json"
            )

        # Read file content
        file_content = file.read()
        file_size = len(file_content)

        # Validate file size
        if file_size > settings.max_upload_size_bytes:
            logger.warning(f"File too large: {file_size} bytes")
            return func.HttpResponse(
                json.dumps({
                    "error": f"File too large. Maximum size: {settings.MAX_UPLOAD_SIZE_MB}MB",
                    "file_size_mb": round(file_size / (1024 * 1024), 2),
                    "max_size_mb": settings.MAX_UPLOAD_SIZE_MB
                }),
                status_code=413,
                mimetype="application/json"
            )

        logger.info(f"File validated: {filename} ({file_size} bytes)")

        # Get optional metadata from form data
        contract_name = req.form.get('contract_name', filename)
        counterparty = req.form.get('counterparty')
        start_date = req.form.get('start_date')
        end_date = req.form.get('end_date')
        contract_value = req.form.get('contract_value')

        # Generate contract ID
        contract_id = f"contract_{uuid.uuid4().hex[:12]}"

        # Create contract record
        contract = Contract(
            id=contract_id,
            contract_id=contract_id,
            contract_name=contract_name,
            source=ContractSource.UPLOAD,
            file_type=file_extension,
            counterparty=counterparty,
            start_date=start_date,
            end_date=end_date,
            contract_value_estimate=float(contract_value) if contract_value else None,
            status=ContractStatus.UPLOADED,
            partition_key=contract_id
        )

        # Save to Cosmos DB
        cosmos_client = get_cosmos_client()
        contract_repo = ContractRepository(cosmos_client.contracts_container)

        created_contract = contract_repo.create(contract)

        logger.info(f"Contract created successfully: {contract_id}")

        # Upload file to Azure Blob Storage and extract text
        from shared.services.document_service import DocumentService

        try:
            document_service = DocumentService()
            processing_result = document_service.process_uploaded_contract(
                file_content,
                contract_id,
                filename,
                file_extension,
                req.files.get('file').content_type
            )

            logger.info(f"Document processing completed: {processing_result['metadata']}")
        except Exception as doc_error:
            logger.error(f"Document processing failed: {str(doc_error)}")
            # Contract created but processing failed - still return success
            # User can retry analysis later

        # Return success response
        return func.HttpResponse(
            json.dumps({
                "message": "Contract uploaded successfully",
                "contract_id": contract_id,
                "contract_name": contract_name,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "status": created_contract.status
            }),
            status_code=201,
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
        logger.error(f"Unexpected error in upload_contract: {str(e)}", exc_info=True)
        return func.HttpResponse(
            json.dumps({"error": "An unexpected error occurred", "details": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
