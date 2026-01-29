"""Cosmos DB client wrapper for the Contract Leakage Engine."""

from functools import lru_cache
from typing import Optional

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError

from ..utils.config import get_settings
from ..utils.exceptions import ConfigurationError, DatabaseError
from ..utils.logging import setup_logging

logger = setup_logging(__name__)


class CosmosDBClient:
    """
    Wrapper for Azure Cosmos DB client.

    Provides thread-safe, singleton access to Cosmos DB database and containers.
    All containers use contract_id as partition key for optimal query performance.
    """

    def __init__(self):
        """Initialize Cosmos DB client."""
        self.settings = get_settings()
        self._client: Optional[CosmosClient] = None
        self._database: Optional[DatabaseProxy] = None
        self._containers: dict[str, ContainerProxy] = {}

    @property
    def client(self) -> CosmosClient:
        """Get or create Cosmos DB client."""
        if self._client is None:
            try:
                logger.info("Initializing Cosmos DB client")
                self._client = CosmosClient.from_connection_string(self.settings.COSMOS_CONNECTION_STRING)
            except Exception as e:
                logger.error(f"Failed to initialize Cosmos DB client: {str(e)}")
                raise ConfigurationError(
                    f"Failed to connect to Cosmos DB. Check your connection string. Error: {str(e)}"
                )
        return self._client

    @property
    def database(self) -> DatabaseProxy:
        """Get or create database proxy."""
        if self._database is None:
            try:
                logger.info(f"Getting database: {self.settings.COSMOS_DATABASE_NAME}")
                self._database = self.client.get_database_client(self.settings.COSMOS_DATABASE_NAME)
            except CosmosResourceNotFoundError:
                logger.error(f"Database {self.settings.COSMOS_DATABASE_NAME} not found")
                raise DatabaseError(
                    f"Database '{self.settings.COSMOS_DATABASE_NAME}' not found. "
                    "Please create it first using Azure Portal or setup scripts."
                )
            except CosmosHttpResponseError as e:
                logger.error(f"Cosmos HTTP error accessing database: {str(e)}")
                raise DatabaseError(f"Failed to access database (HTTP {e.status_code}): {str(e)}")
            except Exception as e:
                logger.error(f"Failed to get database: {str(e)}")
                raise DatabaseError(f"Failed to access database: {str(e)}")
        return self._database

    def get_container(self, container_name: str) -> ContainerProxy:
        """
        Get container proxy by name.

        Args:
            container_name: Name of the container

        Returns:
            ContainerProxy instance

        Raises:
            DatabaseError: If container cannot be accessed
        """
        if container_name not in self._containers:
            try:
                logger.info(f"Getting container: {container_name}")
                self._containers[container_name] = self.database.get_container_client(container_name)
            except CosmosResourceNotFoundError:
                logger.error(f"Container {container_name} not found")
                raise DatabaseError(
                    f"Container '{container_name}' not found in database '{self.settings.COSMOS_DATABASE_NAME}'. "
                    "Please create it first using Azure Portal or setup scripts."
                )
            except CosmosHttpResponseError as e:
                logger.error(f"Cosmos HTTP error accessing container {container_name}: {str(e)}")
                raise DatabaseError(f"Failed to access container '{container_name}' (HTTP {e.status_code}): {str(e)}")
            except Exception as e:
                logger.error(f"Failed to get container {container_name}: {str(e)}")
                raise DatabaseError(f"Failed to access container '{container_name}': {str(e)}")
        return self._containers[container_name]

    @property
    def contracts_container(self) -> ContainerProxy:
        """Get contracts container."""
        return self.get_container(self.settings.COSMOS_CONTRACTS_CONTAINER)

    @property
    def clauses_container(self) -> ContainerProxy:
        """Get clauses container."""
        return self.get_container(self.settings.COSMOS_CLAUSES_CONTAINER)

    @property
    def findings_container(self) -> ContainerProxy:
        """Get leakage_findings container."""
        return self.get_container(self.settings.COSMOS_FINDINGS_CONTAINER)

    @property
    def sessions_container(self) -> ContainerProxy:
        """Get analysis_sessions container."""
        return self.get_container(self.settings.COSMOS_SESSIONS_CONTAINER)

    @property
    def overrides_container(self) -> ContainerProxy:
        """Get user_overrides container."""
        return self.get_container(self.settings.COSMOS_OVERRIDES_CONTAINER)

    @property
    def obligations_container(self) -> ContainerProxy:
        """Get obligations container."""
        return self.get_container(self.settings.COSMOS_OBLIGATIONS_CONTAINER)

    def close(self):
        """Close the Cosmos DB client connection."""
        if self._client:
            logger.info("Closing Cosmos DB client")
            # Cosmos SDK manages connection pooling, explicit close not needed
            self._client = None
            self._database = None
            self._containers.clear()


@lru_cache()
def get_cosmos_client() -> CosmosDBClient:
    """
    Get cached Cosmos DB client instance (singleton).

    Returns:
        CosmosDBClient instance
    """
    return CosmosDBClient()
