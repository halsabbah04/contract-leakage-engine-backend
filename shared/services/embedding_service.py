"""Embedding service for generating vector embeddings using Azure OpenAI."""

import time
from typing import List

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

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call

        Returns:
            List of embedding vectors

        Raises:
            EmbeddingServiceError: If batch embedding fails
        """
        try:
            logger.info(f"Generating embeddings for {len(texts)} texts in batches of {batch_size}")

            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]

                # Filter empty texts
                batch = [t[:32000] if t else "" for t in batch]

                try:
                    response = self.client.embeddings.create(
                        input=batch,
                        model=self.embedding_model,
                        dimensions=self.embedding_dimensions,
                    )

                    batch_embeddings = [data.embedding for data in response.data]
                    all_embeddings.extend(batch_embeddings)

                    logger.info(f"Processed batch {i // batch_size + 1}: {len(batch_embeddings)} embeddings")

                    # Rate limiting (avoid throttling)
                    if i + batch_size < len(texts):
                        time.sleep(0.5)

                except Exception as e:
                    logger.error(f"Batch {i // batch_size + 1} failed: {str(e)}")
                    # Add empty embeddings for failed batch
                    all_embeddings.extend([[] for _ in batch])

            logger.info(f"Generated {len(all_embeddings)} embeddings total")

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
