"""
Synchronization utilities for PostgreSQL and VectorDB.

Keeps the PrecedentEmbedding table in PostgreSQL in sync with the vector database.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
import numpy as np

from sqlalchemy.orm import Session

from ..database import DatabaseManager
from ..models import PrecedentEmbedding
from ..repositories import BaseRepository
from .base import VectorStore, EmbeddingMetadata

logger = logging.getLogger(__name__)


class EmbeddingSync:
    """Synchronizes embeddings between PostgreSQL and VectorDB."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        vector_store: VectorStore,
    ):
        """
        Initialize embedding sync.

        Args:
            db_manager: PostgreSQL database manager
            vector_store: Vector database store
        """
        self.db_manager = db_manager
        self.vector_store = vector_store

    async def sync_to_vectordb(
        self,
        precedent_id: str,
        embedding_vector: np.ndarray,
        decision_id: str,
        embedding_model: str,
        context: Optional[str] = None,
        tags: Optional[List[str]] = None,
        similarity_threshold: Optional[float] = None,
    ) -> None:
        """
        Sync a single embedding to both PostgreSQL and VectorDB.

        Args:
            precedent_id: Unique precedent ID
            embedding_vector: Vector embedding
            decision_id: Associated decision ID
            embedding_model: Model used for embedding
            context: Optional context for the embedding
            tags: Optional tags for filtering
            similarity_threshold: Optional similarity threshold
        """
        # Create metadata
        metadata = EmbeddingMetadata(
            precedent_id=precedent_id,
            decision_id=decision_id,
            embedding_model=embedding_model,
            created_at=datetime.utcnow(),
            context=context,
            tags=tags,
            similarity_threshold=similarity_threshold,
        )

        # Store in PostgreSQL
        with self.db_manager.session() as session:
            # Check if exists
            existing = session.query(PrecedentEmbedding).filter_by(
                precedent_id=precedent_id
            ).first()

            if existing:
                # Update
                existing.embedding_vector = embedding_vector.tobytes()
                existing.embedding_dimension = len(embedding_vector)
                existing.embedding_model = embedding_model
                existing.similarity_threshold = similarity_threshold
            else:
                # Create new
                embedding_record = PrecedentEmbedding(
                    precedent_id=precedent_id,
                    decision_id=decision_id,
                    embedding_vector=embedding_vector.tobytes(),
                    embedding_dimension=len(embedding_vector),
                    embedding_model=embedding_model,
                    similarity_threshold=similarity_threshold,
                    created_at=datetime.utcnow(),
                )
                session.add(embedding_record)

            session.commit()

        # Store in VectorDB
        await self.vector_store.upsert(
            precedent_id=precedent_id,
            embedding=embedding_vector,
            metadata=metadata,
        )

        logger.info(f"Synced embedding for precedent {precedent_id}")

    async def sync_batch_to_vectordb(
        self,
        precedent_ids: List[str],
        embedding_vectors: np.ndarray,
        decision_ids: List[str],
        embedding_model: str,
        contexts: Optional[List[Optional[str]]] = None,
        tags_list: Optional[List[Optional[List[str]]]] = None,
        similarity_thresholds: Optional[List[Optional[float]]] = None,
        batch_size: int = 100,
    ) -> None:
        """
        Sync multiple embeddings to both PostgreSQL and VectorDB.

        Args:
            precedent_ids: List of precedent IDs
            embedding_vectors: Array of embeddings
            decision_ids: List of decision IDs
            embedding_model: Model used for embeddings
            contexts: Optional list of contexts
            tags_list: Optional list of tags
            similarity_thresholds: Optional list of thresholds
            batch_size: Batch size for processing
        """
        n = len(precedent_ids)

        # Validate inputs
        if len(decision_ids) != n:
            raise ValueError("decision_ids must match precedent_ids length")
        if embedding_vectors.shape[0] != n:
            raise ValueError("embedding_vectors must match precedent_ids length")

        # Fill defaults
        if contexts is None:
            contexts = [None] * n
        if tags_list is None:
            tags_list = [None] * n
        if similarity_thresholds is None:
            similarity_thresholds = [None] * n

        # Store in PostgreSQL
        with self.db_manager.session() as session:
            for i in range(n):
                # Check if exists
                existing = session.query(PrecedentEmbedding).filter_by(
                    precedent_id=precedent_ids[i]
                ).first()

                if existing:
                    # Update
                    existing.embedding_vector = embedding_vectors[i].tobytes()
                    existing.embedding_dimension = len(embedding_vectors[i])
                    existing.embedding_model = embedding_model
                    existing.similarity_threshold = similarity_thresholds[i]
                else:
                    # Create new
                    embedding_record = PrecedentEmbedding(
                        precedent_id=precedent_ids[i],
                        decision_id=decision_ids[i],
                        embedding_vector=embedding_vectors[i].tobytes(),
                        embedding_dimension=len(embedding_vectors[i]),
                        embedding_model=embedding_model,
                        similarity_threshold=similarity_thresholds[i],
                        created_at=datetime.utcnow(),
                    )
                    session.add(embedding_record)

            session.commit()

        # Create metadata objects
        metadatas = [
            EmbeddingMetadata(
                precedent_id=precedent_ids[i],
                decision_id=decision_ids[i],
                embedding_model=embedding_model,
                created_at=datetime.utcnow(),
                context=contexts[i],
                tags=tags_list[i],
                similarity_threshold=similarity_thresholds[i],
            )
            for i in range(n)
        ]

        # Store in VectorDB
        await self.vector_store.upsert_batch(
            precedent_ids=precedent_ids,
            embeddings=embedding_vectors,
            metadatas=metadatas,
            batch_size=batch_size,
        )

        logger.info(f"Synced batch of {n} embeddings")

    async def delete_from_both(self, precedent_id: str) -> bool:
        """
        Delete embedding from both PostgreSQL and VectorDB.

        Args:
            precedent_id: ID of precedent to delete

        Returns:
            True if deleted from both, False otherwise
        """
        # Delete from PostgreSQL
        with self.db_manager.session() as session:
            deleted_pg = session.query(PrecedentEmbedding).filter_by(
                precedent_id=precedent_id
            ).delete()
            session.commit()

        # Delete from VectorDB
        deleted_vdb = await self.vector_store.delete(precedent_id)

        success = deleted_pg > 0 and deleted_vdb
        if success:
            logger.info(f"Deleted embedding {precedent_id} from both stores")
        else:
            logger.warning(
                f"Partial deletion for {precedent_id}: "
                f"PG={deleted_pg > 0}, VDB={deleted_vdb}"
            )

        return success

    async def delete_batch_from_both(self, precedent_ids: List[str]) -> int:
        """
        Delete multiple embeddings from both stores.

        Args:
            precedent_ids: List of precedent IDs to delete

        Returns:
            Number of embeddings successfully deleted from both
        """
        # Delete from PostgreSQL
        with self.db_manager.session() as session:
            deleted_pg = session.query(PrecedentEmbedding).filter(
                PrecedentEmbedding.precedent_id.in_(precedent_ids)
            ).delete(synchronize_session=False)
            session.commit()

        # Delete from VectorDB
        deleted_vdb = await self.vector_store.delete_batch(precedent_ids)

        logger.info(
            f"Deleted batch: {deleted_pg} from PG, {deleted_vdb} from VectorDB"
        )

        return min(deleted_pg, deleted_vdb)

    async def sync_from_postgres_to_vectordb(
        self,
        limit: Optional[int] = None,
        batch_size: int = 100,
    ) -> int:
        """
        Sync all embeddings from PostgreSQL to VectorDB.

        Useful for initial population or recovery.

        Args:
            limit: Optional limit on number of embeddings to sync
            batch_size: Batch size for syncing

        Returns:
            Number of embeddings synced
        """
        total_synced = 0

        with self.db_manager.session() as session:
            query = session.query(PrecedentEmbedding)

            if limit:
                query = query.limit(limit)

            embeddings = query.all()

            # Process in batches
            for i in range(0, len(embeddings), batch_size):
                batch = embeddings[i:i + batch_size]

                precedent_ids = [e.precedent_id for e in batch]
                decision_ids = [e.decision_id for e in batch]
                vectors = [
                    np.frombuffer(e.embedding_vector, dtype=np.float32)
                    for e in batch
                ]
                embedding_vectors = np.array(vectors)

                metadatas = [
                    EmbeddingMetadata(
                        precedent_id=e.precedent_id,
                        decision_id=e.decision_id,
                        embedding_model=e.embedding_model,
                        created_at=e.created_at,
                        similarity_threshold=e.similarity_threshold,
                    )
                    for e in batch
                ]

                await self.vector_store.upsert_batch(
                    precedent_ids=precedent_ids,
                    embeddings=embedding_vectors,
                    metadatas=metadatas,
                    batch_size=batch_size,
                )

                total_synced += len(batch)
                logger.info(f"Synced {total_synced}/{len(embeddings)} embeddings")

        logger.info(f"Completed sync: {total_synced} embeddings to VectorDB")
        return total_synced

    async def verify_sync(self, sample_size: int = 100) -> Dict[str, Any]:
        """
        Verify sync status between PostgreSQL and VectorDB.

        Args:
            sample_size: Number of random samples to verify

        Returns:
            Dictionary with sync statistics
        """
        with self.db_manager.session() as session:
            # Count in PostgreSQL
            pg_count = session.query(PrecedentEmbedding).count()

            # Get sample IDs
            if pg_count > 0:
                sample_limit = min(sample_size, pg_count)
                samples = session.query(
                    PrecedentEmbedding.precedent_id
                ).limit(sample_limit).all()
                sample_ids = [s.precedent_id for s in samples]
            else:
                sample_ids = []

        # Count in VectorDB
        vdb_count = await self.vector_store.count()

        # Check samples
        missing_in_vdb = 0
        for precedent_id in sample_ids:
            result = await self.vector_store.get(precedent_id, include_embedding=False)
            if result is None:
                missing_in_vdb += 1

        sync_rate = (
            (len(sample_ids) - missing_in_vdb) / len(sample_ids) * 100
            if sample_ids else 100.0
        )

        stats = {
            "postgres_count": pg_count,
            "vectordb_count": vdb_count,
            "samples_checked": len(sample_ids),
            "missing_in_vectordb": missing_in_vdb,
            "sync_rate_percent": sync_rate,
            "in_sync": pg_count == vdb_count and missing_in_vdb == 0,
        }

        logger.info(
            f"Sync verification: PG={pg_count}, VDB={vdb_count}, "
            f"sync_rate={sync_rate:.1f}%"
        )

        return stats


async def search_similar_precedents(
    vector_store: VectorStore,
    query_embedding: np.ndarray,
    top_k: int = 10,
    filters: Optional[Dict[str, Any]] = None,
    min_similarity: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Search for similar precedents in the vector database.

    Args:
        vector_store: VectorStore instance
        query_embedding: Query vector
        top_k: Number of results to return
        filters: Optional metadata filters
        min_similarity: Minimum similarity score (0-1)

    Returns:
        List of similar precedents with metadata

    Example:
        results = await search_similar_precedents(
            vector_store=store,
            query_embedding=embedding,
            top_k=5,
            filters={"tags": ["critical"]},
            min_similarity=0.8,
        )
    """
    results = await vector_store.search(
        query_embedding=query_embedding,
        top_k=top_k,
        filters=filters,
        min_score=min_similarity,
        include_embeddings=False,
    )

    return [result.to_dict() for result in results]
