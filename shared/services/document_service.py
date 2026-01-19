"""Document ingestion orchestration service.

Coordinates file upload, storage, and text extraction.
"""

from datetime import datetime
from typing import Optional

from ..db import ContractRepository, get_cosmos_client
from ..models.contract import ContractStatus
from ..utils.exceptions import DocumentProcessingError, OCRError, StorageError
from ..utils.logging import setup_logging
from .ocr_service import OCRService
from .storage_service import StorageService

logger = setup_logging(__name__)


class DocumentService:
    """Service for document ingestion and processing."""

    def __init__(self):
        """Initialize document service."""
        self.storage_service = StorageService()
        self.ocr_service = OCRService()
        logger.info("Document service initialized")

    def process_uploaded_contract(
        self,
        file_content: bytes,
        contract_id: str,
        filename: str,
        file_type: str,
        content_type: Optional[str] = None,
    ) -> dict:
        """
        Process an uploaded contract file.

        Steps:
        1. Upload file to Blob Storage
        2. Extract text using OCR (if needed)
        3. Store extracted text
        4. Update contract record

        Args:
            file_content: File content as bytes
            contract_id: Contract identifier
            filename: Original filename
            file_type: File extension (pdf, docx)
            content_type: MIME type

        Returns:
            Dict with blob_uri, extracted_text_uri, metadata

        Raises:
            DocumentProcessingError: If processing fails
        """
        try:
            logger.info(f"Processing contract {contract_id}: {filename}")

            # Initialize Cosmos DB repo
            cosmos_client = get_cosmos_client()
            contract_repo = ContractRepository(cosmos_client.contracts_container)

            # Step 1: Upload original file to blob storage
            logger.info("Step 1: Uploading file to blob storage...")
            contract_repo.update_status(contract_id, ContractStatus.UPLOADED)

            blob_uri = self.storage_service.upload_contract_file(file_content, contract_id, filename, content_type)

            # Update contract with blob URI
            contract_repo.set_blob_uri(contract_id, blob_uri)

            logger.info(f"File uploaded: {blob_uri}")

            # Step 2: Extract text using OCR
            logger.info("Step 2: Extracting text...")
            contract_repo.update_status(contract_id, ContractStatus.EXTRACTING_TEXT)

            extracted_text, ocr_metadata = self.ocr_service.extract_text(file_content, filename, file_type)

            logger.info(
                f"Text extracted: {ocr_metadata['character_count']} chars, "
                f"{ocr_metadata['page_count']} pages, "
                f"confidence: {ocr_metadata.get('confidence', 0):.2f}"
            )

            # Step 3: Store extracted text
            logger.info("Step 3: Storing extracted text...")

            extracted_text_uri = self.storage_service.upload_extracted_text(
                extracted_text,
                contract_id,
                f"extracted_text_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.txt",
            )

            logger.info(f"Extracted text stored: {extracted_text_uri}")

            # Step 4: Update contract status
            contract_repo.update_status(contract_id, ContractStatus.TEXT_EXTRACTED)

            # Return processing results
            result = {
                "contract_id": contract_id,
                "blob_uri": blob_uri,
                "extracted_text_uri": extracted_text_uri,
                "extracted_text": extracted_text,  # Include for next steps
                "metadata": {
                    "page_count": ocr_metadata.get("page_count", 0),
                    "character_count": ocr_metadata.get("character_count", 0),
                    "word_count": ocr_metadata.get("word_count", 0),
                    "language": ocr_metadata.get("language", "unknown"),
                    "confidence": ocr_metadata.get("confidence", 0.0),
                    "extraction_method": "azure_document_intelligence",
                },
            }

            logger.info(f"Document processing completed for contract {contract_id}")
            return result

        except StorageError as e:
            logger.error(f"Storage error during document processing: {str(e)}")
            self._mark_contract_failed(contract_id, f"Storage error: {str(e)}")
            raise DocumentProcessingError(f"Storage error: {str(e)}")

        except OCRError as e:
            logger.error(f"OCR error during document processing: {str(e)}")
            self._mark_contract_failed(contract_id, f"OCR error: {str(e)}")
            raise DocumentProcessingError(f"OCR error: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error during document processing: {str(e)}")
            self._mark_contract_failed(contract_id, f"Unexpected error: {str(e)}")
            raise DocumentProcessingError(f"Document processing failed: {str(e)}")

    def get_extracted_text(self, contract_id: str) -> Optional[str]:
        """
        Retrieve extracted text for a contract.

        Args:
            contract_id: Contract identifier

        Returns:
            Extracted text if available, None otherwise

        Raises:
            DocumentProcessingError: If retrieval fails
        """
        try:
            logger.info(f"Retrieving extracted text for contract {contract_id}")

            # Get contract to find extracted text URI
            cosmos_client = get_cosmos_client()
            contract_repo = ContractRepository(cosmos_client.contracts_container)

            contract = contract_repo.get_by_contract_id(contract_id)
            if not contract:
                raise DocumentProcessingError(f"Contract {contract_id} not found")

            if not contract.extracted_text_uri:
                logger.warning(f"No extracted text URI for contract {contract_id}")
                return None

            # Download extracted text
            extracted_text = self.storage_service.download_blob_text(contract.extracted_text_uri)

            logger.info(f"Retrieved extracted text: {len(extracted_text)} characters")
            return extracted_text

        except StorageError as e:
            logger.error(f"Storage error retrieving text: {str(e)}")
            raise DocumentProcessingError(f"Failed to retrieve extracted text: {str(e)}")

        except Exception as e:
            logger.error(f"Unexpected error retrieving text: {str(e)}")
            raise DocumentProcessingError(f"Failed to retrieve extracted text: {str(e)}")

    def reprocess_contract(self, contract_id: str) -> dict:
        """
        Re-process a contract (re-run OCR).

        Args:
            contract_id: Contract identifier

        Returns:
            Processing results

        Raises:
            DocumentProcessingError: If reprocessing fails
        """
        try:
            logger.info(f"Re-processing contract {contract_id}")

            # Get contract
            cosmos_client = get_cosmos_client()
            contract_repo = ContractRepository(cosmos_client.contracts_container)

            contract = contract_repo.get_by_contract_id(contract_id)
            if not contract:
                raise DocumentProcessingError(f"Contract {contract_id} not found")

            if not contract.blob_uri:
                raise DocumentProcessingError(f"No source file for contract {contract_id}")

            # Download original file
            file_content = self.storage_service.download_blob(contract.blob_uri)

            # Re-process
            file_type = contract.file_type if contract.file_type else "pdf"
            return self.process_uploaded_contract(
                file_content,
                contract_id,
                contract.contract_name,
                file_type,
                None,
            )

        except Exception as e:
            logger.error(f"Error during reprocessing: {str(e)}")
            raise DocumentProcessingError(f"Failed to reprocess contract: {str(e)}")

    def _mark_contract_failed(self, contract_id: str, error_message: str):
        """Mark contract as failed (best effort)."""
        try:
            cosmos_client = get_cosmos_client()
            contract_repo = ContractRepository(cosmos_client.contracts_container)
            contract_repo.update_status(contract_id, ContractStatus.FAILED, error_message)
        except Exception as e:
            logger.error(f"Failed to mark contract as failed: {str(e)}")
