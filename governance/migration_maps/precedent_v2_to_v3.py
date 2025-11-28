"""
Migrate precedents from v2.0 (hash-based) to v3.0 (vector-based).

GCR Reference: GCR-2025-002
Migration Type: Additive (backward compatible)
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class MigrationReport:
    """Report of migration results."""

    total: int
    migrated: int
    failed: int
    skipped: int
    failures: List[tuple]
    duration_seconds: float


def migrate_precedent(old_precedent: Dict) -> Dict:
    """
    Migrate single precedent from v2 to v3 schema.

    Changes in v3:
    - Add 'embedding' field (None initially, computed on demand)
    - Add 'migration_status' field
    - Add 'original_version' field
    - Add 'semantic_searchable' flag

    Args:
        old_precedent: Precedent in v2.0 schema

    Returns:
        Precedent in v3.0 schema
    """
    # Preserve all v2 fields
    new_precedent = old_precedent.copy()

    # Add v3 fields
    new_precedent.update({
        "version": "3.0",

        # Vector search fields (computed lazily)
        "embedding": None,  # Will be computed when needed
        "semantic_searchable": False,  # Set to True after embedding generated

        # Migration tracking
        "migration_status": "MIGRATED",
        "original_version": old_precedent.get("version", "2.0"),
        "migrated_at": datetime.utcnow().isoformat() + "Z"
    })

    return new_precedent


def validate_precedent(precedent: Dict) -> bool:
    """
    Validate precedent schema.

    Args:
        precedent: Precedent dictionary

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["id", "hash", "input_data", "outcome", "timestamp"]

    # Check required fields
    for field in required_fields:
        if field not in precedent:
            logger.error(f"Missing required field: {field}")
            return False

    # Validate input_data structure
    input_data = precedent.get("input_data", {})
    if "prompt" not in input_data:
        logger.error("Missing 'prompt' in input_data")
        return False

    # Validate outcome structure
    outcome = precedent.get("outcome", {})
    if "verdict" not in outcome:
        logger.error("Missing 'verdict' in outcome")
        return False

    return True


def migrate_all(
    source_file: str,
    destination_file: str,
    dry_run: bool = False
) -> MigrationReport:
    """
    Migrate all precedents from v2 to v3.

    Args:
        source_file: Path to v2 precedents JSON file
        destination_file: Path to write v3 precedents
        dry_run: If True, don't write output file

    Returns:
        MigrationReport with results
    """
    start_time = datetime.utcnow()

    logger.info(f"Starting migration: {source_file} -> {destination_file}")

    # Load v2 precedents
    try:
        with open(source_file, 'r') as f:
            precedents_v2 = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load source file: {e}")
        return MigrationReport(
            total=0,
            migrated=0,
            failed=1,
            skipped=0,
            failures=[("load", str(e))],
            duration_seconds=0.0
        )

    # Migrate each precedent
    precedents_v3 = []
    failures = []
    skipped = 0

    for i, prec_v2 in enumerate(precedents_v2):
        try:
            # Check if already v3
            if prec_v2.get("version") == "3.0":
                logger.debug(f"Precedent {i} already v3, skipping")
                precedents_v3.append(prec_v2)
                skipped += 1
                continue

            # Migrate
            prec_v3 = migrate_precedent(prec_v2)

            # Validate
            if not validate_precedent(prec_v3):
                raise ValueError("Validation failed")

            precedents_v3.append(prec_v3)

        except Exception as e:
            prec_id = prec_v2.get("id", prec_v2.get("hash", f"index_{i}"))
            logger.error(f"Migration failed for {prec_id}: {e}")
            failures.append((prec_id, str(e)))

    # Write v3 precedents
    if not dry_run:
        try:
            with open(destination_file, 'w') as f:
                json.dump(precedents_v3, f, indent=2, default=str)
            logger.info(f"Wrote {len(precedents_v3)} precedents to {destination_file}")
        except Exception as e:
            logger.error(f"Failed to write destination file: {e}")
            failures.append(("write", str(e)))

    # Calculate duration
    end_time = datetime.utcnow()
    duration = (end_time - start_time).total_seconds()

    # Build report
    report = MigrationReport(
        total=len(precedents_v2),
        migrated=len(precedents_v3) - skipped,
        failed=len(failures),
        skipped=skipped,
        failures=failures,
        duration_seconds=duration
    )

    logger.info(
        f"Migration complete: {report.migrated} migrated, "
        f"{report.skipped} skipped, {report.failed} failed "
        f"({duration:.2f}s)"
    )

    return report


def rollback_migration(
    v3_file: str,
    v2_backup_file: str
) -> bool:
    """
    Rollback migration by restoring v2 backup.

    Args:
        v3_file: Path to v3 precedents (will be overwritten)
        v2_backup_file: Path to v2 backup

    Returns:
        True if successful, False otherwise
    """
    try:
        import shutil
        shutil.copy2(v2_backup_file, v3_file)
        logger.info(f"Rollback successful: restored {v2_backup_file} to {v3_file}")
        return True
    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return False


def generate_embedding_batch(
    precedents_v3: List[Dict],
    embedding_model: str = "all-MiniLM-L6-v2"
) -> List[Dict]:
    """
    Generate embeddings for migrated precedents (post-migration step).

    Args:
        precedents_v3: List of v3 precedents
        embedding_model: Sentence transformer model name

    Returns:
        Precedents with embeddings populated
    """
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np

        model = SentenceTransformer(embedding_model)
        logger.info(f"Loaded embedding model: {embedding_model}")

        updated = []
        for prec in precedents_v3:
            # Skip if already has embedding
            if prec.get("embedding") is not None:
                updated.append(prec)
                continue

            # Generate embedding
            input_data = prec.get("input_data", {})
            prompt = input_data.get("prompt", "")
            context_str = json.dumps(input_data.get("context", {}))
            text = f"{prompt} {context_str}"

            embedding = model.encode(text, convert_to_numpy=True)

            # Normalize
            embedding = embedding / np.linalg.norm(embedding)

            # Update precedent
            prec_updated = prec.copy()
            prec_updated["embedding"] = embedding.tolist()
            prec_updated["semantic_searchable"] = True

            updated.append(prec_updated)

        logger.info(f"Generated embeddings for {len(updated)} precedents")
        return updated

    except ImportError:
        logger.warning("sentence-transformers not available, skipping embeddings")
        return precedents_v3
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return precedents_v3


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Migrate precedents v2 -> v3")
    parser.add_argument("source", help="Source v2 precedents JSON file")
    parser.add_argument("destination", help="Destination v3 precedents JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Don't write output")
    parser.add_argument("--embeddings", action="store_true", help="Generate embeddings")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run migration
    report = migrate_all(args.source, args.destination, dry_run=args.dry_run)

    # Generate embeddings if requested
    if args.embeddings and not args.dry_run and report.migrated > 0:
        logger.info("Generating embeddings...")
        with open(args.destination, 'r') as f:
            precs = json.load(f)

        precs_with_embeddings = generate_embedding_batch(precs)

        with open(args.destination, 'w') as f:
            json.dump(precs_with_embeddings, f, indent=2, default=str)

    # Print report
    print(f"\nMigration Report:")
    print(f"  Total:    {report.total}")
    print(f"  Migrated: {report.migrated}")
    print(f"  Skipped:  {report.skipped}")
    print(f"  Failed:   {report.failed}")
    print(f"  Duration: {report.duration_seconds:.2f}s")

    if report.failures:
        print(f"\nFailures:")
        for prec_id, error in report.failures:
            print(f"  - {prec_id}: {error}")

    # Exit with appropriate code
    sys.exit(0 if report.failed == 0 else 1)
