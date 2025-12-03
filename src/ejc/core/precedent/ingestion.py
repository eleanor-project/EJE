"""
Precedent Ingestion Pipeline

Handles importing precedent cases from various sources and formats into the precedent storage system.
Supports batch processing, validation, deduplication, and automatic embedding generation.

Features:
- Multi-format support (JSON, JSONL, CSV, Evidence Bundles)
- Batch processing with progress tracking
- Automatic deduplication using case hashing
- Embedding generation for semantic search
- Validation and error handling
- Transaction management for atomicity
"""

import json
import csv
import os
import pickle
from typing import Any, Dict, List, Optional, Callable, Iterator
from datetime import datetime
from pathlib import Path

import numpy as np

from .embeddings import embed_text
from .sql_store import SQLPrecedentStore
from .store import VectorPrecedentManager
from ..evidence_normalizer import EvidenceBundle, EvidenceBundleSerializer
from ...utils.logging import get_logger
from ..error_handling import PrecedentException


logger = get_logger("ejc.precedent.ingestion")


class PrecedentIngestionPipeline:
    """
    Pipeline for ingesting precedent cases from various sources.

    Handles validation, deduplication, embedding generation, and storage
    for precedent cases in multiple formats.
    """

    def __init__(
        self,
        store: Any,  # SQLPrecedentStore or VectorPrecedentManager
        embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2',
        batch_size: int = 100,
        validate: bool = True,
        skip_duplicates: bool = True
    ):
        """
        Initialize precedent ingestion pipeline.

        Args:
            store: Precedent storage backend (SQL or Vector)
            embedding_model: Model to use for generating embeddings
            batch_size: Number of precedents to process in each batch
            validate: Whether to validate precedents before ingestion
            skip_duplicates: Whether to skip duplicate precedents
        """
        self.store = store
        self.embedding_model = embedding_model
        self.batch_size = batch_size
        self.validate = validate
        self.skip_duplicates = skip_duplicates

        self.stats = {
            'total': 0,
            'ingested': 0,
            'skipped': 0,
            'errors': 0
        }

    def reset_stats(self):
        """Reset ingestion statistics"""
        self.stats = {
            'total': 0,
            'ingested': 0,
            'skipped': 0,
            'errors': 0
        }

    def ingest_from_json(self, file_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, int]:
        """
        Ingest precedents from a JSON file.

        Args:
            file_path: Path to JSON file containing precedent array
            progress_callback: Optional callback for progress updates (called with stats dict)

        Returns:
            Statistics dictionary with counts

        Raises:
            PrecedentException: If ingestion fails
        """
        try:
            logger.info(f"Ingesting precedents from JSON file: {file_path}")

            with open(file_path, 'r') as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise PrecedentException(f"Expected JSON array, got {type(data).__name__}")

            return self._ingest_batch(data, progress_callback)

        except json.JSONDecodeError as e:
            raise PrecedentException(f"Invalid JSON format: {str(e)}")
        except FileNotFoundError:
            raise PrecedentException(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to ingest from JSON: {str(e)}")
            raise PrecedentException(f"JSON ingestion failed: {str(e)}")

    def ingest_from_jsonl(self, file_path: str, progress_callback: Optional[Callable] = None) -> Dict[str, int]:
        """
        Ingest precedents from a JSONL (JSON Lines) file.

        Args:
            file_path: Path to JSONL file
            progress_callback: Optional callback for progress updates

        Returns:
            Statistics dictionary with counts

        Raises:
            PrecedentException: If ingestion fails
        """
        try:
            logger.info(f"Ingesting precedents from JSONL file: {file_path}")

            precedents = []
            with open(file_path, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        precedent = json.loads(line)
                        precedents.append(precedent)

                        # Process in batches
                        if len(precedents) >= self.batch_size:
                            self._ingest_batch(precedents, progress_callback)
                            precedents = []

                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON on line {line_num}: {str(e)}")
                        self.stats['errors'] += 1

            # Process remaining precedents
            if precedents:
                self._ingest_batch(precedents, progress_callback)

            return self.stats

        except FileNotFoundError:
            raise PrecedentException(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to ingest from JSONL: {str(e)}")
            raise PrecedentException(f"JSONL ingestion failed: {str(e)}")

    def ingest_from_csv(self, file_path: str, column_mapping: Optional[Dict[str, str]] = None, progress_callback: Optional[Callable] = None) -> Dict[str, int]:
        """
        Ingest precedents from a CSV file.

        Args:
            file_path: Path to CSV file
            column_mapping: Mapping of CSV columns to precedent fields
                Example: {'request': 'request_id', 'text': 'input_text', ...}
            progress_callback: Optional callback for progress updates

        Returns:
            Statistics dictionary with counts

        Raises:
            PrecedentException: If ingestion fails
        """
        try:
            logger.info(f"Ingesting precedents from CSV file: {file_path}")

            # Default column mapping
            if column_mapping is None:
                column_mapping = {
                    'request_id': 'request_id',
                    'input_text': 'input_text',
                    'final_verdict': 'final_verdict',
                    'final_reason': 'final_reason',
                    'avg_confidence': 'avg_confidence',
                    'timestamp': 'timestamp'
                }

            precedents = []
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    try:
                        # Map CSV columns to precedent fields
                        precedent = {}
                        for csv_col, prec_field in column_mapping.items():
                            if csv_col in row:
                                value = row[csv_col]

                                # Type conversion for numeric fields
                                if prec_field in ['avg_confidence', 'ambiguity'] and value:
                                    value = float(value)

                                precedent[prec_field] = value

                        precedents.append(precedent)

                        # Process in batches
                        if len(precedents) >= self.batch_size:
                            self._ingest_batch(precedents, progress_callback)
                            precedents = []

                    except (ValueError, KeyError) as e:
                        logger.warning(f"Invalid row in CSV: {str(e)}")
                        self.stats['errors'] += 1

            # Process remaining precedents
            if precedents:
                self._ingest_batch(precedents, progress_callback)

            return self.stats

        except FileNotFoundError:
            raise PrecedentException(f"File not found: {file_path}")
        except Exception as e:
            logger.error(f"Failed to ingest from CSV: {str(e)}")
            raise PrecedentException(f"CSV ingestion failed: {str(e)}")

    def ingest_evidence_bundles(
        self,
        bundles: List[EvidenceBundle],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """
        Ingest precedents from evidence bundles.

        Args:
            bundles: List of EvidenceBundle objects
            progress_callback: Optional callback for progress updates

        Returns:
            Statistics dictionary with counts
        """
        try:
            logger.info(f"Ingesting {len(bundles)} evidence bundles as precedents")

            precedents = []
            for bundle in bundles:
                precedent = self._evidence_bundle_to_precedent(bundle)
                precedents.append(precedent)

            return self._ingest_batch(precedents, progress_callback)

        except Exception as e:
            logger.error(f"Failed to ingest evidence bundles: {str(e)}")
            raise PrecedentException(f"Evidence bundle ingestion failed: {str(e)}")

    def ingest_from_directory(
        self,
        directory_path: str,
        file_pattern: str = '*.json',
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, int]:
        """
        Ingest all matching files from a directory.

        Args:
            directory_path: Path to directory containing precedent files
            file_pattern: Glob pattern for files to process
            progress_callback: Optional callback for progress updates

        Returns:
            Statistics dictionary with counts
        """
        try:
            logger.info(f"Ingesting precedents from directory: {directory_path}")

            directory = Path(directory_path)
            if not directory.exists():
                raise PrecedentException(f"Directory not found: {directory_path}")

            files = list(directory.glob(file_pattern))
            logger.info(f"Found {len(files)} files matching pattern '{file_pattern}'")

            for file_path in files:
                try:
                    if file_path.suffix == '.json':
                        self.ingest_from_json(str(file_path), progress_callback)
                    elif file_path.suffix == '.jsonl':
                        self.ingest_from_jsonl(str(file_path), progress_callback)
                    elif file_path.suffix == '.csv':
                        self.ingest_from_csv(str(file_path), progress_callback=progress_callback)
                    else:
                        logger.warning(f"Unsupported file type: {file_path}")

                except Exception as e:
                    logger.error(f"Failed to process file {file_path}: {str(e)}")
                    self.stats['errors'] += 1

            return self.stats

        except Exception as e:
            logger.error(f"Failed to ingest from directory: {str(e)}")
            raise PrecedentException(f"Directory ingestion failed: {str(e)}")

    def _ingest_batch(self, precedents: List[Dict[str, Any]], progress_callback: Optional[Callable] = None) -> Dict[str, int]:
        """
        Ingest a batch of precedents.

        Args:
            precedents: List of precedent dictionaries
            progress_callback: Optional callback for progress updates

        Returns:
            Statistics dictionary
        """
        for precedent in precedents:
            self.stats['total'] += 1

            try:
                # Validate if enabled
                if self.validate and not self._validate_precedent(precedent):
                    logger.warning(f"Invalid precedent: {precedent.get('request_id')}")
                    self.stats['errors'] += 1
                    continue

                # Ingest single precedent
                success = self._ingest_precedent(precedent)

                if success:
                    self.stats['ingested'] += 1
                else:
                    self.stats['skipped'] += 1

                # Progress callback
                if progress_callback:
                    progress_callback(self.stats)

            except Exception as e:
                logger.error(f"Failed to ingest precedent: {str(e)}")
                self.stats['errors'] += 1

        return self.stats

    def _ingest_precedent(self, precedent: Dict[str, Any]) -> bool:
        """
        Ingest a single precedent into the store.

        Args:
            precedent: Precedent dictionary

        Returns:
            True if ingested, False if skipped
        """
        try:
            # Extract fields
            request_id = precedent.get('request_id', precedent.get('id', ''))

            # Handle input data structure
            input_data = precedent.get('input', {})
            if isinstance(input_data, dict):
                input_text = input_data.get('text', precedent.get('input_text', ''))
                input_context = input_data.get('context', precedent.get('input_context', {}))
                input_metadata = input_data.get('metadata', precedent.get('input_metadata', {}))
            else:
                input_text = precedent.get('input_text', '')
                input_context = precedent.get('input_context', {})
                input_metadata = precedent.get('input_metadata', {})

            # Handle final decision structure
            final_decision = precedent.get('final_decision', {})
            if isinstance(final_decision, dict):
                final_verdict = final_decision.get('overall_verdict', precedent.get('final_verdict', ''))
                final_reason = final_decision.get('reason', precedent.get('final_reason'))
                avg_confidence = final_decision.get('avg_confidence', precedent.get('avg_confidence'))
                ambiguity = final_decision.get('ambiguity', precedent.get('ambiguity'))
            else:
                final_verdict = precedent.get('final_verdict', '')
                final_reason = precedent.get('final_reason')
                avg_confidence = precedent.get('avg_confidence')
                ambiguity = precedent.get('ambiguity')

            critic_outputs = precedent.get('critic_outputs', [])

            # Parse timestamp
            timestamp_str = precedent.get('timestamp')
            if timestamp_str:
                try:
                    if isinstance(timestamp_str, str):
                        # Handle ISO format
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        timestamp = datetime.utcnow()
                except ValueError:
                    timestamp = datetime.utcnow()
            else:
                timestamp = datetime.utcnow()

            # Generate embedding
            embedding = None
            if input_text:
                try:
                    embedding_vec = embed_text(input_text, self.embedding_model)
                    embedding = pickle.dumps(embedding_vec)
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {str(e)}")

            # Store in SQL backend
            if isinstance(self.store, SQLPrecedentStore):
                self.store.store_precedent(
                    request_id=request_id,
                    input_text=input_text,
                    input_context=input_context,
                    input_metadata=input_metadata,
                    final_verdict=final_verdict,
                    final_reason=final_reason,
                    avg_confidence=avg_confidence,
                    ambiguity=ambiguity,
                    critic_outputs=critic_outputs,
                    embedding=embedding,
                    embedding_model=self.embedding_model,
                    timestamp=timestamp
                )
            # Store in Vector backend
            elif isinstance(self.store, VectorPrecedentManager):
                # Convert to format expected by vector manager
                outcome = {
                    'overall_verdict': final_verdict,
                    'reason': final_reason,
                    'avg_confidence': avg_confidence,
                    'ambiguity': ambiguity
                }
                self.store.store_precedent(
                    decision_id=request_id,
                    input_data={'text': input_text, 'context': input_context},
                    outcome=outcome,
                    timestamp=timestamp.isoformat() if timestamp else None
                )
            else:
                raise PrecedentException(f"Unsupported store type: {type(self.store)}")

            return True

        except Exception as e:
            logger.error(f"Failed to ingest precedent {request_id}: {str(e)}")
            raise

    def _validate_precedent(self, precedent: Dict[str, Any]) -> bool:
        """
        Validate a precedent dictionary.

        Args:
            precedent: Precedent to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        required_fields = ['request_id', 'input_text']

        for field in required_fields:
            # Check both top-level and nested structures
            if field not in precedent:
                if field == 'input_text':
                    input_data = precedent.get('input', {})
                    if not isinstance(input_data, dict) or 'text' not in input_data:
                        return False
                elif field == 'request_id':
                    if 'id' not in precedent:
                        return False
                else:
                    return False

        return True

    def _evidence_bundle_to_precedent(self, bundle: EvidenceBundle) -> Dict[str, Any]:
        """
        Convert an evidence bundle to precedent format.

        Args:
            bundle: EvidenceBundle instance

        Returns:
            Precedent dictionary
        """
        return {
            'request_id': bundle.bundle_id,
            'timestamp': bundle.timestamp,
            'input': {
                'text': bundle.input_snapshot.text,
                'context': bundle.input_snapshot.context,
                'metadata': bundle.input_snapshot.metadata.model_dump()
            },
            'critic_outputs': [
                {
                    'critic': output.critic,
                    'verdict': output.verdict,
                    'confidence': output.confidence,
                    'justification': output.justification,
                    'weight': output.weight,
                    'priority': output.priority
                }
                for output in bundle.critic_outputs
            ],
            'final_decision': {
                # Extract from justification_synthesis if available
                # Otherwise use first critic's verdict as placeholder
                'overall_verdict': bundle.critic_outputs[0].verdict if bundle.critic_outputs else 'REVIEW',
                'reason': bundle.justification_synthesis.summary if bundle.justification_synthesis else None,
                'avg_confidence': bundle.justification_synthesis.confidence_assessment.average_confidence if bundle.justification_synthesis and bundle.justification_synthesis.confidence_assessment else None,
                'ambiguity': None
            }
        }

    def get_stats(self) -> Dict[str, int]:
        """Get current ingestion statistics"""
        return self.stats.copy()


# Convenience functions

def ingest_json_file(
    file_path: str,
    store: Any,
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
) -> Dict[str, int]:
    """
    Convenience function to ingest precedents from a JSON file.

    Args:
        file_path: Path to JSON file
        store: Precedent storage backend
        embedding_model: Embedding model to use

    Returns:
        Statistics dictionary
    """
    pipeline = PrecedentIngestionPipeline(store, embedding_model=embedding_model)
    return pipeline.ingest_from_json(file_path)


def ingest_evidence_bundles_file(
    file_path: str,
    store: Any,
    embedding_model: str = 'sentence-transformers/all-MiniLM-L6-v2'
) -> Dict[str, int]:
    """
    Convenience function to ingest evidence bundles from a JSON file.

    Args:
        file_path: Path to JSON file containing evidence bundles
        store: Precedent storage backend
        embedding_model: Embedding model to use

    Returns:
        Statistics dictionary
    """
    # Load and deserialize bundles
    with open(file_path, 'r') as f:
        bundles_data = json.load(f)

    bundles = []
    for bundle_data in bundles_data:
        bundle = EvidenceBundleSerializer.from_dict(bundle_data)
        bundles.append(bundle)

    pipeline = PrecedentIngestionPipeline(store, embedding_model=embedding_model)
    return pipeline.ingest_evidence_bundles(bundles)
