"""
Ethical Jurisprudence Core (EJC)
Part of the Mutual Intelligence Framework (MIF)

Signed Audit Log implementing RBJA security requirements.
Provides cryptographic signatures for tamper detection and audit trail integrity.

This module implements Gap #7 from the ELEANOR Spec v2.1 feature gap analysis.
"""

import hmac
import hashlib
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from ..utils.logging import get_logger
from ..utils.filepaths import ensure_dir

Base = declarative_base()


class SignedAuditEntry(Base):
    """
    Signed audit entry with cryptographic signature for tamper detection.
    Implements WORM (Write-Once-Read-Many) pattern at application level.
    """
    __tablename__ = 'signed_audit_log'

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(64), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Decision data (stored as JSON)
    decision_data = Column(Text, nullable=False)

    # Cryptographic signature (HMAC-SHA256)
    signature = Column(String(64), nullable=False)

    # Signing key version (for key rotation support)
    key_version = Column(String(16), nullable=False, default="v1")

    # Metadata
    version = Column(String(16), nullable=False, default="1.0")

    def __repr__(self):
        return f"<SignedAuditEntry(id={self.id}, request_id={self.request_id}, timestamp={self.timestamp})>"


class SignedAuditLogger:
    """
    Ethical Jurisprudence Core (EJC)
    Part of the Mutual Intelligence Framework (MIF)

    Cryptographically signed audit logger implementing RBJA security requirements.

    Features:
    - HMAC-SHA256 signatures for tamper detection
    - Key versioning for rotation support
    - Integrity verification
    - WORM (Write-Once-Read-Many) enforcement
    - Append-only operations

    Security Properties:
    - Tamper-evident: Any modification to log entries is detectable
    - Non-repudiation: Signed entries cannot be denied
    - Integrity: Complete audit trail verification
    """

    def __init__(
        self,
        db_uri: Optional[str] = None,
        signing_key: Optional[str] = None,
        key_version: str = "v1"
    ) -> None:
        """
        Initialize signed audit logger.

        Args:
            db_uri: Database URI (defaults to SQLite)
            signing_key: HMAC signing key (loaded from env if not provided)
            key_version: Key version identifier for rotation
        """
        self.logger = get_logger("EJC.SignedAuditLogger")

        # Load signing key from environment or parameter
        self.signing_key = signing_key or os.getenv("EJC_AUDIT_SIGNING_KEY")
        if not self.signing_key:
            raise ValueError(
                "EJC_AUDIT_SIGNING_KEY environment variable not set. "
                "Set it to a secure random string (e.g., output of: openssl rand -hex 32)"
            )

        self.signing_key_bytes = self.signing_key.encode('utf-8')
        self.key_version = key_version

        # Setup database
        if db_uri is None:
            # Default to SQLite in eleanor_data directory
            data_dir = "./eleanor_data"
            ensure_dir(data_dir)
            db_uri = f"sqlite:///{data_dir}/signed_audit_log.db"

        self.engine = create_engine(db_uri, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        self.logger.info(f"Signed audit logger initialized (key version: {key_version})")
        self.logger.info("✅ Cryptographic signatures enabled for tamper detection")

    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        Generate HMAC-SHA256 signature for audit entry.

        Args:
            data: Decision data to sign

        Returns:
            Hex-encoded HMAC-SHA256 signature
        """
        # Serialize data in canonical form (sorted keys for determinism)
        data_json = json.dumps(data, sort_keys=True, separators=(',', ':'))

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.signing_key_bytes,
            data_json.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return signature

    def verify_signature(self, entry: SignedAuditEntry) -> bool:
        """
        Verify the cryptographic signature of an audit entry.

        Args:
            entry: Audit entry to verify

        Returns:
            True if signature is valid, False if tampered
        """
        try:
            # Parse the decision data
            data = json.loads(entry.decision_data)

            # Recompute signature
            expected_signature = self._generate_signature(data)

            # Use constant-time comparison to prevent timing attacks
            return hmac.compare_digest(entry.signature, expected_signature)
        except Exception as e:
            self.logger.error(f"Signature verification failed: {e}")
            return False

    def log_decision(self, decision_bundle: Dict[str, Any]) -> SignedAuditEntry:
        """
        Log a decision with cryptographic signature.

        Args:
            decision_bundle: Complete decision bundle from EthicalReasoningEngine

        Returns:
            The signed audit entry

        Raises:
            ValueError: If decision_bundle is invalid
        """
        if not decision_bundle or 'request_id' not in decision_bundle:
            raise ValueError("Invalid decision bundle: missing request_id")

        # Generate signature
        signature = self._generate_signature(decision_bundle)

        # Create signed entry
        entry = SignedAuditEntry(
            request_id=decision_bundle['request_id'],
            timestamp=datetime.fromisoformat(decision_bundle['timestamp']),
            decision_data=json.dumps(decision_bundle, separators=(',', ':')),
            signature=signature,
            key_version=self.key_version,
            version="1.0"
        )

        # Store in database (WORM - Write Once Read Many)
        session = self.Session()
        try:
            session.add(entry)
            session.commit()

            self.logger.info(
                f"✅ Signed audit entry created: {entry.request_id} "
                f"(signature: {signature[:16]}...)"
            )

            return entry
        except Exception as e:
            session.rollback()
            self.logger.error(f"Failed to log decision: {e}")
            raise
        finally:
            session.close()

    def verify_entry_by_id(self, entry_id: int) -> bool:
        """
        Verify an audit entry by ID.

        Args:
            entry_id: Database ID of the entry

        Returns:
            True if signature is valid, False if tampered or not found
        """
        session = self.Session()
        try:
            entry = session.query(SignedAuditEntry).filter_by(id=entry_id).first()
            if not entry:
                self.logger.warning(f"Entry {entry_id} not found")
                return False

            is_valid = self.verify_signature(entry)
            if is_valid:
                self.logger.info(f"✅ Entry {entry_id} signature valid")
            else:
                self.logger.error(f"❌ Entry {entry_id} TAMPERED - signature invalid!")

            return is_valid
        finally:
            session.close()

    def verify_all_entries(self) -> Dict[str, Any]:
        """
        Verify all audit entries in the database.

        Returns:
            dict: Verification statistics
        """
        session = self.Session()
        try:
            all_entries = session.query(SignedAuditEntry).all()

            total = len(all_entries)
            valid = 0
            tampered = 0

            tampered_ids = []

            for entry in all_entries:
                if self.verify_signature(entry):
                    valid += 1
                else:
                    tampered += 1
                    tampered_ids.append(entry.id)

            results = {
                "total_entries": total,
                "valid_signatures": valid,
                "tampered_entries": tampered,
                "tampered_ids": tampered_ids,
                "integrity_status": "INTACT" if tampered == 0 else "COMPROMISED"
            }

            if tampered == 0:
                self.logger.info(f"✅ All {total} audit entries verified successfully")
            else:
                self.logger.error(
                    f"❌ SECURITY ALERT: {tampered}/{total} entries have invalid signatures! "
                    f"Tampered IDs: {tampered_ids}"
                )

            return results
        finally:
            session.close()

    def get_entry_by_request_id(self, request_id: str) -> Optional[SignedAuditEntry]:
        """
        Retrieve an audit entry by request ID.

        Args:
            request_id: Request ID to search for

        Returns:
            SignedAuditEntry if found, None otherwise
        """
        session = self.Session()
        try:
            return session.query(SignedAuditEntry).filter_by(
                request_id=request_id
            ).first()
        finally:
            session.close()

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Returns:
            dict: Statistics including total entries, key versions, etc.
        """
        session = self.Session()
        try:
            total = session.query(SignedAuditEntry).count()

            # Get entries by key version
            key_versions = {}
            for version in session.query(SignedAuditEntry.key_version).distinct():
                count = session.query(SignedAuditEntry).filter_by(
                    key_version=version[0]
                ).count()
                key_versions[version[0]] = count

            return {
                "total_entries": total,
                "key_versions": key_versions,
                "current_key_version": self.key_version,
                "security_status": "ENABLED"
            }
        finally:
            session.close()


# Convenience function for backward compatibility
def create_signed_audit_logger(
    db_uri: Optional[str] = None,
    signing_key: Optional[str] = None
) -> SignedAuditLogger:
    """
    Factory function to create a signed audit logger.

    Args:
        db_uri: Database URI (defaults to SQLite)
        signing_key: HMAC signing key (loaded from env if not provided)

    Returns:
        SignedAuditLogger instance
    """
    return SignedAuditLogger(db_uri=db_uri, signing_key=signing_key)
