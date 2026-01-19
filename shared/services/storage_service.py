"""Azure Blob Storage service for contract file storage."""

from datetime import datetime, timedelta
from typing import Optional

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobClient, BlobSasPermissions, BlobServiceClient, ContentSettings, generate_blob_sas

from ..utils.config import get_settings
from ..utils.exceptions import StorageError
from ..utils.logging import setup_logging

logger = setup_logging(__name__)
settings = get_settings()


class StorageService:
    """Service for Azure Blob Storage operations."""

    def __init__(self):
        """Initialize storage service."""
        try:
            self.blob_service_client = BlobServiceClient.from_connection_string(settings.STORAGE_CONNECTION_STRING)
            self.container_name = settings.STORAGE_CONTAINER_NAME
            logger.info(f"Storage service initialized for container: {self.container_name}")
        except Exception as e:
            logger.error(f"Failed to initialize storage service: {str(e)}")
            raise StorageError(f"Failed to initialize Azure Blob Storage: {str(e)}")

    def upload_contract_file(
        self,
        file_content: bytes,
        contract_id: str,
        filename: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a contract file to blob storage.

        Args:
            file_content: File content as bytes
            contract_id: Contract identifier (used in blob path)
            filename: Original filename
            content_type: MIME type of the file

        Returns:
            Blob URI (URL to the uploaded file)

        Raises:
            StorageError: If upload fails
        """
        try:
            # Generate blob name: contracts/{contract_id}/original/{filename}
            blob_name = f"contracts/{contract_id}/original/{filename}"

            logger.info(f"Uploading file to blob: {blob_name}")

            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)

            # Set content settings
            content_settings = None
            if content_type:
                content_settings = ContentSettings(content_type=content_type)

            # Upload file
            blob_client.upload_blob(
                file_content,
                overwrite=True,
                content_settings=content_settings,
                metadata={
                    "contract_id": contract_id,
                    "original_filename": filename,
                    "upload_timestamp": datetime.utcnow().isoformat(),
                },
            )

            # Get blob URL
            blob_url = blob_client.url

            logger.info(f"File uploaded successfully: {blob_url}")
            return blob_url

        except ResourceExistsError:
            logger.warning(f"Blob already exists, overwriting: {blob_name}")
            return blob_client.url

        except Exception as e:
            logger.error(f"Failed to upload file to blob storage: {str(e)}")
            raise StorageError(f"Failed to upload file: {str(e)}")

    def upload_extracted_text(self, text_content: str, contract_id: str, filename: str = "extracted_text.txt") -> str:
        """
        Upload extracted text to blob storage.

        Args:
            text_content: Extracted text content
            contract_id: Contract identifier
            filename: Name for the text file

        Returns:
            Blob URI

        Raises:
            StorageError: If upload fails
        """
        try:
            # Generate blob name: contracts/{contract_id}/extracted/{filename}
            blob_name = f"contracts/{contract_id}/extracted/{filename}"

            logger.info(f"Uploading extracted text to blob: {blob_name}")

            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)

            # Convert text to bytes
            text_bytes = text_content.encode("utf-8")

            # Upload
            blob_client.upload_blob(
                text_bytes,
                overwrite=True,
                content_settings=ContentSettings(content_type="text/plain"),
                metadata={
                    "contract_id": contract_id,
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                    "character_count": str(len(text_content)),
                },
            )

            blob_url = blob_client.url
            logger.info(f"Extracted text uploaded: {blob_url}")
            return blob_url

        except Exception as e:
            logger.error(f"Failed to upload extracted text: {str(e)}")
            raise StorageError(f"Failed to upload extracted text: {str(e)}")

    def download_blob(self, blob_url: str) -> bytes:
        """
        Download blob content by URL.

        Args:
            blob_url: Full blob URL

        Returns:
            Blob content as bytes

        Raises:
            StorageError: If download fails
        """
        try:
            logger.info(f"Downloading blob: {blob_url}")

            # Create blob client from URL
            blob_client = BlobClient.from_blob_url(blob_url)

            # Download
            blob_data = blob_client.download_blob()
            content = blob_data.readall()

            logger.info(f"Blob downloaded: {len(content)} bytes")
            return content

        except ResourceNotFoundError:
            logger.error(f"Blob not found: {blob_url}")
            raise StorageError(f"Blob not found: {blob_url}")

        except Exception as e:
            logger.error(f"Failed to download blob: {str(e)}")
            raise StorageError(f"Failed to download blob: {str(e)}")

    def download_blob_text(self, blob_url: str) -> str:
        """
        Download blob content as text.

        Args:
            blob_url: Full blob URL

        Returns:
            Blob content as string

        Raises:
            StorageError: If download fails
        """
        try:
            content_bytes = self.download_blob(blob_url)
            return content_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            logger.error(f"Failed to decode blob as UTF-8: {str(e)}")
            raise StorageError(f"Blob content is not valid UTF-8 text: {str(e)}")

    def generate_sas_url(self, blob_url: str, expiry_hours: int = 24) -> str:
        """
        Generate a SAS URL for temporary access to a blob.

        Args:
            blob_url: Full blob URL
            expiry_hours: Hours until SAS token expires

        Returns:
            SAS URL with token

        Raises:
            StorageError: If SAS generation fails
        """
        try:
            logger.info(f"Generating SAS URL for blob (expiry: {expiry_hours}h)")

            # Create blob client from URL
            blob_client = BlobClient.from_blob_url(blob_url)

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=blob_client.container_name,
                blob_name=blob_client.blob_name,
                account_key=settings.STORAGE_CONNECTION_STRING.split("AccountKey=")[1].split(";")[0],
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours),
            )

            # Construct SAS URL
            sas_url = f"{blob_url}?{sas_token}"

            logger.info("SAS URL generated successfully")
            return sas_url

        except Exception as e:
            logger.error(f"Failed to generate SAS URL: {str(e)}")
            raise StorageError(f"Failed to generate SAS URL: {str(e)}")

    def delete_blob(self, blob_url: str) -> bool:
        """
        Delete a blob.

        Args:
            blob_url: Full blob URL

        Returns:
            True if deleted successfully

        Raises:
            StorageError: If deletion fails
        """
        try:
            logger.info(f"Deleting blob: {blob_url}")

            blob_client = BlobClient.from_blob_url(blob_url)
            blob_client.delete_blob()

            logger.info("Blob deleted successfully")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Blob not found (already deleted?): {blob_url}")
            return False

        except Exception as e:
            logger.error(f"Failed to delete blob: {str(e)}")
            raise StorageError(f"Failed to delete blob: {str(e)}")

    def list_contract_blobs(self, contract_id: str) -> list[dict]:
        """
        List all blobs for a specific contract.

        Args:
            contract_id: Contract identifier

        Returns:
            List of blob metadata dictionaries
        """
        try:
            logger.info(f"Listing blobs for contract: {contract_id}")

            container_client = self.blob_service_client.get_container_client(self.container_name)

            # List blobs with prefix
            prefix = f"contracts/{contract_id}/"
            blobs = container_client.list_blobs(name_starts_with=prefix)

            blob_list = []
            for blob in blobs:
                blob_list.append(
                    {
                        "name": blob.name,
                        "url": f"{container_client.url}/{blob.name}",
                        "size": blob.size,
                        "created": blob.creation_time,
                        "modified": blob.last_modified,
                        "content_type": (blob.content_settings.content_type if blob.content_settings else None),
                    }
                )

            logger.info(f"Found {len(blob_list)} blobs for contract {contract_id}")
            return blob_list

        except Exception as e:
            logger.error(f"Failed to list blobs: {str(e)}")
            raise StorageError(f"Failed to list blobs: {str(e)}")
