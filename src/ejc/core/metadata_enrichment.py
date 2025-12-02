"""
Metadata Enrichment Module

Enriches evidence bundles with system metadata including timestamps,
execution statistics, configuration versions, and audit information.
"""

import os
import platform
import time
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ExecutionStats(BaseModel):
    """Statistics about critic execution"""
    critic_name: str
    start_time: float
    end_time: float
    duration_ms: float
    success: bool
    error_message: Optional[str] = None


class ConfigSnapshot(BaseModel):
    """Snapshot of configuration at execution time"""
    system_version: str
    config_version: str
    critic_versions: Dict[str, str] = Field(default_factory=dict)
    environment: str
    deployment_id: Optional[str] = None


class SystemMetadata(BaseModel):
    """System-level metadata"""
    hostname: Optional[str] = None
    process_id: int
    platform: str
    python_version: str


class MetadataEnricher:
    """
    Enriches evidence bundles with comprehensive metadata.

    Handles:
    - Timestamp generation and tracking
    - Execution timing and statistics
    - Configuration version tracking
    - System and environment metadata
    - Correlation IDs for distributed tracing
    """

    def __init__(
        self,
        system_version: str = "1.0.0",
        config_version: str = "1.0.0",
        environment: str = "development",
        deployment_id: Optional[str] = None
    ):
        """
        Initialize the metadata enricher.

        Args:
            system_version: Version of the EJE system
            config_version: Version of the configuration
            environment: Deployment environment
            deployment_id: Unique deployment identifier
        """
        self.system_version = system_version
        self.config_version = config_version
        self.environment = environment
        self.deployment_id = deployment_id or str(uuid.uuid4())
        self.system_metadata = self._capture_system_metadata()

    def _capture_system_metadata(self) -> SystemMetadata:
        """Capture system-level metadata"""
        try:
            hostname = platform.node()
        except Exception:
            hostname = None

        return SystemMetadata(
            hostname=hostname,
            process_id=os.getpid(),
            platform=platform.system(),
            python_version=platform.python_version()
        )

    def generate_correlation_id(self) -> str:
        """
        Generate a unique correlation ID for distributed tracing.

        Returns:
            UUID-based correlation ID
        """
        return str(uuid.uuid4())

    def generate_run_id(self) -> str:
        """
        Generate a unique aggregator run ID.

        Returns:
            UUID-based run ID
        """
        return str(uuid.uuid4())

    def create_timestamp(self) -> str:
        """
        Create an ISO 8601 formatted timestamp.

        Returns:
            Current UTC timestamp in ISO 8601 format
        """
        return datetime.utcnow().isoformat() + "Z"

    def enrich_bundle_metadata(
        self,
        bundle_data: Dict[str, Any],
        correlation_id: Optional[str] = None,
        run_id: Optional[str] = None,
        execution_stats: Optional[List[ExecutionStats]] = None
    ) -> Dict[str, Any]:
        """
        Enrich evidence bundle with comprehensive metadata.

        Args:
            bundle_data: Raw evidence bundle data
            correlation_id: Optional correlation ID (generated if not provided)
            run_id: Optional run ID (generated if not provided)
            execution_stats: Optional execution statistics

        Returns:
            Enriched bundle data with metadata
        """
        # Ensure metadata section exists
        if 'metadata' not in bundle_data:
            bundle_data['metadata'] = {}

        metadata = bundle_data['metadata']

        # Add timestamps
        current_time = self.create_timestamp()
        if 'created_at' not in metadata:
            metadata['created_at'] = current_time
        metadata['updated_at'] = current_time

        # Add system version
        metadata['system_version'] = self.system_version

        # Add environment
        metadata['environment'] = self.environment

        # Add correlation ID
        if correlation_id:
            metadata['correlation_id'] = correlation_id
        elif 'correlation_id' not in metadata:
            metadata['correlation_id'] = self.generate_correlation_id()

        # Add run ID if provided
        if run_id:
            if 'run_id' not in metadata:
                metadata['run_id'] = run_id

        # Add deployment ID
        metadata['deployment_id'] = self.deployment_id

        # Add system metadata
        metadata['system'] = self.system_metadata.model_dump()

        # Add execution statistics if provided
        if execution_stats:
            metadata['execution_stats'] = [stat.model_dump() for stat in execution_stats]

            # Calculate total processing time from execution stats
            if execution_stats:
                total_duration = sum(stat.duration_ms for stat in execution_stats)
                metadata['processing_time_ms'] = total_duration

        # Add config snapshot
        metadata['config_snapshot'] = ConfigSnapshot(
            system_version=self.system_version,
            config_version=self.config_version,
            environment=self.environment,
            deployment_id=self.deployment_id
        ).model_dump()

        return bundle_data

    def track_critic_execution(
        self,
        critic_name: str
    ) -> 'CriticExecutionTracker':
        """
        Create a context manager for tracking critic execution.

        Args:
            critic_name: Name of the critic being executed

        Returns:
            CriticExecutionTracker context manager
        """
        return CriticExecutionTracker(critic_name)

    def enrich_critic_config_versions(
        self,
        bundle_data: Dict[str, Any],
        critic_versions: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Enrich bundle with critic configuration versions.

        Args:
            bundle_data: Evidence bundle data
            critic_versions: Mapping of critic names to config versions

        Returns:
            Enriched bundle data
        """
        if 'metadata' not in bundle_data:
            bundle_data['metadata'] = {}

        bundle_data['metadata']['critic_config_versions'] = critic_versions

        # Also update config snapshot if it exists
        if 'config_snapshot' in bundle_data['metadata']:
            bundle_data['metadata']['config_snapshot']['critic_versions'] = critic_versions

        return bundle_data

    def add_precedent_references(
        self,
        bundle_data: Dict[str, Any],
        precedent_refs: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Add precedent references to bundle metadata.

        Args:
            bundle_data: Evidence bundle data
            precedent_refs: List of precedent references

        Returns:
            Enriched bundle data
        """
        if 'metadata' not in bundle_data:
            bundle_data['metadata'] = {}

        bundle_data['metadata']['precedent_refs'] = precedent_refs

        return bundle_data

    def set_flags(
        self,
        bundle_data: Dict[str, Any],
        requires_human_review: bool = False,
        is_override: bool = False,
        is_fallback: bool = False,
        is_test: bool = False
    ) -> Dict[str, Any]:
        """
        Set operational flags in bundle metadata.

        Args:
            bundle_data: Evidence bundle data
            requires_human_review: Whether bundle requires human review
            is_override: Whether decision was overridden
            is_fallback: Whether fallback logic was used
            is_test: Whether this is a test bundle

        Returns:
            Enriched bundle data
        """
        if 'metadata' not in bundle_data:
            bundle_data['metadata'] = {}

        bundle_data['metadata']['flags'] = {
            'requires_human_review': requires_human_review,
            'is_override': is_override,
            'is_fallback': is_fallback,
            'is_test': is_test
        }

        return bundle_data

    def add_audit_trail_entry(
        self,
        bundle_data: Dict[str, Any],
        action: str,
        actor: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add an entry to the bundle's audit trail.

        Args:
            bundle_data: Evidence bundle data
            action: Action performed
            actor: Who performed the action
            details: Additional details about the action

        Returns:
            Enriched bundle data
        """
        if 'metadata' not in bundle_data:
            bundle_data['metadata'] = {}

        if 'audit_trail' not in bundle_data['metadata']:
            bundle_data['metadata']['audit_trail'] = []

        audit_entry = {
            'timestamp': self.create_timestamp(),
            'action': action,
            'actor': actor,
            'details': details or {}
        }

        bundle_data['metadata']['audit_trail'].append(audit_entry)

        return bundle_data


class CriticExecutionTracker:
    """
    Context manager for tracking critic execution timing.

    Usage:
        with enricher.track_critic_execution("bias_critic") as tracker:
            # Execute critic
            result = critic.evaluate(input)

        stats = tracker.get_stats()
    """

    def __init__(self, critic_name: str):
        self.critic_name = critic_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.success: bool = False
        self.error_message: Optional[str] = None

    def __enter__(self) -> 'CriticExecutionTracker':
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        if exc_type is None:
            self.success = True
        else:
            self.success = False
            self.error_message = str(exc_val) if exc_val else "Unknown error"
        return False  # Don't suppress exceptions

    def get_stats(self) -> ExecutionStats:
        """
        Get execution statistics.

        Returns:
            ExecutionStats object

        Raises:
            ValueError: If tracker hasn't completed execution
        """
        if self.start_time is None or self.end_time is None:
            raise ValueError("Execution not completed")

        duration_ms = (self.end_time - self.start_time) * 1000

        return ExecutionStats(
            critic_name=self.critic_name,
            start_time=self.start_time,
            end_time=self.end_time,
            duration_ms=duration_ms,
            success=self.success,
            error_message=self.error_message
        )


# Convenience functions for common metadata operations
def create_enricher_from_config(config: Dict[str, Any]) -> MetadataEnricher:
    """
    Create a metadata enricher from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured MetadataEnricher instance
    """
    return MetadataEnricher(
        system_version=config.get('system_version', '1.0.0'),
        config_version=config.get('config_version', '1.0.0'),
        environment=config.get('environment', 'development'),
        deployment_id=config.get('deployment_id')
    )


def enrich_with_timing(
    bundle_data: Dict[str, Any],
    start_time: float,
    end_time: float
) -> Dict[str, Any]:
    """
    Enrich bundle with timing information.

    Args:
        bundle_data: Evidence bundle data
        start_time: Start timestamp (from time.time())
        end_time: End timestamp (from time.time())

    Returns:
        Enriched bundle data
    """
    if 'metadata' not in bundle_data:
        bundle_data['metadata'] = {}

    duration_ms = (end_time - start_time) * 1000
    bundle_data['metadata']['processing_time_ms'] = duration_ms

    return bundle_data
