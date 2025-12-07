"""
Evidence bundle storage utilities.

Provides high-level functions for storing and retrieving evidence bundles
with decision metadata.
"""

import json
import logging
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib

from .base import ObjectStore

logger = logging.getLogger(__name__)


@dataclass
class EvidenceBundle:
    """Evidence bundle with decision metadata."""

    decision_id: str
    evidence_data: Dict[str, Any]
    created_at: datetime
    evidence_type: str = "decision"
    version: str = "1.0"
    checksum: Optional[str] = None
    metadata: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "decision_id": self.decision_id,
            "evidence_data": self.evidence_data,
            "created_at": self.created_at.isoformat(),
            "evidence_type": self.evidence_type,
            "version": self.version,
            "checksum": self.checksum,
            "metadata": self.metadata or {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceBundle":
        """Create from dictionary."""
        return cls(
            decision_id=data["decision_id"],
            evidence_data=data["evidence_data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            evidence_type=data.get("evidence_type", "decision"),
            version=data.get("version", "1.0"),
            checksum=data.get("checksum"),
            metadata=data.get("metadata"),
        )

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def from_json(cls, json_str: str) -> "EvidenceBundle":
        """Create from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)

    def calculate_checksum(self) -> str:
        """Calculate SHA256 checksum of evidence data."""
        evidence_json = json.dumps(
            self.evidence_data,
            sort_keys=True,
            default=str
        )
        return hashlib.sha256(evidence_json.encode()).hexdigest()


def generate_evidence_key(
    decision_id: str,
    evidence_type: str = "decision",
    prefix: str = "evidence",
) -> str:
    """
    Generate a storage key for an evidence bundle.

    Args:
        decision_id: Decision ID
        evidence_type: Type of evidence
        prefix: Key prefix for organization

    Returns:
        Object key in format: evidence/{type}/{year}/{month}/{decision_id}.json

    Example:
        generate_evidence_key("dec-123", "decision")
        # Returns: "evidence/decision/2024/01/dec-123.json"
    """
    now = datetime.utcnow()
    year = now.strftime("%Y")
    month = now.strftime("%m")

    key = f"{prefix}/{evidence_type}/{year}/{month}/{decision_id}.json"
    return key


def store_evidence_bundle(
    store: ObjectStore,
    bundle: EvidenceBundle,
    key: Optional[str] = None,
    verify_checksum: bool = True,
) -> str:
    """
    Store an evidence bundle in object storage.

    Args:
        store: ObjectStore instance
        bundle: Evidence bundle to store
        key: Optional custom key (auto-generated if None)
        verify_checksum: Whether to calculate and verify checksum

    Returns:
        Object key where bundle was stored

    Example:
        bundle = EvidenceBundle(
            decision_id="dec-123",
            evidence_data={"verdict": "ALLOW", "confidence": 0.95},
            created_at=datetime.utcnow(),
        )

        key = store_evidence_bundle(store, bundle)
        print(f"Stored at: {key}")
    """
    # Generate key if not provided
    if key is None:
        key = generate_evidence_key(
            decision_id=bundle.decision_id,
            evidence_type=bundle.evidence_type,
        )

    # Calculate checksum if requested
    if verify_checksum and bundle.checksum is None:
        bundle.checksum = bundle.calculate_checksum()

    # Convert to JSON
    json_data = bundle.to_json()
    data = json_data.encode("utf-8")

    # Prepare metadata
    metadata = {
        "decision-id": bundle.decision_id,
        "evidence-type": bundle.evidence_type,
        "version": bundle.version,
        "created-at": bundle.created_at.isoformat(),
    }

    if bundle.checksum:
        metadata["checksum"] = bundle.checksum

    # Add custom metadata
    if bundle.metadata:
        metadata.update(bundle.metadata)

    # Upload
    try:
        result = store.put_object(
            key=key,
            data=data,
            content_type="application/json",
            metadata=metadata,
        )

        logger.info(
            f"Stored evidence bundle for decision '{bundle.decision_id}' at '{key}' "
            f"({len(data)} bytes, etag: {result.etag})"
        )

        return key
    except Exception as e:
        logger.error(f"Failed to store evidence bundle: {e}")
        raise


def retrieve_evidence_bundle(
    store: ObjectStore,
    key: Optional[str] = None,
    decision_id: Optional[str] = None,
    evidence_type: str = "decision",
    verify_checksum: bool = True,
) -> Optional[EvidenceBundle]:
    """
    Retrieve an evidence bundle from object storage.

    Args:
        store: ObjectStore instance
        key: Object key (if known)
        decision_id: Decision ID (to auto-generate key)
        evidence_type: Type of evidence
        verify_checksum: Whether to verify checksum

    Returns:
        Evidence bundle or None if not found

    Example:
        # By key
        bundle = retrieve_evidence_bundle(store, key="evidence/decision/2024/01/dec-123.json")

        # By decision ID (tries current month first)
        bundle = retrieve_evidence_bundle(store, decision_id="dec-123")
    """
    # Generate key from decision_id if not provided
    if key is None:
        if decision_id is None:
            raise ValueError("Must provide either key or decision_id")

        key = generate_evidence_key(
            decision_id=decision_id,
            evidence_type=evidence_type,
        )

    try:
        # Download
        data = store.get_object(key=key)
        json_str = data.decode("utf-8")

        # Parse
        bundle = EvidenceBundle.from_json(json_str)

        # Verify checksum if requested
        if verify_checksum and bundle.checksum:
            calculated = bundle.calculate_checksum()
            if calculated != bundle.checksum:
                logger.warning(
                    f"Checksum mismatch for '{key}': "
                    f"expected {bundle.checksum}, got {calculated}"
                )

        logger.info(f"Retrieved evidence bundle from '{key}'")
        return bundle
    except Exception as e:
        logger.error(f"Failed to retrieve evidence bundle from '{key}': {e}")
        return None


def list_evidence_bundles(
    store: ObjectStore,
    evidence_type: str = "decision",
    year: Optional[str] = None,
    month: Optional[str] = None,
    max_results: int = 1000,
) -> List[str]:
    """
    List evidence bundle keys.

    Args:
        store: ObjectStore instance
        evidence_type: Type of evidence
        year: Filter by year (YYYY)
        month: Filter by month (MM)
        max_results: Maximum number of results

    Returns:
        List of object keys

    Example:
        # List all decision bundles
        keys = list_evidence_bundles(store, evidence_type="decision")

        # List for specific month
        keys = list_evidence_bundles(store, year="2024", month="01")
    """
    # Build prefix
    prefix = f"evidence/{evidence_type}"
    if year:
        prefix += f"/{year}"
        if month:
            prefix += f"/{month}"

    try:
        objects = store.list_objects(
            prefix=prefix,
            max_keys=max_results,
        )

        keys = [obj.key for obj in objects]
        logger.info(f"Found {len(keys)} evidence bundles with prefix '{prefix}'")
        return keys
    except Exception as e:
        logger.error(f"Failed to list evidence bundles: {e}")
        return []


def delete_evidence_bundle(
    store: ObjectStore,
    key: Optional[str] = None,
    decision_id: Optional[str] = None,
    evidence_type: str = "decision",
) -> bool:
    """
    Delete an evidence bundle.

    Args:
        store: ObjectStore instance
        key: Object key (if known)
        decision_id: Decision ID (to auto-generate key)
        evidence_type: Type of evidence

    Returns:
        True if deleted, False otherwise

    Example:
        # By key
        deleted = delete_evidence_bundle(store, key="evidence/decision/2024/01/dec-123.json")

        # By decision ID
        deleted = delete_evidence_bundle(store, decision_id="dec-123")
    """
    # Generate key from decision_id if not provided
    if key is None:
        if decision_id is None:
            raise ValueError("Must provide either key or decision_id")

        key = generate_evidence_key(
            decision_id=decision_id,
            evidence_type=evidence_type,
        )

    try:
        result = store.delete_object(key=key)
        if result:
            logger.info(f"Deleted evidence bundle at '{key}'")
        else:
            logger.warning(f"Evidence bundle not found at '{key}'")
        return result
    except Exception as e:
        logger.error(f"Failed to delete evidence bundle at '{key}': {e}")
        return False


def store_attachment(
    store: ObjectStore,
    decision_id: str,
    attachment_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    metadata: Optional[Dict[str, str]] = None,
) -> str:
    """
    Store an attachment associated with a decision.

    Args:
        store: ObjectStore instance
        decision_id: Decision ID
        attachment_name: Name of the attachment
        data: Binary data
        content_type: MIME type
        metadata: Custom metadata

    Returns:
        Object key where attachment was stored

    Example:
        key = store_attachment(
            store=store,
            decision_id="dec-123",
            attachment_name="screenshot.png",
            data=image_bytes,
            content_type="image/png",
        )
    """
    # Generate key
    now = datetime.utcnow()
    year = now.strftime("%Y")
    month = now.strftime("%m")
    key = f"attachments/{year}/{month}/{decision_id}/{attachment_name}"

    # Prepare metadata
    attachment_metadata = {
        "decision-id": decision_id,
        "attachment-name": attachment_name,
    }

    if metadata:
        attachment_metadata.update(metadata)

    try:
        result = store.put_object(
            key=key,
            data=data,
            content_type=content_type,
            metadata=attachment_metadata,
        )

        logger.info(
            f"Stored attachment '{attachment_name}' for decision '{decision_id}' "
            f"at '{key}' ({len(data)} bytes)"
        )

        return key
    except Exception as e:
        logger.error(f"Failed to store attachment: {e}")
        raise


def retrieve_attachment(
    store: ObjectStore,
    key: str,
) -> Optional[bytes]:
    """
    Retrieve an attachment.

    Args:
        store: ObjectStore instance
        key: Object key

    Returns:
        Binary data or None if not found

    Example:
        data = retrieve_attachment(store, key="attachments/2024/01/dec-123/screenshot.png")
    """
    try:
        data = store.get_object(key=key)
        logger.info(f"Retrieved attachment from '{key}' ({len(data)} bytes)")
        return data
    except Exception as e:
        logger.error(f"Failed to retrieve attachment from '{key}': {e}")
        return None


def generate_presigned_url_for_evidence(
    store: ObjectStore,
    decision_id: str,
    evidence_type: str = "decision",
    expiration: int = 3600,
) -> str:
    """
    Generate a presigned URL for evidence bundle access.

    Args:
        store: ObjectStore instance
        decision_id: Decision ID
        evidence_type: Type of evidence
        expiration: URL expiration in seconds

    Returns:
        Presigned URL

    Example:
        url = generate_presigned_url_for_evidence(
            store=store,
            decision_id="dec-123",
            expiration=7200,  # 2 hours
        )
        print(f"Share this URL: {url}")
    """
    key = generate_evidence_key(
        decision_id=decision_id,
        evidence_type=evidence_type,
    )

    try:
        url = store.generate_presigned_url(
            key=key,
            expiration=expiration,
            method="GET",
        )

        logger.info(
            f"Generated presigned URL for evidence '{decision_id}' "
            f"(expires in {expiration}s)"
        )

        return url
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise
