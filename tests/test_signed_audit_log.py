"""
Tests for SignedAuditLogger - Gap #7 Implementation
Cryptographic signature verification and tamper detection
"""

import pytest
import os
import json
from datetime import datetime
from ejc.core.signed_audit_log import SignedAuditLogger, SignedAuditEntry


@pytest.fixture
def test_signing_key():
    """Provide a test signing key"""
    return "test_key_for_hmac_signatures_do_not_use_in_production_12345678"


@pytest.fixture
def signed_logger(test_signing_key, tmp_path):
    """Create a signed audit logger with temporary database"""
    db_uri = f"sqlite:///{tmp_path}/test_audit.db"
    return SignedAuditLogger(db_uri=db_uri, signing_key=test_signing_key)


@pytest.fixture
def sample_decision():
    """Sample decision bundle for testing"""
    return {
        "request_id": "test-request-123",
        "timestamp": datetime.utcnow().isoformat(),
        "input": {"text": "Test case"},
        "critic_outputs": [
            {
                "critic": "TestCritic",
                "verdict": "ALLOW",
                "confidence": 0.95,
                "justification": "Test justification"
            }
        ],
        "final_decision": {
            "overall_verdict": "ALLOW",
            "avg_confidence": 0.95
        },
        "precedent_refs": []
    }


class TestSignedAuditLogger:
    """Test suite for cryptographically signed audit logging"""

    def test_initialization_with_key(self, test_signing_key, tmp_path):
        """Test logger initialization with explicit signing key"""
        db_uri = f"sqlite:///{tmp_path}/test_init.db"
        logger = SignedAuditLogger(db_uri=db_uri, signing_key=test_signing_key)

        assert logger.signing_key == test_signing_key
        assert logger.key_version == "v1"

    def test_initialization_from_env(self, test_signing_key, tmp_path, monkeypatch):
        """Test logger initialization with key from environment"""
        monkeypatch.setenv("EJC_AUDIT_SIGNING_KEY", test_signing_key)

        db_uri = f"sqlite:///{tmp_path}/test_env.db"
        logger = SignedAuditLogger(db_uri=db_uri)

        assert logger.signing_key == test_signing_key

    def test_missing_signing_key_raises_error(self, tmp_path, monkeypatch):
        """Test that missing signing key raises ValueError"""
        monkeypatch.delenv("EJC_AUDIT_SIGNING_KEY", raising=False)

        db_uri = f"sqlite:///{tmp_path}/test_missing_key.db"

        with pytest.raises(ValueError, match="EJC_AUDIT_SIGNING_KEY"):
            SignedAuditLogger(db_uri=db_uri, signing_key=None)

    def test_log_decision_creates_signed_entry(self, signed_logger, sample_decision):
        """Test that logging a decision creates a signed audit entry"""
        entry = signed_logger.log_decision(sample_decision)

        assert isinstance(entry, SignedAuditEntry)
        assert entry.request_id == sample_decision["request_id"]
        assert entry.signature is not None
        assert len(entry.signature) == 64  # HMAC-SHA256 produces 64 hex chars
        assert entry.key_version == "v1"

    def test_signature_verification_valid(self, signed_logger, sample_decision):
        """Test that valid signatures are verified correctly"""
        entry = signed_logger.log_decision(sample_decision)

        # Verify signature
        is_valid = signed_logger.verify_signature(entry)

        assert is_valid is True

    def test_signature_verification_tampered_data(self, signed_logger, sample_decision):
        """Test that tampered data is detected"""
        entry = signed_logger.log_decision(sample_decision)

        # Tamper with the decision data
        tampered_data = json.loads(entry.decision_data)
        tampered_data["final_decision"]["overall_verdict"] = "DENY"
        entry.decision_data = json.dumps(tampered_data)

        # Verify signature (should fail)
        is_valid = signed_logger.verify_signature(entry)

        assert is_valid is False

    def test_signature_verification_tampered_signature(self, signed_logger, sample_decision):
        """Test that tampered signatures are detected"""
        entry = signed_logger.log_decision(sample_decision)

        # Tamper with the signature
        entry.signature = "0" * 64  # Invalid signature

        # Verify signature (should fail)
        is_valid = signed_logger.verify_signature(entry)

        assert is_valid is False

    def test_verify_entry_by_id(self, signed_logger, sample_decision):
        """Test verification by entry ID"""
        entry = signed_logger.log_decision(sample_decision)

        # Verify by ID
        is_valid = signed_logger.verify_entry_by_id(entry.id)

        assert is_valid is True

    def test_verify_all_entries(self, signed_logger, sample_decision):
        """Test verification of all entries"""
        # Log multiple decisions
        for i in range(5):
            decision = sample_decision.copy()
            decision["request_id"] = f"test-request-{i}"
            signed_logger.log_decision(decision)

        # Verify all
        results = signed_logger.verify_all_entries()

        assert results["total_entries"] == 5
        assert results["valid_signatures"] == 5
        assert results["tampered_entries"] == 0
        assert results["integrity_status"] == "INTACT"
        assert len(results["tampered_ids"]) == 0

    def test_verify_all_entries_with_tampering(self, signed_logger, sample_decision):
        """Test that verify_all_entries detects tampering"""
        # Log multiple decisions
        entries = []
        for i in range(5):
            decision = sample_decision.copy()
            decision["request_id"] = f"test-request-{i}"
            entry = signed_logger.log_decision(decision)
            entries.append(entry)

        # Tamper with one entry directly in database
        session = signed_logger.Session()
        try:
            tampered_entry = session.query(SignedAuditEntry).filter_by(
                id=entries[2].id
            ).first()
            tampered_data = json.loads(tampered_entry.decision_data)
            tampered_data["final_decision"]["overall_verdict"] = "TAMPERED"
            tampered_entry.decision_data = json.dumps(tampered_data)
            session.commit()
        finally:
            session.close()

        # Verify all
        results = signed_logger.verify_all_entries()

        assert results["total_entries"] == 5
        assert results["valid_signatures"] == 4
        assert results["tampered_entries"] == 1
        assert results["integrity_status"] == "COMPROMISED"
        assert entries[2].id in results["tampered_ids"]

    def test_get_entry_by_request_id(self, signed_logger, sample_decision):
        """Test retrieval by request ID"""
        signed_logger.log_decision(sample_decision)

        # Retrieve by request ID
        entry = signed_logger.get_entry_by_request_id(sample_decision["request_id"])

        assert entry is not None
        assert entry.request_id == sample_decision["request_id"]

    def test_get_statistics(self, signed_logger, sample_decision):
        """Test statistics retrieval"""
        # Log some decisions
        for i in range(3):
            decision = sample_decision.copy()
            decision["request_id"] = f"test-request-{i}"
            signed_logger.log_decision(decision)

        stats = signed_logger.get_statistics()

        assert stats["total_entries"] == 3
        assert stats["current_key_version"] == "v1"
        assert stats["key_versions"]["v1"] == 3
        assert stats["security_status"] == "ENABLED"

    def test_deterministic_signatures(self, signed_logger, sample_decision):
        """Test that identical data produces identical signatures"""
        # Log same decision twice (with same request_id and timestamp)
        signature1 = signed_logger._generate_signature(sample_decision)
        signature2 = signed_logger._generate_signature(sample_decision)

        assert signature1 == signature2

    def test_different_keys_produce_different_signatures(self, tmp_path, sample_decision):
        """Test that different signing keys produce different signatures"""
        db_uri1 = f"sqlite:///{tmp_path}/test_key1.db"
        db_uri2 = f"sqlite:///{tmp_path}/test_key2.db"

        logger1 = SignedAuditLogger(db_uri=db_uri1, signing_key="key1")
        logger2 = SignedAuditLogger(db_uri=db_uri2, signing_key="key2")

        sig1 = logger1._generate_signature(sample_decision)
        sig2 = logger2._generate_signature(sample_decision)

        assert sig1 != sig2

    def test_key_rotation_support(self, tmp_path, test_signing_key, sample_decision):
        """Test that key rotation is supported via key_version"""
        db_uri = f"sqlite:///{tmp_path}/test_rotation.db"

        # Log with v1 key
        logger_v1 = SignedAuditLogger(
            db_uri=db_uri,
            signing_key=test_signing_key,
            key_version="v1"
        )
        decision1 = sample_decision.copy()
        decision1["request_id"] = "req-v1"
        logger_v1.log_decision(decision1)

        # Log with v2 key (simulating rotation)
        logger_v2 = SignedAuditLogger(
            db_uri=db_uri,
            signing_key="new_key_after_rotation",
            key_version="v2"
        )
        decision2 = sample_decision.copy()
        decision2["request_id"] = "req-v2"
        logger_v2.log_decision(decision2)

        # Check statistics show both versions
        stats = logger_v2.get_statistics()

        assert stats["total_entries"] == 2
        assert "v1" in stats["key_versions"]
        assert "v2" in stats["key_versions"]
        assert stats["key_versions"]["v1"] == 1
        assert stats["key_versions"]["v2"] == 1


class TestSecurityProperties:
    """Test security properties of the signed audit log"""

    def test_worm_property_log_once_read_many(self, signed_logger, sample_decision):
        """Test Write-Once-Read-Many property (no updates allowed)"""
        entry = signed_logger.log_decision(sample_decision)

        # Attempt to retrieve and "update" (which should require manual DB manipulation)
        retrieved = signed_logger.get_entry_by_request_id(entry.request_id)

        assert retrieved.id == entry.id
        assert retrieved.signature == entry.signature

        # In a true WORM system, updates would be prevented at DB level
        # Here we demonstrate that verification would catch any tampering

    def test_non_repudiation(self, signed_logger, sample_decision):
        """Test that signed entries cannot be denied (non-repudiation)"""
        entry = signed_logger.log_decision(sample_decision)

        # Entry exists in database
        assert entry.id is not None

        # Signature proves it was created with the signing key
        assert signed_logger.verify_signature(entry) is True

        # Cannot claim entry was not created (signature proves it)

    def test_integrity_verification(self, signed_logger, sample_decision):
        """Test complete integrity verification"""
        # Log multiple entries
        for i in range(10):
            decision = sample_decision.copy()
            decision["request_id"] = f"integrity-test-{i}"
            signed_logger.log_decision(decision)

        # Verify complete integrity
        results = signed_logger.verify_all_entries()

        assert results["integrity_status"] == "INTACT"
        assert results["tampered_entries"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
