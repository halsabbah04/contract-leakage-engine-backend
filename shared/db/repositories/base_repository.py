"""Base repository for common Cosmos DB operations."""

from typing import TypeVar, Generic, Optional, List, Dict, Any
from abc import ABC, abstractmethod
from azure.cosmos import ContainerProxy
from azure.cosmos.exceptions import CosmosResourceNotFoundError, CosmosHttpResponseError
from pydantic import BaseModel

from ...utils.logging import setup_logging
from ...utils.exceptions import DatabaseError, ContractNotFoundError

logger = setup_logging(__name__)

T = TypeVar('T', bound=BaseModel)


class BaseRepository(Generic[T], ABC):
    """
    Base repository providing common CRUD operations for Cosmos DB.

    All containers use contract_id as partition key.
    """

    def __init__(self, container: ContainerProxy, model_class: type[T]):
        """
        Initialize repository.

        Args:
            container: Cosmos DB container proxy
            model_class: Pydantic model class for this repository
        """
        self.container = container
        self.model_class = model_class

    def create(self, item: T) -> T:
        """
        Create a new item in Cosmos DB.

        Args:
            item: Pydantic model instance to create

        Returns:
            Created item

        Raises:
            DatabaseError: If creation fails
        """
        try:
            # Convert Pydantic model to dict
            item_dict = item.model_dump(mode='json', exclude_none=False)

            logger.info(f"Creating item in {self.container.id}: {item_dict.get('id')}")

            # Create in Cosmos DB
            created_item = self.container.create_item(body=item_dict)

            # Convert back to Pydantic model
            return self.model_class(**created_item)

        except CosmosHttpResponseError as e:
            logger.error(f"Failed to create item: {str(e)}")
            raise DatabaseError(f"Failed to create item in {self.container.id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error creating item: {str(e)}")
            raise DatabaseError(f"Unexpected error: {str(e)}")

    def read(self, item_id: str, partition_key: str) -> Optional[T]:
        """
        Read an item by ID and partition key.

        Args:
            item_id: Item ID
            partition_key: Partition key value (contract_id)

        Returns:
            Item if found, None otherwise

        Raises:
            DatabaseError: If read operation fails
        """
        try:
            logger.info(f"Reading item from {self.container.id}: {item_id}")

            item_dict = self.container.read_item(
                item=item_id,
                partition_key=partition_key
            )

            return self.model_class(**item_dict)

        except CosmosResourceNotFoundError:
            logger.warning(f"Item not found in {self.container.id}: {item_id}")
            return None
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to read item: {str(e)}")
            raise DatabaseError(f"Failed to read item from {self.container.id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error reading item: {str(e)}")
            raise DatabaseError(f"Unexpected error: {str(e)}")

    def update(self, item: T) -> T:
        """
        Update an existing item (replace).

        Args:
            item: Updated item

        Returns:
            Updated item

        Raises:
            DatabaseError: If update fails
        """
        try:
            item_dict = item.model_dump(mode='json', exclude_none=False)

            logger.info(f"Updating item in {self.container.id}: {item_dict.get('id')}")

            updated_item = self.container.replace_item(
                item=item_dict.get('id'),
                body=item_dict
            )

            return self.model_class(**updated_item)

        except CosmosResourceNotFoundError:
            logger.error(f"Item not found for update: {item_dict.get('id')}")
            raise ContractNotFoundError(f"Item {item_dict.get('id')} not found")
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to update item: {str(e)}")
            raise DatabaseError(f"Failed to update item in {self.container.id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error updating item: {str(e)}")
            raise DatabaseError(f"Unexpected error: {str(e)}")

    def delete(self, item_id: str, partition_key: str) -> bool:
        """
        Delete an item by ID and partition key.

        Args:
            item_id: Item ID
            partition_key: Partition key value (contract_id)

        Returns:
            True if deleted successfully

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            logger.info(f"Deleting item from {self.container.id}: {item_id}")

            self.container.delete_item(
                item=item_id,
                partition_key=partition_key
            )

            return True

        except CosmosResourceNotFoundError:
            logger.warning(f"Item not found for deletion: {item_id}")
            return False
        except CosmosHttpResponseError as e:
            logger.error(f"Failed to delete item: {str(e)}")
            raise DatabaseError(f"Failed to delete item from {self.container.id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error deleting item: {str(e)}")
            raise DatabaseError(f"Unexpected error: {str(e)}")

    def query(self, query: str, parameters: Optional[List[Dict[str, Any]]] = None,
              partition_key: Optional[str] = None) -> List[T]:
        """
        Execute a SQL query against the container.

        Args:
            query: SQL query string
            parameters: Query parameters
            partition_key: Optional partition key for partition-scoped query

        Returns:
            List of items matching the query

        Raises:
            DatabaseError: If query fails
        """
        try:
            logger.info(f"Executing query on {self.container.id}")
            logger.debug(f"Query: {query}, Parameters: {parameters}")

            query_kwargs = {
                'query': query,
                'enable_cross_partition_query': partition_key is None
            }

            if parameters:
                query_kwargs['parameters'] = parameters

            if partition_key:
                query_kwargs['partition_key'] = partition_key

            items = list(self.container.query_items(**query_kwargs))

            return [self.model_class(**item) for item in items]

        except CosmosHttpResponseError as e:
            logger.error(f"Query failed: {str(e)}")
            raise DatabaseError(f"Query failed on {self.container.id}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during query: {str(e)}")
            raise DatabaseError(f"Unexpected error: {str(e)}")

    def get_all_by_partition(self, partition_key: str) -> List[T]:
        """
        Get all items for a specific partition key (contract_id).

        Args:
            partition_key: Partition key value (contract_id)

        Returns:
            List of all items in the partition

        Raises:
            DatabaseError: If query fails
        """
        query = f"SELECT * FROM c WHERE c.partition_key = @partition_key"
        parameters = [{"name": "@partition_key", "value": partition_key}]

        return self.query(query, parameters, partition_key=partition_key)

    def exists(self, item_id: str, partition_key: str) -> bool:
        """
        Check if an item exists.

        Args:
            item_id: Item ID
            partition_key: Partition key value

        Returns:
            True if item exists, False otherwise
        """
        return self.read(item_id, partition_key) is not None
