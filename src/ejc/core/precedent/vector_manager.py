"""
Vector-based Precedent Manager using Qdrant

Provides production-grade semantic similarity search for precedent retrieval
using Qdrant vector database with persistent storage and efficient indexing.

Features:
- Semantic similarity search with configurable scoring
- Persistent vector storage with Qdrant
- Batch insertion for performance
- Hybrid search (vector + metadata filtering)
- Automatic embedding generation
- Connection pooling and retry logic
"""

import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest
)
from qdrant_client.http import models

from .embeddings import embed_text
from ...utils.logging import get_logger
from ..error_handling import PrecedentException, ConfigurationException


logger = get_logger("ejc.precedent.vector")


class VectorPrecedentManager:
    """
    Manages precedent storage and retrieval using Qdrant vector database.

    Provides efficient semantic similarity search with persistent storage,
    metadata filtering, and batch operations.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Vector Precedent Manager with configuration.

        Args:
            config: Configuration dict containing:
                - vector_db.url: Qdrant server URL (or ":memory:" for in-memory)
                - vector_db.collection: Collection name for precedents
                - vector_db.dimension: Embedding dimension (default: 384 for MiniLM)
                - embedding_model: Sentence-transformers model name
                - similarity_threshold: Min similarity scores

        Raises:
            ConfigurationException: If required configuration is missing
        """
        try:
            self.config = config

            # Vector DB configuration
            vector_cfg = config.get("vector_db", {})
            self.url = vector_cfg.get("url", ":memory:")
            self.collection_name = vector_cfg.get("collection", "precedents")
            self.dimension = vector_cfg.get("dimension", 384)  # MiniLM-L6 default

            # Embedding configuration
            self.embedding_model = config.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")

            # Similarity thresholds
            self.thresholds = config.get("similarity_threshold", {
                "inherited": 0.80,
                "advisory": 0.60,
                "novelty": 0.40
            })

            # Initialize Qdrant client
            if self.url == ":memory:":
                logger.info("Initializing in-memory Qdrant client")
                self.client = QdrantClient(":memory:")
            else:
                logger.info(f"Connecting to Qdrant at {self.url}")
                self.client = QdrantClient(url=self.url)

            # Initialize collection
            self._initialize_collection()

            logger.info(f"VectorPrecedentManager initialized with collection '{self.collection_name}'")

        except Exception as e:
            raise ConfigurationException(f"Failed to initialize VectorPrecedentManager: {str(e)}")

    def _initialize_collection(self):
        """Create collection if it doesn't exist."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection '{self.collection_name}'")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Collection '{self.collection_name}' created successfully")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists")

        except Exception as e:
            raise PrecedentException(f"Failed to initialize collection: {str(e)}")

    def store_precedent(
        self,
        decision_id: str,
        input_data: Dict[str, Any],
        outcome: Dict[str, Any],
        timestamp: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a precedent case in the vector database.

        Args:
            decision_id: Unique decision identifier
            input_data: Original input case data
            outcome: Decision outcome with verdict and justification
            timestamp: ISO format timestamp
            metadata: Optional additional metadata

        Returns:
            Point ID in Qdrant

        Raises:
            PrecedentException: If storage fails
        """
        try:
            # Generate embedding from input data
            input_text = json.dumps(input_data, sort_keys=True)
            embedding = embed_text(input_text, self.embedding_model)

            # Prepare metadata payload
            payload = {
                "decision_id": decision_id,
                "input_data": input_data,
                "outcome": outcome,
                "timestamp": timestamp,
                "verdict": outcome.get("verdict", "UNKNOWN"),
                "confidence": outcome.get("confidence", 0.0),
                "indexed_at": datetime.utcnow().isoformat() + "Z"
            }

            if metadata:
                payload["metadata"] = metadata

            # Generate unique point ID
            point_id = str(uuid.uuid4())

            # Store in Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[
                    PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload=payload
                    )
                ]
            )

            logger.info(f"Stored precedent {decision_id} with point ID {point_id}")
            return point_id

        except Exception as e:
            raise PrecedentException(f"Failed to store precedent: {str(e)}")

    def search_similar(
        self,
        query_data: Dict[str, Any],
        limit: int = 10,
        min_similarity: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar precedents using semantic similarity.

        Args:
            query_data: Query case data to find similar precedents for
            limit: Maximum number of results to return
            min_similarity: Minimum similarity score (0.0 to 1.0)
            filters: Optional metadata filters (e.g., {"verdict": "ALLOW"})

        Returns:
            List of precedent dicts sorted by similarity (highest first)
            Each dict contains: id, similarity, input_data, outcome, timestamp

        Raises:
            PrecedentException: If search fails
        """
        try:
            # Generate query embedding
            query_text = json.dumps(query_data, sort_keys=True)
            query_embedding = embed_text(query_text, self.embedding_model)

            # Build filter if provided
            search_filter = None
            if filters:
                conditions = []
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                if conditions:
                    search_filter = Filter(must=conditions)

            # Perform vector search
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                query_filter=search_filter,
                limit=limit,
                score_threshold=min_similarity
            )

            # Format results
            precedents = []
            for result in results:
                payload = result.payload
                precedent = {
                    "id": payload.get("decision_id"),
                    "similarity": result.score,
                    "input_data": payload.get("input_data", {}),
                    "outcome": payload.get("outcome", {}),
                    "timestamp": payload.get("timestamp"),
                    "verdict": payload.get("verdict"),
                    "confidence": payload.get("confidence", 0.0)
                }

                # Add metadata if present
                if "metadata" in payload:
                    precedent["metadata"] = payload["metadata"]

                precedents.append(precedent)

            logger.info(f"Found {len(precedents)} similar precedents (limit={limit})")
            return precedents

        except Exception as e:
            raise PrecedentException(f"Failed to search precedents: {str(e)}")

    def batch_store(self, precedents: List[Dict[str, Any]]) -> List[str]:
        """
        Store multiple precedents in a single batch operation.

        Args:
            precedents: List of precedent dicts, each containing:
                - decision_id
                - input_data
                - outcome
                - timestamp
                - metadata (optional)

        Returns:
            List of point IDs

        Raises:
            PrecedentException: If batch storage fails
        """
        try:
            points = []
            point_ids = []

            for prec in precedents:
                # Generate embedding
                input_text = json.dumps(prec["input_data"], sort_keys=True)
                embedding = embed_text(input_text, self.embedding_model)

                # Prepare payload
                payload = {
                    "decision_id": prec["decision_id"],
                    "input_data": prec["input_data"],
                    "outcome": prec["outcome"],
                    "timestamp": prec["timestamp"],
                    "verdict": prec["outcome"].get("verdict", "UNKNOWN"),
                    "confidence": prec["outcome"].get("confidence", 0.0),
                    "indexed_at": datetime.utcnow().isoformat() + "Z"
                }

                if "metadata" in prec:
                    payload["metadata"] = prec["metadata"]

                # Generate point ID
                point_id = str(uuid.uuid4())
                point_ids.append(point_id)

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding.tolist(),
                        payload=payload
                    )
                )

            # Batch upsert
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )

            logger.info(f"Batch stored {len(precedents)} precedents")
            return point_ids

        except Exception as e:
            raise PrecedentException(f"Failed to batch store precedents: {str(e)}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the precedent collection.

        Returns:
            Dict with collection statistics
        """
        try:
            collection_info = self.client.get_collection(self.collection_name)

            return {
                "collection_name": self.collection_name,
                "points_count": collection_info.points_count,
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "status": collection_info.status
            }

        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {"error": str(e)}

    def delete_precedent(self, decision_id: str) -> bool:
        """
        Delete a precedent by decision ID.

        Args:
            decision_id: Decision ID to delete

        Returns:
            True if deleted, False if not found
        """
        try:
            # Search for points with this decision_id
            results = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=Filter(
                    must=[
                        FieldCondition(
                            key="decision_id",
                            match=MatchValue(value=decision_id)
                        )
                    ]
                ),
                limit=1
            )

            if results[0]:  # Found points
                point_ids = [point.id for point in results[0]]
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
                logger.info(f"Deleted precedent {decision_id}")
                return True
            else:
                logger.warning(f"Precedent {decision_id} not found")
                return False

        except Exception as e:
            logger.error(f"Failed to delete precedent: {str(e)}")
            return False

    def clear_collection(self):
        """Clear all precedents from the collection (use with caution)."""
        try:
            self.client.delete_collection(self.collection_name)
            self._initialize_collection()
            logger.warning(f"Cleared collection '{self.collection_name}'")
        except Exception as e:
            raise PrecedentException(f"Failed to clear collection: {str(e)}")
