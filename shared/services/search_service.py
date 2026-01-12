"""Azure AI Search service for vector and hybrid search."""

import time
from typing import List, Dict, Optional, Any
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
)
from azure.search.documents.models import VectorizedQuery

from ..models.clause import Clause
from ..db import get_cosmos_client, ClauseRepository
from ..utils.config import get_settings
from ..utils.logging import setup_logging
from ..utils.exceptions import SearchServiceError

logger = setup_logging(__name__)
settings = get_settings()


class SearchService:
    """Service for Azure AI Search operations."""

    def __init__(self):
        """Initialize Azure AI Search service."""
        try:
            logger.info("Initializing Azure AI Search service...")

            self.search_endpoint = settings.AZURE_SEARCH_ENDPOINT
            self.search_key = settings.AZURE_SEARCH_API_KEY
            self.index_name = settings.AZURE_SEARCH_INDEX_NAME

            # Initialize clients
            credential = AzureKeyCredential(self.search_key)

            self.index_client = SearchIndexClient(
                endpoint=self.search_endpoint,
                credential=credential
            )

            self.search_client = SearchClient(
                endpoint=self.search_endpoint,
                index_name=self.index_name,
                credential=credential
            )

            logger.info(f"Search service initialized: index={self.index_name}")

        except Exception as e:
            logger.error(f"Failed to initialize search service: {str(e)}")
            raise SearchServiceError(f"Search service initialization failed: {str(e)}")

    def create_or_update_index(self):
        """
        Create or update the search index with vector search configuration.

        This should be called during initial setup or when schema changes.
        """
        try:
            logger.info(f"Creating/updating search index: {self.index_name}")

            # Define fields
            fields = [
                SimpleField(name="id", type=SearchFieldDataType.String, key=True),
                SimpleField(name="contract_id", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="clause_type", type=SearchFieldDataType.String, filterable=True),
                SearchableField(name="original_text", type=SearchFieldDataType.String),
                SearchableField(name="normalized_summary", type=SearchFieldDataType.String),
                SimpleField(name="section_number", type=SearchFieldDataType.String, filterable=True),
                SimpleField(
                    name="risk_signals",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                    filterable=True
                ),
                SimpleField(name="extraction_confidence", type=SearchFieldDataType.Double, filterable=True),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    vector_search_dimensions=settings.EMBEDDING_DIMENSIONS,
                    vector_search_profile_name="clause-vector-profile"
                ),
            ]

            # Configure vector search
            vector_search = VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="clause-hnsw-algorithm",
                        parameters={
                            "m": 4,
                            "efConstruction": 400,
                            "efSearch": 500,
                            "metric": "cosine"
                        }
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="clause-vector-profile",
                        algorithm_configuration_name="clause-hnsw-algorithm"
                    )
                ]
            )

            # Create index
            index = SearchIndex(
                name=self.index_name,
                fields=fields,
                vector_search=vector_search
            )

            # Create or update
            result = self.index_client.create_or_update_index(index)

            logger.info(f"Search index created/updated: {result.name}")

        except Exception as e:
            logger.error(f"Failed to create/update index: {str(e)}")
            raise SearchServiceError(f"Index creation failed: {str(e)}")

    def index_clause(self, clause: Clause):
        """
        Index a single clause in Azure AI Search.

        Args:
            clause: Clause to index

        Raises:
            SearchServiceError: If indexing fails
        """
        try:
            document = self._clause_to_search_document(clause)

            result = self.search_client.upload_documents(documents=[document])

            if result[0].succeeded:
                logger.debug(f"Indexed clause: {clause.id}")
            else:
                logger.error(f"Failed to index clause {clause.id}: {result[0].error_message}")
                raise SearchServiceError(f"Indexing failed: {result[0].error_message}")

        except Exception as e:
            logger.error(f"Failed to index clause {clause.id}: {str(e)}")
            raise SearchServiceError(f"Clause indexing failed: {str(e)}")

    def index_clauses_batch(self, clauses: List[Clause]) -> int:
        """
        Index multiple clauses in batches.

        Args:
            clauses: List of clauses to index

        Returns:
            Number of successfully indexed clauses

        Raises:
            SearchServiceError: If batch indexing fails
        """
        try:
            logger.info(f"Indexing {len(clauses)} clauses in search...")

            # Convert to search documents
            documents = [self._clause_to_search_document(c) for c in clauses]

            # Index in batches of 1000
            batch_size = 1000
            indexed_count = 0

            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]

                try:
                    results = self.search_client.upload_documents(documents=batch)

                    # Count successes
                    batch_success = sum(1 for r in results if r.succeeded)
                    indexed_count += batch_success

                    logger.info(f"Indexed batch {i // batch_size + 1}: {batch_success}/{len(batch)} succeeded")

                    # Log failures
                    for result in results:
                        if not result.succeeded:
                            logger.error(f"Failed to index {result.key}: {result.error_message}")

                    # Rate limiting
                    if i + batch_size < len(documents):
                        time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Batch {i // batch_size + 1} indexing failed: {str(e)}")

            logger.info(f"Successfully indexed {indexed_count}/{len(clauses)} clauses")

            return indexed_count

        except Exception as e:
            logger.error(f"Batch indexing failed: {str(e)}")
            raise SearchServiceError(f"Batch indexing failed: {str(e)}")

    def vector_search(
        self,
        query_vector: List[float],
        contract_id: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform vector similarity search.

        Args:
            query_vector: Query embedding vector
            contract_id: Optional filter by contract
            top_k: Number of results to return
            min_score: Minimum similarity score threshold

        Returns:
            List of search results with scores
        """
        try:
            logger.info(f"Vector search: top_k={top_k}, contract={contract_id}")

            # Create vector query
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top_k,
                fields="embedding"
            )

            # Build filter
            filter_expr = None
            if contract_id:
                filter_expr = f"contract_id eq '{contract_id}'"

            # Execute search
            results = self.search_client.search(
                search_text=None,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=top_k
            )

            # Parse results
            search_results = []
            for result in results:
                score = result['@search.score']

                if score >= min_score:
                    search_results.append({
                        'clause_id': result['id'],
                        'contract_id': result['contract_id'],
                        'clause_type': result['clause_type'],
                        'original_text': result['original_text'],
                        'normalized_summary': result['normalized_summary'],
                        'risk_signals': result.get('risk_signals', []),
                        'similarity_score': score
                    })

            logger.info(f"Vector search returned {len(search_results)} results")

            return search_results

        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise SearchServiceError(f"Vector search failed: {str(e)}")

    def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        contract_id: Optional[str] = None,
        top_k: int = 10,
        min_score: float = 0.6
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search (vector + keyword).

        Combines semantic similarity with keyword matching for better results.

        Args:
            query_text: Text query for keyword search
            query_vector: Query embedding for vector search
            contract_id: Optional filter by contract
            top_k: Number of results to return
            min_score: Minimum combined score threshold

        Returns:
            List of search results with scores
        """
        try:
            logger.info(f"Hybrid search: query='{query_text[:50]}...', top_k={top_k}")

            # Create vector query
            vector_query = VectorizedQuery(
                vector=query_vector,
                k_nearest_neighbors=top_k,
                fields="embedding"
            )

            # Build filter
            filter_expr = None
            if contract_id:
                filter_expr = f"contract_id eq '{contract_id}'"

            # Execute hybrid search
            results = self.search_client.search(
                search_text=query_text,
                vector_queries=[vector_query],
                filter=filter_expr,
                top=top_k,
                query_type="semantic",
                semantic_configuration_name=None  # Use default
            )

            # Parse results
            search_results = []
            for result in results:
                score = result['@search.score']

                if score >= min_score:
                    search_results.append({
                        'clause_id': result['id'],
                        'contract_id': result['contract_id'],
                        'clause_type': result['clause_type'],
                        'original_text': result['original_text'],
                        'normalized_summary': result['normalized_summary'],
                        'risk_signals': result.get('risk_signals', []),
                        'combined_score': score
                    })

            logger.info(f"Hybrid search returned {len(search_results)} results")

            return search_results

        except Exception as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            # Fallback to vector-only search
            logger.warning("Falling back to vector-only search")
            return self.vector_search(query_vector, contract_id, top_k, min_score)

    def delete_clauses_by_contract(self, contract_id: str) -> int:
        """
        Delete all clauses for a contract from the search index.

        Args:
            contract_id: Contract identifier

        Returns:
            Number of clauses deleted
        """
        try:
            logger.info(f"Deleting clauses for contract {contract_id} from search index")

            # Search for all clauses
            results = self.search_client.search(
                search_text="*",
                filter=f"contract_id eq '{contract_id}'",
                select="id",
                top=1000
            )

            # Collect IDs
            clause_ids = [r['id'] for r in results]

            if not clause_ids:
                logger.info("No clauses found to delete")
                return 0

            # Delete documents
            documents = [{"id": cid} for cid in clause_ids]
            delete_results = self.search_client.delete_documents(documents=documents)

            deleted_count = sum(1 for r in delete_results if r.succeeded)

            logger.info(f"Deleted {deleted_count} clauses from search index")

            return deleted_count

        except Exception as e:
            logger.error(f"Failed to delete clauses: {str(e)}")
            raise SearchServiceError(f"Clause deletion failed: {str(e)}")

    def _clause_to_search_document(self, clause: Clause) -> Dict[str, Any]:
        """
        Convert Clause model to search document format.

        Args:
            clause: Clause object

        Returns:
            Search document dictionary
        """
        return {
            "id": clause.id,
            "contract_id": clause.contract_id,
            "clause_type": clause.clause_type,
            "original_text": clause.original_text,
            "normalized_summary": clause.normalized_summary,
            "section_number": clause.section_number,
            "risk_signals": clause.risk_signals or [],
            "extraction_confidence": clause.extraction_confidence or 0.0,
            "embedding": clause.embedding or []
        }

    def get_index_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the search index.

        Returns:
            Dictionary with index statistics
        """
        try:
            index = self.index_client.get_index(self.index_name)

            stats = {
                "index_name": index.name,
                "fields_count": len(index.fields),
                "vector_search_enabled": index.vector_search is not None,
            }

            logger.info(f"Index statistics: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Failed to get index statistics: {str(e)}")
            return {}
