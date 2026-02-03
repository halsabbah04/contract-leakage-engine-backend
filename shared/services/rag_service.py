"""RAG (Retrieval-Augmented Generation) service for contract analysis."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from ..db import ClauseRepository, get_cosmos_client
from ..utils.exceptions import RAGServiceError
from ..utils.logging import setup_logging
from .embedding_service import EmbeddingService
from .search_service import SearchService

logger = setup_logging(__name__)


class RAGService:
    """Service for RAG-based contract analysis."""

    # Thread pool for parallel query execution
    _executor = ThreadPoolExecutor(max_workers=5)

    def __init__(self):
        """Initialize RAG service with embedding and search services."""
        try:
            logger.info("Initializing RAG service...")

            self.embedding_service = EmbeddingService()
            self.search_service = SearchService()

            logger.info("RAG service initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {str(e)}")
            raise RAGServiceError(f"RAG service initialization failed: {str(e)}")

    def index_contract_clauses(self, contract_id: str, force_reindex: bool = False) -> Dict[str, int]:
        """
        Index all clauses for a contract in Azure AI Search.

        Complete workflow:
        1. Generate embeddings for clauses (if needed)
        2. Index clauses in Azure AI Search

        Args:
            contract_id: Contract identifier
            force_reindex: Force re-indexing even if clauses already indexed

        Returns:
            Dictionary with indexing statistics
        """
        try:
            logger.info(f"Indexing contract {contract_id} for RAG")

            # Get clauses first to check if already indexed
            cosmos_client = get_cosmos_client()
            clause_repo = ClauseRepository(cosmos_client.clauses_container)
            clauses = clause_repo.get_by_contract_id(contract_id)

            if not clauses:
                logger.warning(f"No clauses found for contract {contract_id}")
                return {"total_clauses": 0, "embedded_count": 0, "indexed_count": 0}

            # Check if all clauses already have embeddings (skip if so, unless force_reindex)
            clauses_with_embeddings = [c for c in clauses if c.embedding]
            if not force_reindex and len(clauses_with_embeddings) == len(clauses):
                logger.info(f"All {len(clauses)} clauses already have embeddings, skipping indexing")
                return {
                    "total_clauses": len(clauses),
                    "embedded_count": 0,
                    "indexed_count": 0,
                    "skipped": True,
                }

            # Step 1: Generate embeddings for clauses that need them
            logger.info("Step 1: Generating embeddings...")
            embedded_count = self.embedding_service.embed_clauses_for_contract(contract_id, force_reembed=force_reindex)

            # Re-fetch clauses with embeddings
            if embedded_count > 0:
                clauses = clause_repo.get_by_contract_id(contract_id)
                clauses_with_embeddings = [c for c in clauses if c.embedding]

            logger.info(f"Found {len(clauses_with_embeddings)} clauses with embeddings")

            # Step 2: Index in Azure AI Search
            logger.info("Step 2: Indexing in Azure AI Search...")
            indexed_count = self.search_service.index_clauses_batch(clauses_with_embeddings)

            stats = {
                "total_clauses": len(clauses),
                "embedded_count": embedded_count,
                "indexed_count": indexed_count,
            }

            logger.info(f"RAG indexing complete: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Failed to index contract for RAG: {str(e)}")
            raise RAGServiceError(f"RAG indexing failed: {str(e)}")

    def semantic_search(
        self,
        query: str,
        contract_id: Optional[str] = None,
        top_k: int = 5,
        min_score: float = 0.7,
        use_hybrid: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search on contract clauses.

        Args:
            query: Natural language query
            contract_id: Optional contract filter
            top_k: Number of results to return
            min_score: Minimum relevance score
            use_hybrid: Use hybrid (vector + keyword) search

        Returns:
            List of relevant clauses with scores
        """
        try:
            logger.info(f"Semantic search: query='{query[:50]}...', contract={contract_id}")

            # Generate query embedding
            query_vector = self.embedding_service.embed_query(query)

            # Perform search
            if use_hybrid:
                results = self.search_service.hybrid_search(
                    query_text=query,
                    query_vector=query_vector,
                    contract_id=contract_id,
                    top_k=top_k,
                    min_score=min_score,
                )
            else:
                results = self.search_service.vector_search(
                    query_vector=query_vector,
                    contract_id=contract_id,
                    top_k=top_k,
                    min_score=min_score,
                )

            logger.info(f"Semantic search returned {len(results)} results")

            return results

        except Exception as e:
            logger.error(f"Semantic search failed: {str(e)}")
            raise RAGServiceError(f"Semantic search failed: {str(e)}")

    def find_similar_clauses(
        self,
        clause_id: str,
        contract_id: str,
        top_k: int = 5,
        same_contract_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Find clauses similar to a given clause.

        Useful for:
        - Finding related clauses in the same contract
        - Finding precedents across contracts
        - Detecting inconsistencies

        Args:
            clause_id: Reference clause ID
            contract_id: Contract containing the clause
            top_k: Number of similar clauses to return
            same_contract_only: Only search within the same contract

        Returns:
            List of similar clauses
        """
        try:
            logger.info(f"Finding clauses similar to {clause_id}")

            # Get reference clause
            cosmos_client = get_cosmos_client()
            clause_repo = ClauseRepository(cosmos_client.clauses_container)
            reference_clause = clause_repo.read(clause_id, contract_id)

            if not reference_clause:
                logger.error(f"Reference clause not found: {clause_id}")
                return []

            if not reference_clause.embedding:
                logger.warning(f"Reference clause has no embedding: {clause_id}")
                return []

            # Search for similar clauses
            filter_contract = contract_id if same_contract_only else None

            results = self.search_service.vector_search(
                query_vector=reference_clause.embedding,
                contract_id=filter_contract,
                top_k=top_k + 1,  # +1 to account for the clause itself
                min_score=0.6,
            )

            # Filter out the reference clause itself
            similar_clauses = [r for r in results if r["clause_id"] != clause_id][:top_k]

            logger.info(f"Found {len(similar_clauses)} similar clauses")

            return similar_clauses

        except Exception as e:
            logger.error(f"Failed to find similar clauses: {str(e)}")
            raise RAGServiceError(f"Similar clause search failed: {str(e)}")

    def build_rag_context(
        self,
        queries: List[str],
        contract_id: str,
        max_clauses_per_query: int = 3,
        max_total_clauses: int = 10,
    ) -> Dict[str, Any]:
        """
        Build RAG context for AI-powered analysis.

        Retrieves relevant clauses based on multiple queries and builds
        a structured context for LLM consumption. Executes queries in parallel
        for faster context building.

        Args:
            queries: List of search queries (leakage patterns to look for)
            contract_id: Contract to search within
            max_clauses_per_query: Max results per query
            max_total_clauses: Max total clauses in context

        Returns:
            Dictionary with context and metadata
        """
        try:
            logger.info(f"Building RAG context with {len(queries)} queries (parallel execution)")

            # Execute all queries in parallel using thread pool
            def execute_query(query: str) -> tuple:
                """Execute a single query and return results with query."""
                results = self.semantic_search(
                    query=query,
                    contract_id=contract_id,
                    top_k=max_clauses_per_query,
                    min_score=0.65,
                    use_hybrid=True,
                )
                return query, results

            # Submit all queries to thread pool for parallel execution
            futures = [self._executor.submit(execute_query, query) for query in queries]

            # Collect results as they complete
            all_results = []
            seen_clause_ids = set()

            for future in futures:
                try:
                    query, results = future.result(timeout=30)  # 30 second timeout per query

                    # Deduplicate and add matched query info
                    for result in results:
                        clause_id = result["clause_id"]
                        if clause_id not in seen_clause_ids:
                            result["matched_query"] = query
                            all_results.append(result)
                            seen_clause_ids.add(clause_id)

                except Exception as e:
                    logger.warning(f"Query execution failed: {str(e)}")
                    continue

            if not all_results:
                logger.warning("No results from parallel queries")
                return {
                    "contract_id": contract_id,
                    "query_count": len(queries),
                    "retrieved_clauses": [],
                    "total_clauses": 0,
                    "context_summary": "No relevant clauses found.",
                }

            # Sort by relevance score
            score_key = "combined_score" if "combined_score" in all_results[0] else "similarity_score"
            all_results.sort(key=lambda x: x[score_key], reverse=True)

            # Limit to max_total_clauses
            all_results = all_results[:max_total_clauses]

            # Build structured context
            context = {
                "contract_id": contract_id,
                "query_count": len(queries),
                "retrieved_clauses": all_results,
                "total_clauses": len(all_results),
                "context_summary": self._summarize_context(all_results),
            }

            logger.info(f"RAG context built: {len(all_results)} clauses retrieved (parallel)")

            return context

        except Exception as e:
            logger.error(f"Failed to build RAG context: {str(e)}")
            raise RAGServiceError(f"RAG context building failed: {str(e)}")

    def _summarize_context(self, results: List[Dict[str, Any]]) -> str:
        """
        Create a text summary of retrieved clauses for LLM context.

        Args:
            results: Search results

        Returns:
            Formatted context string
        """
        if not results:
            return "No relevant clauses found."

        summary_parts = []

        for i, result in enumerate(results, 1):
            clause_type = result.get("clause_type", "unknown")
            text = result.get("normalized_summary", result.get("original_text", ""))
            risk_signals = result.get("risk_signals", [])

            summary = f"\n[Clause {i}] Type: {clause_type}"
            if risk_signals:
                summary += f" | Risk Signals: {', '.join(risk_signals)}"
            summary += f"\nText: {text[:500]}"

            summary_parts.append(summary)

        return "\n".join(summary_parts)

    def reindex_contract(self, contract_id: str) -> Dict[str, int]:
        """
        Completely reindex a contract (regenerate embeddings and reindex).

        Args:
            contract_id: Contract identifier

        Returns:
            Indexing statistics
        """
        try:
            logger.info(f"Reindexing contract {contract_id}")

            # Delete existing index entries
            self.search_service.delete_clauses_by_contract(contract_id)

            # Reindex with fresh embeddings
            return self.index_contract_clauses(contract_id, force_reindex=True)

        except Exception as e:
            logger.error(f"Failed to reindex contract: {str(e)}")
            raise RAGServiceError(f"Reindexing failed: {str(e)}")

    def get_rag_statistics(self, contract_id: str) -> Dict[str, Any]:
        """
        Get RAG statistics for a contract.

        Args:
            contract_id: Contract identifier

        Returns:
            Statistics dictionary
        """
        try:
            cosmos_client = get_cosmos_client()
            clause_repo = ClauseRepository(cosmos_client.clauses_container)

            clauses = clause_repo.get_by_contract_id(contract_id)

            clauses_with_embeddings = sum(1 for c in clauses if c.embedding)

            stats = {
                "contract_id": contract_id,
                "total_clauses": len(clauses),
                "clauses_with_embeddings": clauses_with_embeddings,
                "embedding_coverage": (clauses_with_embeddings / len(clauses) if clauses else 0),
                "indexed_in_search": True,  # Assume indexed if embeddings exist
            }

            return stats

        except Exception as e:
            logger.error(f"Failed to get RAG statistics: {str(e)}")
            return {}
