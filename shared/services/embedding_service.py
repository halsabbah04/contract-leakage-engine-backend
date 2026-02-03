"""Embedding service for generating vector embeddings using Azure OpenAI."""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple

from openai import AzureOpenAI

from ..db import ClauseRepository, get_cosmos_client
from ..models.clause import Clause
from ..utils.config import get_settings
from ..utils.exceptions import EmbeddingServiceError
from ..utils.logging import setup_logging

logger = setup_logging(__name__)
settings = get_settings()


class EmbeddingService:
    """Service for generating and managing vector embeddings."""

    def __init__(self):
        """Initialize embedding service with Azure OpenAI client."""
        try:
            logger.info("Initializing Azure OpenAI embedding service...")

            self.client = AzureOpenAI(
                api_key=settings.AZURE_OPENAI_API_KEY,
                api_version=settings.AZURE_OPENAI_API_VERSION,
                azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            )

            self.embedding_model = settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT
            self.embedding_dimensions = settings.EMBEDDING_DIMENSIONS

            logger.info(
                f"Embedding service initialized: model={self.embedding_model}, "
                f"dimensions={self.embedding_dimensions}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize embedding service: {str(e)}")
            raise EmbeddingServiceError(f"Embedding service initialization failed: {str(e)}")

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for a single text.

        Args:
            text: Text to embed

        Returns:
            List of float values representing the embedding vector

        Raises:
            EmbeddingServiceError: If embedding generation fails
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for embedding")
                return []

            # Truncate if too long (max 8192 tokens for text-embedding-3-large)
            text = text[:32000]  # Rough character limit

            response = self.client.embeddings.create(
                input=text,
                model=self.embedding_model,
                dimensions=self.embedding_dimensions,
            )

            embedding = response.data[0].embedding

            logger.debug(f"Generated embedding: {len(embedding)} dimensions")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {str(e)}")
            raise EmbeddingServiceError(f"Embedding generation failed: {str(e)}")

    def generate_embeddings_batch(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches.

        Uses parallel processing with controlled concurrency to maximize throughput
        while respecting Azure OpenAI rate limits.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingServiceError: If batch embedding fails
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size} (parallel)")

            # Prepare batches with their indices
            batches: List[Tuple[int, List[str]]] = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                # Filter empty texts and truncate
                batch = [t[:32000] if t else "" for t in batch]
                batches.append((i // batch_size, batch))

            if len(batches) <= 1:
                # Single batch - process directly
                if batches:
                    _, batch = batches[0]
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.embedding_model,
                        dimensions=self.embedding_dimensions,
                    )
                    return [data.embedding for data in response.data]
                return []

            def process_batch(batch_info: Tuple[int, List[str]]) -> Tuple[int, List[List[float]]]:
                """Process a single batch and return with index for ordering."""
                batch_idx, batch = batch_info
                max_retries = 3
                retry_delay = 0.1

                for attempt in range(max_retries):
                    try:
                        response = self.client.embeddings.create(
                            input=batch,
                            model=self.embedding_model,
                            dimensions=self.embedding_dimensions,
                        )
                        embeddings = [data.embedding for data in response.data]
                        logger.debug(f"Batch {batch_idx + 1} completed: {len(embeddings)} embeddings")
                        return batch_idx, embeddings
                    except Exception as e:
                        if "429" in str(e) or "rate" in str(e).lower():
                            # Rate limited - wait and retry
                            wait_time = retry_delay * (2 ** attempt)
                            logger.warning(f"Batch {batch_idx + 1} rate limited, retrying in {wait_time:.1f}s...")
                            time.sleep(wait_time)
                        else:
                            logger.error(f"Batch {batch_idx + 1} failed: {str(e)}")
                            return batch_idx, [[] for _ in batch]

                # All retries exhausted
                logger.error(f"Batch {batch_idx + 1} failed after {max_retries} retries")
                return batch_idx, [[] for _ in batch_info[1]]

            # Process batches in parallel with limited concurrency (3 concurrent requests)
            max_workers = min(3, len(batches))
            results: List[Tuple[int, List[List[float]]]] = []

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(process_batch, b): b[0] for b in batches}

                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=60)
                        results.append(result)
                    except Exception as e:
                        batch_idx = futures[future]
                        batch_size_actual = len(batches[batch_idx][1])
                        logger.error(f"Batch {batch_idx + 1} execution failed: {str(e)}")
                        results.append((batch_idx, [[] for _ in range(batch_size_actual)]))

            # Sort results by batch index and flatten
            results.sort(key=lambda x: x[0])
            all_embeddings = []
            for _, embeddings in results:
                all_embeddings.extend(embeddings)

            logger.info(f"Generated {len(all_embeddings)} embeddings total (parallel)")

            return all_embeddings

        except Exception as e:
            logger.error(f"Batch embedding generation failed: {str(e)}")
            raise EmbeddingServiceError(f"Batch embedding failed: {str(e)}")

    def embed_clause(self, clause: Clause) -> Clause:
        """
        Generate and attach embedding to a clause.

        Uses normalized_summary as the embedding text (optimized for RAG).

        Args:
            clause: Clause object

        Returns:
            Clause with embedding attached
        """
        try:
            # Use normalized_summary for embedding (more concise, better for retrieval)
            embedding_text = clause.normalized_summary or clause.original_text

            embedding = self.generate_embedding(embedding_text)
            clause.embedding = embedding

            logger.debug(f"Embedded clause {clause.id}: {len(embedding)} dimensions")

            return clause

        except Exception as e:
            logger.error(f"Failed to embed clause {clause.id}: {str(e)}")
            raise EmbeddingServiceError(f"Clause embedding failed: {str(e)}")

    def embed_clauses_for_contract(self, contract_id: str, force_reembed: bool = False) -> int:
        """
        Generate embeddings for all clauses in a contract.

        Args:
            contract_id: Contract identifier
            force_reembed: Re-generate embeddings even if they exist

        Returns:
            Number of clauses embedded

        Raises:
            EmbeddingServiceError: If embedding process fails
        """
        try:
            logger.info(f"Embedding clauses for contract {contract_id}")

            # Get all clauses
            cosmos_client = get_cosmos_client()
            clause_repo = ClauseRepository(cosmos_client.clauses_container)
            clauses = clause_repo.get_by_contract_id(contract_id)

            if not clauses:
                logger.warning(f"No clauses found for contract {contract_id}")
                return 0

            # Filter clauses that need embedding
            if not force_reembed:
                clauses_to_embed = [c for c in clauses if not c.embedding]
                logger.info(f"{len(clauses_to_embed)} clauses need embedding")
            else:
                clauses_to_embed = clauses
                logger.info(f"Force re-embedding {len(clauses_to_embed)} clauses")

            if not clauses_to_embed:
                logger.info("All clauses already have embeddings")
                return 0

            # Prepare texts for batch embedding
            texts = [(c.normalized_summary or c.original_text) for c in clauses_to_embed]

            # Generate embeddings in batches
            embeddings = self.generate_embeddings_batch(texts, batch_size=100)

            # Update clauses with embeddings
            embedded_count = 0
            for clause, embedding in zip(clauses_to_embed, embeddings):
                if embedding:  # Skip empty embeddings from failures
                    try:
                        clause_repo.add_embedding(clause.id, contract_id, embedding)
                        embedded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to store embedding for clause {clause.id}: {str(e)}")

            logger.info(f"Successfully embedded {embedded_count}/{len(clauses_to_embed)} clauses")

            return embedded_count

        except Exception as e:
            logger.error(f"Failed to embed clauses for contract: {str(e)}")
            raise EmbeddingServiceError(f"Contract embedding failed: {str(e)}")

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query text

        Returns:
            Query embedding vector
        """
        return self.generate_embedding(query)

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1)
        """
        try:
            if not embedding1 or not embedding2:
                return 0.0

            # Cosine similarity
            dot_product = sum(a * b for a, b in zip(embedding1, embedding2))

            magnitude1 = sum(a * a for a in embedding1) ** 0.5
            magnitude2 = sum(b * b for b in embedding2) ** 0.5

            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0

            similarity = dot_product / (magnitude1 * magnitude2)

            return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

        except Exception as e:
            logger.error(f"Similarity calculation failed: {str(e)}")
            return 0.0
