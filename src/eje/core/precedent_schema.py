"""SQLite schema for precedent storage."""

import sqlite3
from typing import Optional
from ..utils.logging import get_logger

logger = get_logger("EJE.PrecedentSchema")


def create_precedent_tables(db_path: str) -> None:
    """
    Create the SQLite tables for precedent storage.

    Args:
        db_path: Path to the SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Precedents table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precedents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_hash TEXT NOT NULL UNIQUE,
            request_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            input_text TEXT NOT NULL,
            input_context TEXT,
            input_metadata TEXT,
            final_verdict TEXT NOT NULL,
            final_reason TEXT,
            avg_confidence REAL,
            ambiguity REAL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_case_hash (case_hash),
            INDEX idx_timestamp (timestamp),
            INDEX idx_verdict (final_verdict)
        )
    """)

    # Critic outputs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS critic_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            precedent_id INTEGER NOT NULL,
            critic_name TEXT NOT NULL,
            verdict TEXT NOT NULL,
            confidence REAL NOT NULL,
            justification TEXT,
            weight REAL DEFAULT 1.0,
            priority TEXT,
            FOREIGN KEY (precedent_id) REFERENCES precedents(id) ON DELETE CASCADE,
            INDEX idx_precedent_id (precedent_id),
            INDEX idx_critic_name (critic_name)
        )
    """)

    # Embeddings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precedent_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            precedent_id INTEGER NOT NULL UNIQUE,
            embedding BLOB NOT NULL,
            model_name TEXT DEFAULT 'all-MiniLM-L6-v2',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (precedent_id) REFERENCES precedents(id) ON DELETE CASCADE,
            INDEX idx_precedent_id (precedent_id)
        )
    """)

    # Precedent references table (for tracking similar cases)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precedent_references (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            precedent_id INTEGER NOT NULL,
            referenced_precedent_id INTEGER NOT NULL,
            similarity_score REAL,
            reference_type TEXT DEFAULT 'semantic',
            FOREIGN KEY (precedent_id) REFERENCES precedents(id) ON DELETE CASCADE,
            FOREIGN KEY (referenced_precedent_id) REFERENCES precedents(id) ON DELETE CASCADE,
            INDEX idx_precedent_id (precedent_id),
            INDEX idx_referenced_id (referenced_precedent_id)
        )
    """)

    conn.commit()
    conn.close()

    logger.info(f"Precedent database schema created at {db_path}")


def migrate_json_to_sqlite(json_path: str, db_path: str) -> int:
    """
    Migrate precedents from JSON file to SQLite database.

    Args:
        json_path: Path to the JSON precedent file
        db_path: Path to the SQLite database

    Returns:
        Number of precedents migrated
    """
    import json
    import os

    if not os.path.exists(json_path):
        logger.warning(f"JSON file not found: {json_path}")
        return 0

    # Create tables if they don't exist
    create_precedent_tables(db_path)

    # Load JSON data
    with open(json_path, 'r') as f:
        precedents = json.load(f)

    if not precedents:
        logger.info("No precedents to migrate")
        return 0

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    migrated_count = 0

    for precedent in precedents:
        try:
            # Extract input data
            input_data = precedent.get('input', {})
            final_decision = precedent.get('final_decision', {})

            # Insert precedent
            cursor.execute("""
                INSERT OR IGNORE INTO precedents (
                    case_hash, request_id, timestamp,
                    input_text, input_context, input_metadata,
                    final_verdict, final_reason, avg_confidence, ambiguity
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                precedent.get('case_hash'),
                precedent.get('request_id'),
                precedent.get('timestamp'),
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
            for critic_output in precedent.get('critic_outputs', []):
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

            migrated_count += 1

        except Exception as e:
            logger.error(f"Failed to migrate precedent {precedent.get('request_id')}: {e}")
            continue

    conn.commit()
    conn.close()

    logger.info(f"Migrated {migrated_count} precedents from JSON to SQLite")
    return migrated_count
