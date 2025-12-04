"""
Metadata Enrichment for Evidence Bundles

Adds system metadata for observability, policy checks, and audit trails.
Includes timestamp generation, execution timing, config tracking, and system info.

Task 1.3: Add Metadata Enrichment
"""

import os
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("ejc.core.metadata_enricher")


class MetadataEnricher:
    """
    Enriches evidence bundles with system metadata for observability and audit.

    Provides consistent metadata generation across all evidence bundles including
    timestamps, execution metrics, configuration versions, and system information.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Metadata Enricher.

        Args:
            config: Optional configuration dict
        """
        self.config = config or {}
        self.config_version = self.config.get("config_version", "1.0")
        self.node_id = self.config.get("node_id", self._generate_node_id())
        self.hostname = socket.gethostname()
        self.process_id = os.getpid()

    def enrich(
        self,
        bundle: Dict[str, Any],
        execution_start_time: Optional[float] = None,
        aggregator_run_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich evidence bundle with metadata.

        Args:
            bundle: Evidence bundle dict (will be modified in-place)
            execution_start_time: Start time from time.time() for timing calculation
            aggregator_run_id: Optional aggregator run ID
            request_id: Optional original request ID

        Returns:
            Enriched bundle (same object as input)
        """
        # Ensure metadata section exists
        if "metadata" not in bundle:
            bundle["metadata"] = {}

        metadata = bundle["metadata"]

        # Add or update timestamp (ISO 8601 with Z suffix)
        if "timestamp" not in metadata:
            metadata["timestamp"] = self._generate_timestamp()

        # Add execution timing if start time provided
        if execution_start_time is not None:
            execution_time_ms = (time.time() - execution_start_time) * 1000.0
            metadata["execution_time_ms"] = round(execution_time_ms, 2)
        elif "execution_time_ms" not in metadata:
            # Default to 0 if not provided (better than missing)
            metadata["execution_time_ms"] = 0.0

        # Add config version
        if "config_version" not in metadata:
            metadata["config_version"] = self.config_version

        # Add aggregator run ID
        if aggregator_run_id:
            metadata["aggregator_run_id"] = aggregator_run_id
        elif "aggregator_run_id" not in metadata:
            # Generate one if not provided
            metadata["aggregator_run_id"] = self._generate_aggregator_run_id()

        # Add request ID if provided
        if request_id:
            metadata["request_id"] = request_id

        # Add trace ID for distributed tracing if not present
        if "trace_id" not in metadata:
            metadata["trace_id"] = self._generate_trace_id()

        # Add system info
        if "system_info" not in metadata:
            metadata["system_info"] = self._generate_system_info()

        logger.debug(f"Enriched bundle {bundle.get('bundle_id', 'unknown')}")
        return bundle

    def enrich_batch(
        self,
        bundles: list,
        execution_times: Optional[Dict[str, float]] = None,
        aggregator_run_id: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> list:
        """
        Enrich multiple bundles with consistent metadata.

        Args:
            bundles: List of evidence bundle dicts
            execution_times: Optional dict mapping bundle_id to start time
            aggregator_run_id: Shared aggregator run ID
            request_id: Shared request ID

        Returns:
            List of enriched bundles
        """
        # Generate shared aggregator run ID if not provided
        if not aggregator_run_id:
            aggregator_run_id = self._generate_aggregator_run_id()

        execution_times = execution_times or {}

        for bundle in bundles:
            bundle_id = bundle.get("bundle_id")
            start_time = execution_times.get(bundle_id) if bundle_id else None

            self.enrich(
                bundle,
                execution_start_time=start_time,
                aggregator_run_id=aggregator_run_id,
                request_id=request_id
            )

        logger.info(f"Enriched {len(bundles)} bundles with run ID {aggregator_run_id}")
        return bundles

    def _generate_timestamp(self) -> str:
        """
        Generate ISO 8601 timestamp with microseconds and Z suffix.

        Returns:
            ISO 8601 timestamp string (e.g., "2025-12-04T10:30:00.123456Z")
        """
        now = datetime.now(timezone.utc)
        # Format with microseconds and Z suffix
        return now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def _generate_aggregator_run_id(self) -> str:
        """
        Generate unique aggregator run ID.

        Returns:
            Aggregator run ID string
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"agg-run-{timestamp}-{unique_id}"

    def _generate_trace_id(self) -> str:
        """
        Generate distributed tracing ID.

        Uses W3C Trace Context format (simplified version).

        Returns:
            Trace ID string
        """
        # Generate 32-character hex trace ID
        trace_id = uuid.uuid4().hex
        # Generate 16-character hex span ID
        span_id = uuid.uuid4().hex[:16]
        # Format as W3C traceparent (version-traceid-spanid-flags)
        return f"00-{trace_id}-{span_id}-01"

    def _generate_system_info(self) -> Dict[str, Any]:
        """
        Generate system information dict.

        Returns:
            System info dict with hostname, process_id, node_id
        """
        return {
            "hostname": self.hostname,
            "process_id": self.process_id,
            "node_id": self.node_id
        }

    def _generate_node_id(self) -> str:
        """
        Generate unique node identifier for federated deployments.

        Returns:
            Node ID string
        """
        # Use hostname + MAC address for stable node ID
        try:
            import hashlib
            node_data = f"{socket.gethostname()}-{uuid.getnode()}"
            hash_val = hashlib.sha256(node_data.encode()).hexdigest()[:16]
            return f"node-{hash_val}"
        except Exception:
            # Fallback to random ID
            return f"node-{uuid.uuid4().hex[:16]}"

    def add_execution_timing(
        self,
        bundle: Dict[str, Any],
        start_time: float
    ) -> Dict[str, Any]:
        """
        Add execution timing to existing bundle.

        Args:
            bundle: Evidence bundle dict
            start_time: Start time from time.time()

        Returns:
            Bundle with timing added
        """
        execution_time_ms = (time.time() - start_time) * 1000.0

        if "metadata" not in bundle:
            bundle["metadata"] = {}

        bundle["metadata"]["execution_time_ms"] = round(execution_time_ms, 2)
        return bundle

    def set_aggregator_run_id(
        self,
        bundle: Dict[str, Any],
        run_id: str
    ) -> Dict[str, Any]:
        """
        Set aggregator run ID on bundle.

        Args:
            bundle: Evidence bundle dict
            run_id: Aggregator run ID

        Returns:
            Bundle with run ID set
        """
        if "metadata" not in bundle:
            bundle["metadata"] = {}

        bundle["metadata"]["aggregator_run_id"] = run_id
        return bundle

    def set_request_id(
        self,
        bundle: Dict[str, Any],
        request_id: str
    ) -> Dict[str, Any]:
        """
        Set original request ID on bundle.

        Args:
            bundle: Evidence bundle dict
            request_id: Request ID

        Returns:
            Bundle with request ID set
        """
        if "metadata" not in bundle:
            bundle["metadata"] = {}

        bundle["metadata"]["request_id"] = request_id
        return bundle

    def get_execution_time(self, bundle: Dict[str, Any]) -> Optional[float]:
        """
        Extract execution time from bundle.

        Args:
            bundle: Evidence bundle dict

        Returns:
            Execution time in milliseconds, or None if not present
        """
        return bundle.get("metadata", {}).get("execution_time_ms")

    def get_timestamp(self, bundle: Dict[str, Any]) -> Optional[str]:
        """
        Extract timestamp from bundle.

        Args:
            bundle: Evidence bundle dict

        Returns:
            ISO 8601 timestamp string, or None if not present
        """
        return bundle.get("metadata", {}).get("timestamp")


class ExecutionTimer:
    """
    Context manager for timing critic execution.

    Usage:
        with ExecutionTimer() as timer:
            # Execute critic
            result = critic.evaluate(case)

        execution_time = timer.elapsed_ms
    """

    def __init__(self):
        """Initialize execution timer."""
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing."""
        self.end_time = time.time()
        return False  # Don't suppress exceptions

    @property
    def elapsed_ms(self) -> float:
        """
        Get elapsed time in milliseconds.

        Returns:
            Elapsed milliseconds
        """
        if self.start_time is None:
            return 0.0

        end = self.end_time if self.end_time is not None else time.time()
        return (end - self.start_time) * 1000.0

    @property
    def start_timestamp(self) -> float:
        """
        Get start timestamp.

        Returns:
            Start time from time.time()
        """
        return self.start_time if self.start_time is not None else 0.0


def enrich_bundle_metadata(
    bundle: Dict[str, Any],
    execution_start: Optional[float] = None,
    aggregator_run_id: Optional[str] = None,
    request_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience function for enriching bundle metadata.

    Args:
        bundle: Evidence bundle dict
        execution_start: Start time from time.time()
        aggregator_run_id: Optional aggregator run ID
        request_id: Optional request ID
        config: Optional configuration dict

    Returns:
        Enriched bundle
    """
    enricher = MetadataEnricher(config)
    return enricher.enrich(bundle, execution_start, aggregator_run_id, request_id)
