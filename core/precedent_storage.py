"""
Precedent Storage Backend

Task 3.1: Implement Precedent Storage Backend

Provides persistent storage for precedent cases using SQLite (with option for PostgreSQL).
Each precedent captures the query, evidence bundle, and final decision for future retrieval.
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
import logging

logger = logging.getLogger("ejc.core.precedent_storage")


class PrecedentStorage:
    """
    Storage backend for precedent cases.

    Supports SQLite by default with option to extend to PostgreSQL.
    Stores completed decisions for similarity-based retrieval.
    """

    def __init__(self, db_path: str = "precedents.db"):
        """
        Initialize precedent storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Create database tables and indexes if they don't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create precedents table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS precedents (
                    precedent_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    query_hash TEXT NOT NULL,
                    evidence_bundle TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
            """)

            # Create indexes for efficient lookup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_query_hash
                ON precedents(query_hash)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_decision
                ON precedents(decision)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON precedents(timestamp DESC)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_confidence
                ON precedents(confidence DESC)
            """)

            conn.commit()
            logger.info(f"Initialized precedent storage at {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
        finally:
            conn.close()

    def _generate_precedent_id(self, query: str, timestamp: str) -> str:
        """
        Generate unique precedent ID.

        Args:
            query: The input query
            timestamp: ISO 8601 timestamp

        Returns:
            Unique precedent ID
        """
        # Use hash of query + timestamp for uniqueness
        hash_input = f"{query}|{timestamp}".encode('utf-8')
        hash_digest = hashlib.sha256(hash_input).hexdigest()[:16]
        return f"prec-{hash_digest}"

    def _hash_query(self, query: str) -> str:
        """
        Generate SHA-256 hash of query for deduplication.

        Args:
            query: The input query

        Returns:
            SHA-256 hash (hex string)
        """
        return hashlib.sha256(query.encode('utf-8')).hexdigest()

    def store_precedent(
        self,
        query: str,
        evidence_bundle: Dict[str, Any],
        decision: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a new precedent.

        Args:
            query: The input query/prompt
            evidence_bundle: Complete evidence bundle dict
            decision: Final verdict (ALLOW, DENY, ESCALATE, etc.)
            confidence: Final confidence score (0.0-1.0)
            metadata: Optional additional metadata

        Returns:
            Precedent ID

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate inputs
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")

        if decision not in ["ALLOW", "DENY", "ESCALATE", "ABSTAIN"]:
            raise ValueError(f"Invalid decision: {decision}")

        if not 0.0 <= confidence <= 1.0:
            raise ValueError(f"Confidence must be 0.0-1.0, got {confidence}")

        # Generate IDs and timestamps
        timestamp = datetime.utcnow().isoformat() + "Z"
        precedent_id = self._generate_precedent_id(query, timestamp)
        query_hash = self._hash_query(query)

        # Serialize data
        evidence_bundle_json = json.dumps(evidence_bundle)
        metadata_json = json.dumps(metadata) if metadata else None

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO precedents
                (precedent_id, query, query_hash, evidence_bundle, decision,
                 confidence, timestamp, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                precedent_id,
                query,
                query_hash,
                evidence_bundle_json,
                decision,
                confidence,
                timestamp,
                metadata_json,
                timestamp
            ))

            conn.commit()

        logger.info(f"Stored precedent {precedent_id}: {decision} ({confidence:.2f})")
        return precedent_id

    def get_precedent(self, precedent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a precedent by ID.

        Args:
            precedent_id: Precedent ID

        Returns:
            Precedent dict or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM precedents WHERE precedent_id = ?
            """, (precedent_id,))

            row = cursor.fetchone()

            if row:
                return self._row_to_dict(row)
            return None

    def find_by_query_hash(self, query: str) -> List[Dict[str, Any]]:
        """
        Find precedents with identical query (by hash).

        Args:
            query: Query string

        Returns:
            List of matching precedents
        """
        query_hash = self._hash_query(query)

        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM precedents
                WHERE query_hash = ?
                ORDER BY timestamp DESC
            """, (query_hash,))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def find_by_decision(
        self,
        decision: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find precedents by decision type.

        Args:
            decision: Decision type (ALLOW, DENY, etc.)
            limit: Maximum number of results

        Returns:
            List of precedents
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM precedents
                WHERE decision = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (decision, limit))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def find_recent(
        self,
        limit: int = 100,
        min_confidence: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Find recent precedents.

        Args:
            limit: Maximum number of results
            min_confidence: Optional minimum confidence threshold

        Returns:
            List of recent precedents
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            if min_confidence is not None:
                cursor.execute("""
                    SELECT * FROM precedents
                    WHERE confidence >= ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (min_confidence, limit))
            else:
                cursor.execute("""
                    SELECT * FROM precedents
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def search_by_text(
        self,
        search_text: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Simple text search in queries (for basic retrieval).

        Args:
            search_text: Text to search for
            limit: Maximum number of results

        Returns:
            List of matching precedents
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Simple LIKE search (case-insensitive)
            search_pattern = f"%{search_text}%"

            cursor.execute("""
                SELECT * FROM precedents
                WHERE query LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (search_pattern, limit))

            rows = cursor.fetchall()
            return [self._row_to_dict(row) for row in rows]

    def count_precedents(self) -> int:
        """
        Get total number of stored precedents.

        Returns:
            Count of precedents
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM precedents")
            return cursor.fetchone()[0]

    def delete_precedent(self, precedent_id: str) -> bool:
        """
        Delete a precedent by ID.

        Args:
            precedent_id: Precedent ID

        Returns:
            True if deleted, False if not found
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM precedents WHERE precedent_id = ?
            """, (precedent_id,))

            conn.commit()
            deleted = cursor.rowcount > 0

            if deleted:
                logger.info(f"Deleted precedent {precedent_id}")

            return deleted

    def clear_all(self):
        """
        Clear all precedents (use with caution).

        Only for testing or explicit user action.
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM precedents")
            conn.commit()

        logger.warning("Cleared all precedents from storage")

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get storage statistics.

        Returns:
            Dict with statistics
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Total count
            cursor.execute("SELECT COUNT(*) FROM precedents")
            total = cursor.fetchone()[0]

            # By decision
            cursor.execute("""
                SELECT decision, COUNT(*) as count
                FROM precedents
                GROUP BY decision
            """)
            by_decision = {row[0]: row[1] for row in cursor.fetchall()}

            # Average confidence
            cursor.execute("SELECT AVG(confidence) FROM precedents")
            avg_confidence = cursor.fetchone()[0] or 0.0

            # Oldest and newest
            cursor.execute("""
                SELECT MIN(timestamp), MAX(timestamp)
                FROM precedents
            """)
            oldest, newest = cursor.fetchone()

            return {
                "total_precedents": total,
                "by_decision": by_decision,
                "average_confidence": avg_confidence,
                "oldest_precedent": oldest,
                "newest_precedent": newest
            }

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """
        Convert SQLite row to dict.

        Args:
            row: SQLite row object

        Returns:
            Dict representation
        """
        return {
            "precedent_id": row["precedent_id"],
            "query": row["query"],
            "query_hash": row["query_hash"],
            "evidence_bundle": json.loads(row["evidence_bundle"]),
            "decision": row["decision"],
            "confidence": row["confidence"],
            "timestamp": row["timestamp"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else None,
            "created_at": row["created_at"]
        }
