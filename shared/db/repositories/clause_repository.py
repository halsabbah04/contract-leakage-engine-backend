"""Repository for Clause operations."""

from typing import List, Optional

from ...models.clause import Clause
from ...utils.logging import setup_logging
from .base_repository import BaseRepository

logger = setup_logging(__name__)


class ClauseRepository(BaseRepository[Clause]):
    """Repository for Clause CRUD operations."""

    def __init__(self, container):
        """Initialize clause repository."""
        super().__init__(container, Clause)

    def get_by_contract_id(self, contract_id: str) -> List[Clause]:
        """
        Get all clauses for a specific contract.

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of clauses for the contract
        """
        logger.info(f"Getting all clauses for contract {contract_id}")
        return self.get_all_by_partition(contract_id)

    def get_by_id_and_contract(self, clause_id: str, contract_id: str) -> Optional[Clause]:
        """
        Get a specific clause by ID and contract ID.

        Args:
            clause_id: Clause identifier
            contract_id: Contract identifier (partition key)

        Returns:
            Clause if found, None otherwise
        """
        return self.read(clause_id, contract_id)

    def get_by_clause_type(self, contract_id: str, clause_type: str) -> List[Clause]:
        """
        Get all clauses of a specific type for a contract.

        Args:
            contract_id: Contract identifier (partition key)
            clause_type: Type of clause to filter by

        Returns:
            List of clauses matching the type
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND c.clause_type = @clause_type
            AND c.type = 'clause'
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@clause_type", "value": clause_type},
        ]

        logger.info(f"Getting {clause_type} clauses for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_by_risk_signals(self, contract_id: str, risk_signal: str) -> List[Clause]:
        """
        Get clauses containing a specific risk signal.

        Args:
            contract_id: Contract identifier (partition key)
            risk_signal: Risk signal to search for

        Returns:
            List of clauses with the risk signal
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND ARRAY_CONTAINS(c.risk_signals, @risk_signal)
            AND c.type = 'clause'
        """
        parameters = [
            {"name": "@contract_id", "value": contract_id},
            {"name": "@risk_signal", "value": risk_signal},
        ]

        logger.info(f"Getting clauses with risk signal '{risk_signal}' for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def get_clauses_with_embeddings(self, contract_id: str) -> List[Clause]:
        """
        Get all clauses that have vector embeddings (for RAG).

        Args:
            contract_id: Contract identifier (partition key)

        Returns:
            List of clauses with embeddings
        """
        query = """
            SELECT * FROM c
            WHERE c.contract_id = @contract_id
            AND IS_DEFINED(c.embedding)
            AND c.type = 'clause'
        """
        parameters = [{"name": "@contract_id", "value": contract_id}]

        logger.info(f"Getting clauses with embeddings for contract {contract_id}")
        return self.query(query, parameters, partition_key=contract_id)

    def add_embedding(self, clause_id: str, contract_id: str, embedding: List[float]) -> Clause:
        """
        Add vector embedding to a clause.

        Args:
            clause_id: Clause identifier
            contract_id: Contract identifier (partition key)
            embedding: Vector embedding

        Returns:
            Updated clause
        """
        clause = self.get_by_id_and_contract(clause_id, contract_id)
        if not clause:
            raise ValueError(f"Clause {clause_id} not found in contract {contract_id}")

        clause.embedding = embedding

        logger.info(f"Adding embedding to clause {clause_id} (dim={len(embedding)})")
        return self.update(clause)

    def bulk_create(self, clauses: List[Clause]) -> List[Clause]:
        """
        Create multiple clauses efficiently.

        Args:
            clauses: List of clauses to create

        Returns:
            List of created clauses
        """
        created_clauses = []

        logger.info(f"Bulk creating {len(clauses)} clauses")

        for clause in clauses:
            try:
                created = self.create(clause)
                created_clauses.append(created)
            except Exception as e:
                logger.error(f"Failed to create clause {clause.id}: {str(e)}")
                # Continue with other clauses

        logger.info(f"Successfully created {len(created_clauses)}/{len(clauses)} clauses")
        return created_clauses
