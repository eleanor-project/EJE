"""SQLite-based precedent manager with semantic similarity support."""

import sqlite3
import hashlib
import json
import pickle
from typing import Dict, List, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from ..utils.logging import get_logger
from ..constants import PRECEDENT_SIMILARITY_THRESHOLD
from .precedent_schema import create_precedent_tables


class PrecedentManagerSQLite:
    """
    SQLite-based precedent manager.
    Stores and retrieves precedent bundles with semantic similarity support.
    """

    def __init__(
        self,
        db_path: str = "./eleanor_data/precedents.db",
        use_embeddings: bool = True
    ) -> None:
        self.logger = get_logger("EJE.PrecedentManagerSQLite")
        self.db_path: str = db_path
        self.use_embeddings: bool = use_embeddings

        # Create database and tables
        create_precedent_tables(db_path)

        # Initialize embedding model
        if self.use_embeddings:
            try:
                self.logger.info("Loading sentence transformer model...")
                self.embedder: Optional[SentenceTransformer] = SentenceTransformer('all-MiniLM-L6-v2')
                self.logger.info("Semantic similarity enabled")
            except Exception as e:
                self.logger.warning(f"Failed to load embeddings model: {e}. Falling back to hash-only matching.")
                self.use_embeddings = False
                self.embedder = None
        else:
            self.embedder = None

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _hash_case(self, case: Dict[str, Any]) -> str:
        """Generate SHA-256 hash of case for exact matching."""
        return hashlib.sha256(
            json.dumps(case, sort_keys=True).encode()
        ).hexdigest()

    def _embed_case(self, case: Dict[str, Any]) -> Optional[np.ndarray]:
        """Generate embedding vector for semantic similarity."""
        if not self.use_embeddings or not self.embedder:
            return None

        try:
            # Create a text representation of the case
            text = case.get('text', '')
            if 'context' in case:
                text += f" {json.dumps(case['context'])}"

            # Generate embedding
            embedding = self.embedder.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            self.logger.error(f"Failed to generate embedding: {e}")
            return None

    def lookup(
        self,
        case: Dict[str, Any],
        similarity_threshold: float = PRECEDENT_SIMILARITY_THRESHOLD,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Return precedents similar to the given case.

        Args:
            case: The case dictionary to find precedents for
            similarity_threshold: Minimum cosine similarity (0-1) for semantic matches
            max_results: Maximum number of results to return

        Returns:
            List of precedent bundles, sorted by similarity (most similar first)
        """
        # First, try exact hash matching (fastest)
        target_hash = self._hash_case(case)
        exact_matches = self._lookup_by_hash(target_hash, max_results)

        if exact_matches:
            self.logger.info(f"Found {len(exact_matches)} exact hash matches")
            return exact_matches

        # If no exact matches and embeddings enabled, use semantic similarity
        if self.use_embeddings and self.embedder:
            return self._semantic_lookup(case, similarity_threshold, max_results)

        # No matches
        return []

    def _lookup_by_hash(self, case_hash: str, max_results: int) -> List[Dict[str, Any]]:
        """Lookup precedents by exact hash match."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT p.*, GROUP_CONCAT(co.id) as critic_output_ids
            FROM precedents p
            LEFT JOIN critic_outputs co ON p.id = co.precedent_id
            WHERE p.case_hash = ?
            GROUP BY p.id
            ORDER BY p.timestamp DESC
            LIMIT ?
        """, (case_hash, max_results))

        results = []
        for row in cursor.fetchall():
            precedent = self._row_to_precedent(row, cursor)
            results.append(precedent)

        conn.close()
        return results

    def _semantic_lookup(
        self,
        case: Dict[str, Any],
        threshold: float,
        max_results: int
    ) -> List[Dict[str, Any]]:
        """
        Find similar precedents using semantic similarity.

        Args:
            case: The case to match
            threshold: Minimum similarity threshold
            max_results: Maximum results to return

        Returns:
            List of similar precedents with similarity scores
        """
        # Generate embedding for query case
        query_embedding = self._embed_case(case)
        if query_embedding is None:
            return []

        conn = self._get_connection()
        cursor = conn.cursor()

        # Retrieve all embeddings
        cursor.execute("""
            SELECT pe.precedent_id, pe.embedding, p.id
            FROM precedent_embeddings pe
            JOIN precedents p ON pe.precedent_id = p.id
        """)

        embeddings = []
        precedent_ids = []

        for row in cursor.fetchall():
            try:
                embedding = pickle.loads(row['embedding'])
                embeddings.append(embedding)
                precedent_ids.append(row['precedent_id'])
            except Exception as e:
                self.logger.error(f"Failed to deserialize embedding: {e}")
                continue

        if not embeddings:
            conn.close()
            return []

        # Calculate cosine similarities
        try:
            similarities = cosine_similarity([query_embedding], embeddings)[0]

            # Find precedents above threshold
            similar_indices = np.where(similarities >= threshold)[0]

            if len(similar_indices) == 0:
                self.logger.info("No semantically similar precedents found")
                conn.close()
                return []

            # Sort by similarity (descending)
            sorted_indices = similar_indices[np.argsort(-similarities[similar_indices])]

            # Build result list with similarity scores
            results = []
            for idx in sorted_indices[:max_results]:
                precedent_id = precedent_ids[idx]

                # Fetch the full precedent
                cursor.execute("""
                    SELECT p.*, GROUP_CONCAT(co.id) as critic_output_ids
                    FROM precedents p
                    LEFT JOIN critic_outputs co ON p.id = co.precedent_id
                    WHERE p.id = ?
                    GROUP BY p.id
                """, (precedent_id,))

                row = cursor.fetchone()
                if row:
                    precedent = self._row_to_precedent(row, cursor)
                    precedent['similarity_score'] = float(similarities[idx])
                    results.append(precedent)

            self.logger.info(f"Found {len(results)} semantically similar precedents")
            conn.close()
            return results

        except Exception as e:
            self.logger.error(f"Semantic lookup failed: {e}")
            conn.close()
            return []

    def _row_to_precedent(self, row: sqlite3.Row, cursor: sqlite3.Cursor) -> Dict[str, Any]:
        """Convert database row to precedent bundle."""
        # Fetch critic outputs
        critic_outputs = []
        cursor.execute("""
            SELECT * FROM critic_outputs WHERE precedent_id = ?
        """, (row['id'],))

        for co_row in cursor.fetchall():
            critic_outputs.append({
                'critic': co_row['critic_name'],
                'verdict': co_row['verdict'],
                'confidence': co_row['confidence'],
                'justification': co_row['justification'],
                'weight': co_row['weight'],
                'priority': co_row['priority']
            })

        # Reconstruct input
        input_data = {'text': row['input_text']}
        if row['input_context']:
            input_data['context'] = json.loads(row['input_context'])
        if row['input_metadata']:
            input_data['metadata'] = json.loads(row['input_metadata'])

        # Reconstruct bundle
        return {
            'request_id': row['request_id'],
            'timestamp': row['timestamp'],
            'case_hash': row['case_hash'],
            'input': input_data,
            'final_decision': {
                'overall_verdict': row['final_verdict'],
                'reason': row['final_reason'],
                'avg_confidence': row['avg_confidence'],
                'ambiguity': row['ambiguity'],
                'details': critic_outputs
            },
            'critic_outputs': critic_outputs,
            'precedent_refs': []  # Will be populated if needed
        }

    def store_precedent(self, bundle: Dict[str, Any]) -> None:
        """
        Store a new precedent with its hash and embedding.

        Args:
            bundle: The decision bundle to store as precedent
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        try:
            # Extract data
            input_data = bundle.get('input', {})
            final_decision = bundle.get('final_decision', {})

            # Generate hash if not present
            case_hash = bundle.get('case_hash') or self._hash_case(input_data)

            # Insert precedent
            cursor.execute("""
                INSERT INTO precedents (
                    case_hash, request_id, timestamp,
                    input_text, input_context, input_metadata,
                    final_verdict, final_reason, avg_confidence, ambiguity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_hash,
                bundle.get('request_id'),
                bundle.get('timestamp'),
                input_data.get('text'),
                json.dumps(input_data.get('context')) if input_data.get('context') else None,
                json.dumps(input_data.get('metadata')) if input_data.get('metadata') else None,
                final_decision.get('overall_verdict'),
                final_decision.get('reason'),
                final_decision.get('avg_confidence'),
                final_decision.get('ambiguity')
            ))

            precedent_id = cursor.lastrowid

            # Insert critic outputs
            for critic_output in bundle.get('critic_outputs', []):
                cursor.execute("""
                    INSERT INTO critic_outputs (
                        precedent_id, critic_name, verdict, confidence,
                        justification, weight, priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    precedent_id,
                    critic_output.get('critic'),
                    critic_output.get('verdict'),
                    critic_output.get('confidence'),
                    critic_output.get('justification'),
                    critic_output.get('weight', 1.0),
                    critic_output.get('priority')
                ))

            # Generate and store embedding
            if self.use_embeddings and self.embedder:
                embedding = self._embed_case(input_data)
                if embedding is not None:
                    embedding_blob = pickle.dumps(embedding)
                    cursor.execute("""
                        INSERT INTO precedent_embeddings (precedent_id, embedding)
                        VALUES (?, ?)
                    """, (precedent_id, embedding_blob))

            conn.commit()
            self.logger.debug(f"Stored precedent with hash {case_hash[:8]}...")

        except Exception as e:
            conn.rollback()
            self.logger.error(f"Failed to store precedent: {e}")
            raise
        finally:
            conn.close()

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the precedent database."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as count FROM precedents")
        total_precedents = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM precedent_embeddings")
        embeddings_count = cursor.fetchone()['count']

        cursor.execute("SELECT COUNT(*) as count FROM critic_outputs")
        critic_outputs_count = cursor.fetchone()['count']

        conn.close()

        return {
            "total_precedents": total_precedents,
            "embeddings_cached": embeddings_count,
            "critic_outputs_stored": critic_outputs_count,
            "embeddings_enabled": self.use_embeddings,
            "storage_path": self.db_path,
            "storage_type": "SQLite"
        }
