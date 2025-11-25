#!/usr/bin/env python3
"""
Migration script to convert JSON precedent storage to SQLite.

Usage:
    python scripts/migrate_precedents.py [--json-path PATH] [--db-path PATH]
"""

import argparse
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.eje.core.precedent_schema import migrate_json_to_sqlite, create_precedent_tables
from src.eje.utils.logging import get_logger

logger = get_logger("EJE.Migration")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate precedents from JSON to SQLite database"
    )
    parser.add_argument(
        "--json-path",
        default="./eleanor_data/precedent_store.json",
        help="Path to JSON precedent file (default: ./eleanor_data/precedent_store.json)"
    )
    parser.add_argument(
        "--db-path",
        default="./eleanor_data/precedents.db",
        help="Path to SQLite database (default: ./eleanor_data/precedents.db)"
    )
    parser.add_argument(
        "--create-only",
        action="store_true",
        help="Only create database schema without migration"
    )

    args = parser.parse_args()

    logger.info("Starting precedent migration...")
    logger.info(f"JSON source: {args.json_path}")
    logger.info(f"SQLite target: {args.db_path}")

    if args.create_only:
        logger.info("Creating database schema only...")
        create_precedent_tables(args.db_path)
        logger.info("Database schema created successfully!")
        return

    # Run migration
    try:
        count = migrate_json_to_sqlite(args.json_path, args.db_path)
        logger.info(f"✅ Migration complete! {count} precedents migrated.")

        # Backup original JSON file
        if count > 0 and os.path.exists(args.json_path):
            backup_path = f"{args.json_path}.backup"
            os.rename(args.json_path, backup_path)
            logger.info(f"Original JSON backed up to: {backup_path}")

    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
