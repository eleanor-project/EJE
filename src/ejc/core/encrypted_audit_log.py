"""
Encrypted Audit Log with AES-256-GCM encryption at rest

Adds encryption layer on top of SignedAuditLogger for sensitive decision data.
Implements defense-in-depth: encryption + signatures + WORM.

Security Features:
- AES-256-GCM authenticated encryption (AEAD)
- Separate encryption and signing keys
- Key versioning for rotation
- Encrypted data at rest
- Signed ciphertext for tamper detection
- Automatic key derivation from master key
"""

import os
import base64
import json
from typing import Dict, Any, Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .signed_audit_log import SignedAuditLogger, SignedAuditEntry
from ..utils.logging import get_logger


logger = get_logger("ejc.encrypted_audit")


class EncryptedAuditLogger:
    """
    Encrypted audit logger with AES-256-GCM encryption at rest.

    Provides layered security:
    1. Encryption: AES-256-GCM for confidentiality
    2. Authentication: GCM built-in authentication tag
    3. Signatures: HMAC-SHA256 for non-repudiation
    4. WORM: Write-Once-Read-Many storage pattern

    The decision data is encrypted before being signed, providing
    defense-in-depth protection.
    """

    def __init__(
        self,
        db_uri: Optional[str] = None,
        signing_key: Optional[str] = None,
        encryption_key: Optional[str] = None,
        key_version: str = "v1"
    ):
        """
        Initialize encrypted audit logger.

        Args:
            db_uri: Database URI for audit storage
            signing_key: HMAC signing key (from EJC_AUDIT_SIGNING_KEY env)
            encryption_key: AES encryption key (from EJC_AUDIT_ENCRYPTION_KEY env)
            key_version: Key version for rotation support

        Raises:
            ValueError: If encryption key is not provided
        """
        # Load encryption key from environment or parameter
        self.encryption_key_str = encryption_key or os.getenv("EJC_AUDIT_ENCRYPTION_KEY")
        if not self.encryption_key_str:
            raise ValueError(
                "EJC_AUDIT_ENCRYPTION_KEY environment variable not set. "
                "Generate with: python -c 'import secrets; print(secrets.token_hex(32))'"
            )

        # Derive 256-bit key for AES-256
        self.encryption_key = self._derive_key(self.encryption_key_str, key_version)

        # Initialize AESGCM cipher (AES-256-GCM)
        self.cipher = AESGCM(self.encryption_key)

        # Initialize underlying signed audit logger
        self.signed_logger = SignedAuditLogger(
            db_uri=db_uri,
            signing_key=signing_key,
            key_version=key_version
        )

        self.key_version = key_version

        logger.info(f"Encrypted audit logger initialized (key version: {key_version})")
        logger.info("✅ AES-256-GCM encryption enabled for audit logs")

    def _derive_key(self, master_key: str, salt_context: str) -> bytes:
        """
        Derive AES-256 key from master key using PBKDF2.

        Args:
            master_key: Master encryption key (hex string)
            salt_context: Context for key derivation (e.g., key version)

        Returns:
            32-byte AES-256 key
        """
        # Use salt based on context to allow key versioning
        salt = salt_context.encode('utf-8')

        # Derive 32-byte key using PBKDF2-HMAC-SHA256
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 256 bits for AES-256
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
        )

        return kdf.derive(master_key.encode('utf-8'))

    def _encrypt_data(self, data: Dict[str, Any]) -> Dict[str, str]:
        """
        Encrypt decision data using AES-256-GCM.

        Args:
            data: Plaintext decision data

        Returns:
            Dict containing encrypted data and metadata:
            - ciphertext: Base64-encoded encrypted data
            - nonce: Base64-encoded nonce (96 bits)
            - key_version: Key version used for encryption
        """
        # Serialize data to JSON
        plaintext = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')

        # Generate random nonce (96 bits recommended for GCM)
        nonce = os.urandom(12)

        # Encrypt with AES-256-GCM (includes authentication tag)
        ciphertext = self.cipher.encrypt(nonce, plaintext, None)

        return {
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "nonce": base64.b64encode(nonce).decode('utf-8'),
            "key_version": self.key_version,
            "algorithm": "AES-256-GCM"
        }

    def _decrypt_data(self, encrypted_data: Dict[str, str]) -> Dict[str, Any]:
        """
        Decrypt decision data using AES-256-GCM.

        Args:
            encrypted_data: Dict containing ciphertext, nonce, and metadata

        Returns:
            Decrypted decision data dict

        Raises:
            ValueError: If decryption fails (wrong key, tampered data, etc.)
        """
        try:
            # Decode from base64
            ciphertext = base64.b64decode(encrypted_data["ciphertext"])
            nonce = base64.b64decode(encrypted_data["nonce"])

            # Decrypt and verify authentication tag
            plaintext = self.cipher.decrypt(nonce, ciphertext, None)

            # Parse JSON
            return json.loads(plaintext.decode('utf-8'))

        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise ValueError(f"Failed to decrypt audit data: {str(e)}")

    def log_decision(self, decision_bundle: Dict[str, Any]) -> SignedAuditEntry:
        """
        Log a decision with encryption and cryptographic signature.

        Args:
            decision_bundle: Complete decision bundle to log

        Returns:
            Signed audit entry (with encrypted data)

        Raises:
            ValueError: If decision_bundle is invalid
        """
        if not decision_bundle or 'request_id' not in decision_bundle:
            raise ValueError("Invalid decision bundle: missing request_id")

        # Encrypt the decision data
        encrypted_data = self._encrypt_data(decision_bundle)

        # Create wrapper with metadata (this gets signed)
        wrapped_bundle = {
            "request_id": decision_bundle['request_id'],
            "timestamp": decision_bundle['timestamp'],
            "encrypted": True,
            "data": encrypted_data
        }

        # Store encrypted+signed entry
        entry = self.signed_logger.log_decision(wrapped_bundle)

        logger.info(
            f"✅ Encrypted audit entry created: {decision_bundle['request_id']} "
            f"(algorithm: AES-256-GCM, key version: {self.key_version})"
        )

        return entry

    def get_decrypted_entry(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and decrypt an audit entry by request ID.

        Args:
            request_id: Request ID to search for

        Returns:
            Decrypted decision bundle if found, None otherwise

        Raises:
            ValueError: If decryption or signature verification fails
        """
        # Retrieve entry
        entry = self.signed_logger.get_entry_by_request_id(request_id)
        if not entry:
            logger.warning(f"Entry with request_id {request_id} not found")
            return None

        # Verify signature first
        if not self.signed_logger.verify_signature(entry):
            raise ValueError(f"Signature verification failed for entry {request_id} - data may be tampered!")

        # Parse decision data
        wrapped_data = json.loads(entry.decision_data)

        # Check if encrypted
        if not wrapped_data.get("encrypted", False):
            logger.warning(f"Entry {request_id} is not encrypted")
            return wrapped_data

        # Decrypt the data
        encrypted_data = wrapped_data["data"]
        decrypted = self._decrypt_data(encrypted_data)

        logger.info(f"✅ Successfully decrypted entry: {request_id}")
        return decrypted

    def verify_entry(self, request_id: str) -> Dict[str, Any]:
        """
        Verify encryption and signature integrity of an entry.

        Args:
            request_id: Request ID to verify

        Returns:
            Dict with verification results:
            - found: bool
            - signature_valid: bool
            - decryption_successful: bool
            - status: str
        """
        entry = self.signed_logger.get_entry_by_request_id(request_id)

        if not entry:
            return {
                "found": False,
                "signature_valid": False,
                "decryption_successful": False,
                "status": "NOT_FOUND"
            }

        # Verify signature
        signature_valid = self.signed_logger.verify_signature(entry)

        if not signature_valid:
            return {
                "found": True,
                "signature_valid": False,
                "decryption_successful": False,
                "status": "SIGNATURE_INVALID"
            }

        # Try to decrypt
        try:
            self.get_decrypted_entry(request_id)
            return {
                "found": True,
                "signature_valid": True,
                "decryption_successful": True,
                "status": "VALID"
            }
        except Exception as e:
            logger.error(f"Decryption verification failed: {e}")
            return {
                "found": True,
                "signature_valid": True,
                "decryption_successful": False,
                "status": "DECRYPTION_FAILED"
            }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics.

        Returns:
            Dict with statistics including encryption status
        """
        stats = self.signed_logger.get_statistics()
        stats["encryption_enabled"] = True
        stats["encryption_algorithm"] = "AES-256-GCM"
        stats["encryption_key_version"] = self.key_version
        return stats


def create_encrypted_audit_logger(
    db_uri: Optional[str] = None,
    signing_key: Optional[str] = None,
    encryption_key: Optional[str] = None
) -> EncryptedAuditLogger:
    """
    Factory function to create an encrypted audit logger.

    Args:
        db_uri: Database URI for audit storage
        signing_key: HMAC signing key
        encryption_key: AES encryption key

    Returns:
        EncryptedAuditLogger instance
    """
    return EncryptedAuditLogger(
        db_uri=db_uri,
        signing_key=signing_key,
        encryption_key=encryption_key
    )
