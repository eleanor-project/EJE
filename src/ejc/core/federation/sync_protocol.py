"""
Federated precedent synchronization protocol.

Enables privacy-preserving precedent sharing across distributed EJC nodes
using k-anonymous bundles and consent-based synchronization.

This implements Gap #1 Phase 3: Federated Sync Protocol
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set
from enum import Enum
import json
import hashlib

from ..precedent.privacy import AnonymousBundle, KAnonymityBundler
from ...utils.logging import get_logger


logger = get_logger("ejc.federation.sync")


class SyncStatus(Enum):
    """Status of precedent synchronization."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CONFLICT = "conflict"
    PARTIAL = "partial"


class MigrationStatus(Enum):
    """Migration status for cross-version precedents."""
    NATIVE = "native"  # Created on this node
    MIGRATED = "migrated"  # Successfully migrated from another version
    PARTIAL = "partial"  # Partially migrated (some data loss)
    FAILED = "failed"  # Migration failed


@dataclass
class SyncRequest:
    """Request to synchronize precedent bundles between nodes."""

    request_id: str
    source_node: str
    target_node: str
    bundles: List[Dict[str, Any]]  # Serialized AnonymousBundle objects
    timestamp: str
    protocol_version: str = "1.0"
    consent_verified: bool = True


@dataclass
class SyncResponse:
    """Response to precedent synchronization request."""

    request_id: str
    status: str  # SyncStatus value
    accepted_count: int
    rejected_count: int
    conflict_count: int
    conflicts: List[Dict[str, Any]]
    timestamp: str
    message: Optional[str] = None


@dataclass
class PrecedentConflict:
    """Conflict between local and remote precedent versions."""

    bundle_id: str
    local_version: Dict[str, Any]
    remote_version: Dict[str, Any]
    conflict_reason: str
    resolution_strategy: str  # "keep_local", "keep_remote", "merge"


class FederatedSyncProtocol:
    """
    Manages federated precedent synchronization across EJC nodes.

    Provides privacy-preserving precedent sharing using k-anonymous bundles,
    conflict resolution, and consent verification.
    """

    def __init__(
        self,
        node_id: str,
        bundler: Optional[KAnonymityBundler] = None,
        protocol_version: str = "1.0"
    ):
        """
        Initialize federated sync protocol.

        Args:
            node_id: Unique identifier for this node
            bundler: K-anonymity bundler instance
            protocol_version: Protocol version string
        """
        self.node_id = node_id
        self.bundler = bundler or KAnonymityBundler()
        self.protocol_version = protocol_version

        # Track synced bundles to avoid duplicates
        self.synced_bundle_ids: Set[str] = set()

        # Track sync history
        self.sync_history: List[Dict[str, Any]] = []

    def create_sync_request(
        self,
        bundles: List[AnonymousBundle],
        target_node: str
    ) -> SyncRequest:
        """
        Create synchronization request to send bundles to another node.

        Args:
            bundles: List of k-anonymous bundles to share
            target_node: Target node identifier

        Returns:
            SyncRequest object
        """
        # Serialize bundles
        serialized_bundles = [
            self.bundler.bundle_to_dict(bundle) for bundle in bundles
        ]

        # Generate request ID
        request_id = self._generate_request_id(target_node)

        request = SyncRequest(
            request_id=request_id,
            source_node=self.node_id,
            target_node=target_node,
            bundles=serialized_bundles,
            timestamp=datetime.utcnow().isoformat(),
            protocol_version=self.protocol_version,
            consent_verified=all(b.consent_given for b in bundles)
        )

        logger.info(
            f"Created sync request {request_id} with {len(bundles)} bundles "
            f"for node {target_node}"
        )

        return request

    def process_sync_request(
        self,
        request: SyncRequest,
        existing_bundles: List[AnonymousBundle]
    ) -> SyncResponse:
        """
        Process incoming synchronization request from another node.

        Args:
            request: Incoming sync request
            existing_bundles: Currently stored bundles on this node

        Returns:
            SyncResponse with acceptance/rejection status
        """
        logger.info(
            f"Processing sync request {request.request_id} from {request.source_node}"
        )

        # Validate request
        validation_error = self._validate_sync_request(request)
        if validation_error:
            return SyncResponse(
                request_id=request.request_id,
                status=SyncStatus.REJECTED.value,
                accepted_count=0,
                rejected_count=len(request.bundles),
                conflict_count=0,
                conflicts=[],
                timestamp=datetime.utcnow().isoformat(),
                message=validation_error
            )

        # Deserialize incoming bundles
        incoming_bundles = [
            self.bundler.bundle_from_dict(b) for b in request.bundles
        ]

        # Detect conflicts with existing bundles
        conflicts = self._detect_conflicts(incoming_bundles, existing_bundles)

        # Process each bundle
        accepted = []
        rejected = []

        for bundle in incoming_bundles:
            # Check if already synced
            if bundle.bundle_id in self.synced_bundle_ids:
                logger.debug(f"Bundle {bundle.bundle_id} already synced, skipping")
                continue

            # Verify k-anonymity
            if not self.bundler.verify_k_anonymity(bundle):
                logger.warning(f"Bundle {bundle.bundle_id} failed k-anonymity check")
                rejected.append(bundle.bundle_id)
                continue

            # Check consent
            if not bundle.consent_given:
                logger.warning(f"Bundle {bundle.bundle_id} missing consent")
                rejected.append(bundle.bundle_id)
                continue

            # Accept bundle
            accepted.append(bundle.bundle_id)
            self.synced_bundle_ids.add(bundle.bundle_id)

        # Create response
        response = SyncResponse(
            request_id=request.request_id,
            status=self._determine_sync_status(accepted, rejected, conflicts),
            accepted_count=len(accepted),
            rejected_count=len(rejected),
            conflict_count=len(conflicts),
            conflicts=[asdict(c) for c in conflicts],
            timestamp=datetime.utcnow().isoformat(),
            message=f"Processed {len(accepted)} accepted, {len(rejected)} rejected"
        )

        # Record sync history
        self._record_sync_history(request, response)

        logger.info(
            f"Sync request {request.request_id} completed: "
            f"{response.accepted_count} accepted, {response.rejected_count} rejected"
        )

        return response

    def _validate_sync_request(self, request: SyncRequest) -> Optional[str]:
        """
        Validate incoming sync request.

        Args:
            request: SyncRequest to validate

        Returns:
            Error message if invalid, None if valid
        """
        # Check protocol version
        if request.protocol_version != self.protocol_version:
            return f"Protocol version mismatch: {request.protocol_version} != {self.protocol_version}"

        # Check consent
        if not request.consent_verified:
            return "Consent not verified for precedent sharing"

        # Check target node matches
        if request.target_node != self.node_id:
            return f"Request target {request.target_node} does not match node {self.node_id}"

        # Check bundles present
        if not request.bundles:
            return "No bundles in sync request"

        return None

    def _detect_conflicts(
        self,
        incoming_bundles: List[AnonymousBundle],
        existing_bundles: List[AnonymousBundle]
    ) -> List[PrecedentConflict]:
        """
        Detect conflicts between incoming and existing bundles.

        Args:
            incoming_bundles: Bundles from sync request
            existing_bundles: Bundles already on this node

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Build index of existing bundles
        existing_index = {b.bundle_id: b for b in existing_bundles}

        for incoming in incoming_bundles:
            if incoming.bundle_id in existing_index:
                existing = existing_index[incoming.bundle_id]

                # Check if versions differ
                if self._bundles_differ(incoming, existing):
                    conflict = PrecedentConflict(
                        bundle_id=incoming.bundle_id,
                        local_version=self.bundler.bundle_to_dict(existing),
                        remote_version=self.bundler.bundle_to_dict(incoming),
                        conflict_reason="Bundle with same ID exists but differs",
                        resolution_strategy="keep_local"  # Default: prefer local
                    )
                    conflicts.append(conflict)

        return conflicts

    def _bundles_differ(
        self,
        bundle1: AnonymousBundle,
        bundle2: AnonymousBundle
    ) -> bool:
        """
        Check if two bundles with same ID differ in content.

        Args:
            bundle1, bundle2: Bundles to compare

        Returns:
            True if bundles differ
        """
        # Compare key fields
        if bundle1.precedent_count != bundle2.precedent_count:
            return True

        if bundle1.verdict_distribution != bundle2.verdict_distribution:
            return True

        if abs(bundle1.avg_confidence - bundle2.avg_confidence) > 0.01:
            return True

        return False

    def _determine_sync_status(
        self,
        accepted: List[str],
        rejected: List[str],
        conflicts: List[PrecedentConflict]
    ) -> str:
        """
        Determine overall sync status.

        Args:
            accepted: List of accepted bundle IDs
            rejected: List of rejected bundle IDs
            conflicts: List of conflicts

        Returns:
            SyncStatus value
        """
        total = len(accepted) + len(rejected)

        if conflicts:
            return SyncStatus.CONFLICT.value

        if len(rejected) == total:
            return SyncStatus.REJECTED.value

        if len(accepted) == total:
            return SyncStatus.ACCEPTED.value

        return SyncStatus.PARTIAL.value

    def _generate_request_id(self, target_node: str) -> str:
        """Generate unique request ID."""
        timestamp = datetime.utcnow().isoformat()
        data = f"{self.node_id}-{target_node}-{timestamp}"
        hash_val = hashlib.sha256(data.encode()).hexdigest()
        return f"sync-{hash_val[:16]}"

    def _record_sync_history(
        self,
        request: SyncRequest,
        response: SyncResponse
    ):
        """Record synchronization history."""
        self.sync_history.append({
            "request_id": request.request_id,
            "source_node": request.source_node,
            "bundle_count": len(request.bundles),
            "accepted": response.accepted_count,
            "rejected": response.rejected_count,
            "conflicts": response.conflict_count,
            "status": response.status,
            "timestamp": response.timestamp
        })

        # Keep last 1000 sync records
        if len(self.sync_history) > 1000:
            self.sync_history = self.sync_history[-1000:]

    def resolve_conflict(
        self,
        conflict: PrecedentConflict,
        strategy: str = "keep_local"
    ) -> Dict[str, Any]:
        """
        Resolve precedent conflict.

        Args:
            conflict: PrecedentConflict to resolve
            strategy: Resolution strategy
                - "keep_local": Keep existing local version
                - "keep_remote": Accept remote version
                - "merge": Merge both versions (if possible)

        Returns:
            Resolved bundle dict
        """
        if strategy == "keep_local":
            logger.info(f"Resolving conflict {conflict.bundle_id}: keeping local version")
            return conflict.local_version

        elif strategy == "keep_remote":
            logger.info(f"Resolving conflict {conflict.bundle_id}: accepting remote version")
            return conflict.remote_version

        elif strategy == "merge":
            logger.info(f"Resolving conflict {conflict.bundle_id}: merging versions")
            return self._merge_bundles(conflict.local_version, conflict.remote_version)

        else:
            logger.warning(f"Unknown resolution strategy: {strategy}, defaulting to keep_local")
            return conflict.local_version

    def _merge_bundles(
        self,
        local: Dict[str, Any],
        remote: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Merge two bundle versions.

        Args:
            local: Local bundle dict
            remote: Remote bundle dict

        Returns:
            Merged bundle dict
        """
        # Merge verdict distributions
        merged_verdicts = {}
        all_verdicts = set(local.get("verdict_distribution", {}).keys()) | \
                       set(remote.get("verdict_distribution", {}).keys())

        for verdict in all_verdicts:
            local_count = local.get("verdict_distribution", {}).get(verdict, 0)
            remote_count = remote.get("verdict_distribution", {}).get(verdict, 0)
            merged_verdicts[verdict] = local_count + remote_count

        # Average confidence
        local_conf = local.get("avg_confidence", 0.5)
        remote_conf = remote.get("avg_confidence", 0.5)
        merged_confidence = (local_conf + remote_conf) / 2.0

        # Combine themes
        local_themes = set(local.get("common_themes", []))
        remote_themes = set(remote.get("common_themes", []))
        merged_themes = list(local_themes | remote_themes)

        # Create merged bundle
        merged = local.copy()
        merged.update({
            "verdict_distribution": merged_verdicts,
            "avg_confidence": merged_confidence,
            "common_themes": merged_themes,
            "precedent_count": local.get("precedent_count", 0) + remote.get("precedent_count", 0),
            "merged": True,
            "merge_timestamp": datetime.utcnow().isoformat()
        })

        return merged

    def get_sync_statistics(self) -> Dict[str, Any]:
        """
        Get synchronization statistics.

        Returns:
            Dict with sync stats
        """
        if not self.sync_history:
            return {
                "total_syncs": 0,
                "total_accepted": 0,
                "total_rejected": 0,
                "total_conflicts": 0,
                "unique_nodes": []
            }

        total_accepted = sum(r["accepted"] for r in self.sync_history)
        total_rejected = sum(r["rejected"] for r in self.sync_history)
        total_conflicts = sum(r["conflicts"] for r in self.sync_history)

        unique_nodes = list(set(r["source_node"] for r in self.sync_history))

        return {
            "node_id": self.node_id,
            "total_syncs": len(self.sync_history),
            "total_accepted": total_accepted,
            "total_rejected": total_rejected,
            "total_conflicts": total_conflicts,
            "unique_nodes": unique_nodes,
            "synced_bundle_count": len(self.synced_bundle_ids),
            "last_sync": self.sync_history[-1]["timestamp"] if self.sync_history else None
        }

    def export_sync_history(self, filepath: str):
        """Export sync history to JSON file."""
        with open(filepath, 'w') as f:
            json.dump({
                "node_id": self.node_id,
                "export_timestamp": datetime.utcnow().isoformat(),
                "sync_history": self.sync_history
            }, f, indent=2)

        logger.info(f"Exported sync history to {filepath}")
