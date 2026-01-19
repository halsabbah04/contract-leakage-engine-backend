"""Repository for Contract operations."""

from datetime import datetime
from typing import List, Optional

from ...models.contract import Contract, ContractStatus
from ...utils.logging import setup_logging
from .base_repository import BaseRepository

logger = setup_logging(__name__)


class ContractRepository(BaseRepository[Contract]):
    """Repository for Contract CRUD operations."""

    def __init__(self, container):
        """Initialize contract repository."""
        super().__init__(container, Contract)

    def get_by_contract_id(self, contract_id: str) -> Optional[Contract]:
        """
        Get contract by contract_id.

        Args:
            contract_id: Contract identifier

        Returns:
            Contract if found, None otherwise
        """
        # contract_id is both the ID and partition key
        return self.read(contract_id, contract_id)

    def update_status(
        self,
        contract_id: str,
        status: ContractStatus,
        error_message: Optional[str] = None,
    ) -> Contract:
        """
        Update contract processing status.

        Args:
            contract_id: Contract identifier
            status: New status
            error_message: Optional error message if status is FAILED

        Returns:
            Updated contract

        Raises:
            ContractNotFoundError: If contract doesn't exist
        """
        contract = self.get_by_contract_id(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        contract.status = status
        contract.updated_at = datetime.utcnow()

        if error_message:
            contract.error_message = error_message

        logger.info(f"Updating contract {contract_id} status to {status}")
        return self.update(contract)

    def get_by_status(self, status: ContractStatus) -> List[Contract]:
        """
        Get all contracts with a specific status.

        Args:
            status: Contract status to filter by

        Returns:
            List of contracts with the given status
        """
        query = "SELECT * FROM c WHERE c.status = @status AND c.type = 'contract'"
        parameters = [{"name": "@status", "value": status.value}]

        return self.query(query, parameters)

    def get_recent_contracts(self, limit: int = 10) -> List[Contract]:
        """
        Get recently created contracts.

        Args:
            limit: Maximum number of contracts to return

        Returns:
            List of recent contracts
        """
        query = f"""
            SELECT TOP {limit} * FROM c
            WHERE c.type = 'contract'
            ORDER BY c.created_at DESC
        """

        return self.query(query)

    def set_blob_uri(self, contract_id: str, blob_uri: str) -> Contract:
        """
        Set the blob storage URI for the contract file.

        Args:
            contract_id: Contract identifier
            blob_uri: Azure Blob Storage URI

        Returns:
            Updated contract
        """
        contract = self.get_by_contract_id(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        contract.blob_uri = blob_uri
        contract.updated_at = datetime.utcnow()

        logger.info(f"Setting blob URI for contract {contract_id}")
        return self.update(contract)

    def set_processing_duration(self, contract_id: str, duration_seconds: float) -> Contract:
        """
        Set the total processing duration for the contract.

        Args:
            contract_id: Contract identifier
            duration_seconds: Processing duration in seconds

        Returns:
            Updated contract
        """
        contract = self.get_by_contract_id(contract_id)
        if not contract:
            raise ValueError(f"Contract {contract_id} not found")

        contract.processing_duration_seconds = duration_seconds
        contract.updated_at = datetime.utcnow()

        logger.info(f"Setting processing duration for contract {contract_id}: {duration_seconds}s")
        return self.update(contract)
