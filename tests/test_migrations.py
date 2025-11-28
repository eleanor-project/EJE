"""
Tests for GCR migration system.

Tests migration maps and GCR ledger validation.
"""

import json
import os
import pytest
import tempfile
from datetime import datetime

# Import migration map
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'governance', 'migration_maps'))
from precedent_v2_to_v3 import (
    migrate_precedent,
    validate_precedent,
    migrate_all,
    MigrationReport
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_precedent_v2():
    """Sample precedent in v2.0 schema."""
    return {
        "id": "prec_001",
        "hash": "abc123",
        "version": "2.0",
        "input_data": {
            "prompt": "Share user medical records",
            "context": {"privacy_sensitive": True}
        },
        "outcome": {
            "verdict": "blocked",
            "confidence": 0.95,
            "justification": "Privacy violation"
        },
        "timestamp": "2025-01-15T10:00:00Z"
    }


@pytest.fixture
def temp_json_file():
    """Create temporary JSON file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        yield f.name
    # Cleanup
    if os.path.exists(f.name):
        os.unlink(f.name)


# ============================================================================
# Migration Tests
# ============================================================================

class TestPrecedentMigration:
    """Tests for precedent v2 -> v3 migration."""

    def test_migrate_single_precedent(self, sample_precedent_v2):
        """Test migrating single precedent from v2 to v3."""
        prec_v3 = migrate_precedent(sample_precedent_v2)

        # Check v3 fields added
        assert prec_v3["version"] == "3.0"
        assert prec_v3["embedding"] is None
        assert prec_v3["semantic_searchable"] is False
        assert prec_v3["migration_status"] == "MIGRATED"
        assert prec_v3["original_version"] == "2.0"
        assert "migrated_at" in prec_v3

        # Check v2 fields preserved
        assert prec_v3["id"] == sample_precedent_v2["id"]
        assert prec_v3["hash"] == sample_precedent_v2["hash"]
        assert prec_v3["input_data"] == sample_precedent_v2["input_data"]
        assert prec_v3["outcome"] == sample_precedent_v2["outcome"]

    def test_validate_precedent_valid(self, sample_precedent_v2):
        """Test validation of valid precedent."""
        prec_v3 = migrate_precedent(sample_precedent_v2)

        assert validate_precedent(prec_v3) is True

    def test_validate_precedent_missing_id(self):
        """Test validation fails when ID missing."""
        invalid = {
            "hash": "abc123",
            "input_data": {"prompt": "test"},
            "outcome": {"verdict": "allowed"},
            "timestamp": "2025-01-01T00:00:00Z"
        }

        assert validate_precedent(invalid) is False

    def test_validate_precedent_missing_prompt(self):
        """Test validation fails when prompt missing."""
        invalid = {
            "id": "prec_001",
            "hash": "abc123",
            "input_data": {},  # Missing prompt
            "outcome": {"verdict": "allowed"},
            "timestamp": "2025-01-01T00:00:00Z"
        }

        assert validate_precedent(invalid) is False

    def test_validate_precedent_missing_verdict(self):
        """Test validation fails when verdict missing."""
        invalid = {
            "id": "prec_001",
            "hash": "abc123",
            "input_data": {"prompt": "test"},
            "outcome": {},  # Missing verdict
            "timestamp": "2025-01-01T00:00:00Z"
        }

        assert validate_precedent(invalid) is False

    def test_migrate_batch(self, sample_precedent_v2, temp_json_file):
        """Test batch migration of multiple precedents."""
        # Create source file with multiple precedents
        precedents_v2 = [
            sample_precedent_v2,
            {**sample_precedent_v2, "id": "prec_002", "hash": "def456"},
            {**sample_precedent_v2, "id": "prec_003", "hash": "ghi789"}
        ]

        source_file = temp_json_file
        dest_file = temp_json_file + ".out"

        with open(source_file, 'w') as f:
            json.dump(precedents_v2, f)

        # Run migration
        report = migrate_all(source_file, dest_file)

        # Check report
        assert report.total == 3
        assert report.migrated == 3
        assert report.failed == 0
        assert report.skipped == 0

        # Check output file
        assert os.path.exists(dest_file)

        with open(dest_file, 'r') as f:
            precedents_v3 = json.load(f)

        assert len(precedents_v3) == 3
        assert all(p["version"] == "3.0" for p in precedents_v3)

        # Cleanup
        os.unlink(dest_file)

    def test_migrate_skip_existing_v3(self, sample_precedent_v2, temp_json_file):
        """Test migration skips precedents already in v3 format."""
        prec_v3_already = migrate_precedent(sample_precedent_v2)

        precedents = [
            sample_precedent_v2,  # Needs migration
            prec_v3_already       # Already v3
        ]

        source_file = temp_json_file
        dest_file = temp_json_file + ".out"

        with open(source_file, 'w') as f:
            json.dump(precedents, f)

        report = migrate_all(source_file, dest_file)

        assert report.total == 2
        assert report.migrated == 1
        assert report.skipped == 1
        assert report.failed == 0

        # Cleanup
        os.unlink(dest_file)

    def test_migrate_handles_failures(self, temp_json_file):
        """Test migration handles invalid precedents gracefully."""
        precedents = [
            {  # Valid
                "id": "prec_001",
                "hash": "abc123",
                "input_data": {"prompt": "test"},
                "outcome": {"verdict": "allowed"},
                "timestamp": "2025-01-01T00:00:00Z",
                "version": "2.0"
            },
            {  # Invalid - missing prompt
                "id": "prec_002",
                "hash": "def456",
                "input_data": {},
                "outcome": {"verdict": "allowed"},
                "timestamp": "2025-01-01T00:00:00Z",
                "version": "2.0"
            }
        ]

        source_file = temp_json_file
        dest_file = temp_json_file + ".out"

        with open(source_file, 'w') as f:
            json.dump(precedents, f)

        report = migrate_all(source_file, dest_file)

        assert report.total == 2
        assert report.migrated == 1
        assert report.failed == 1
        assert len(report.failures) == 1
        assert "prec_002" in report.failures[0][0]

        # Cleanup
        if os.path.exists(dest_file):
            os.unlink(dest_file)

    def test_migration_preserves_all_fields(self, sample_precedent_v2):
        """Test migration doesn't lose any v2 fields."""
        prec_v3 = migrate_precedent(sample_precedent_v2)

        # All v2 keys should be present in v3
        for key in sample_precedent_v2.keys():
            assert key in prec_v3

        # Plus new v3 keys
        assert "embedding" in prec_v3
        assert "semantic_searchable" in prec_v3
        assert "migration_status" in prec_v3
        assert "migrated_at" in prec_v3


# ============================================================================
# GCR Ledger Tests
# ============================================================================

class TestGCRLedger:
    """Tests for GCR ledger validation."""

    def test_gcr_ledger_exists(self):
        """Test GCR ledger file exists."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        assert os.path.exists(ledger_path), "GCR ledger not found"

    def test_gcr_ledger_valid_json(self):
        """Test GCR ledger is valid JSON."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        with open(ledger_path, 'r') as f:
            ledger = json.load(f)

        assert isinstance(ledger, dict)
        assert "gcr_ledger" in ledger
        assert "metadata" in ledger

    def test_gcr_ledger_schema(self):
        """Test GCR ledger has correct schema."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        with open(ledger_path, 'r') as f:
            ledger = json.load(f)

        # Check top-level fields
        assert "schema_version" in ledger
        assert "gcr_ledger" in ledger
        assert "metadata" in ledger

        # Check metadata fields
        metadata = ledger["metadata"]
        assert "total_gcrs" in metadata
        assert "approved_gcrs" in metadata
        assert "pending_gcrs" in metadata

    def test_gcr_entries_valid(self):
        """Test all GCR entries have required fields."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        with open(ledger_path, 'r') as f:
            ledger = json.load(f)

        required_fields = [
            'gcr_id', 'title', 'proposed_by', 'date_proposed',
            'status', 'priority', 'impact_analysis', 'changes',
            'test_coverage', 'version'
        ]

        for gcr in ledger["gcr_ledger"]:
            for field in required_fields:
                assert field in gcr, f"GCR {gcr.get('gcr_id')} missing field: {field}"

    def test_gcr_ids_unique(self):
        """Test all GCR IDs are unique."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        with open(ledger_path, 'r') as f:
            ledger = json.load(f)

        gcr_ids = [gcr["gcr_id"] for gcr in ledger["gcr_ledger"]]

        assert len(gcr_ids) == len(set(gcr_ids)), "Duplicate GCR IDs found"

    def test_gcr_id_format(self):
        """Test GCR IDs follow correct format (GCR-YYYY-NNN)."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        with open(ledger_path, 'r') as f:
            ledger = json.load(f)

        for gcr in ledger["gcr_ledger"]:
            gcr_id = gcr["gcr_id"]
            assert gcr_id.startswith("GCR-"), f"Invalid GCR ID format: {gcr_id}"

            # Check format GCR-YYYY-NNN
            parts = gcr_id.split("-")
            assert len(parts) == 3, f"Invalid GCR ID format: {gcr_id}"
            assert parts[0] == "GCR"
            assert len(parts[1]) == 4 and parts[1].isdigit(), f"Invalid year: {parts[1]}"
            assert parts[2].isdigit(), f"Invalid number: {parts[2]}"

    def test_gcr_status_valid(self):
        """Test GCR statuses are valid."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        with open(ledger_path, 'r') as f:
            ledger = json.load(f)

        valid_statuses = ['PROPOSED', 'APPROVED', 'REJECTED', 'IMPLEMENTED']

        for gcr in ledger["gcr_ledger"]:
            status = gcr["status"]
            assert status in valid_statuses, f"Invalid status: {status} in {gcr['gcr_id']}"

    def test_gcr_priority_valid(self):
        """Test GCR priorities are valid."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        with open(ledger_path, 'r') as f:
            ledger = json.load(f)

        valid_priorities = ['HIGH', 'MEDIUM', 'LOW']

        for gcr in ledger["gcr_ledger"]:
            priority = gcr["priority"]
            assert priority in valid_priorities, f"Invalid priority: {priority} in {gcr['gcr_id']}"

    def test_metadata_counts_accurate(self):
        """Test metadata counts match actual GCR counts."""
        ledger_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'governance',
            'gcr_ledger.json'
        )

        with open(ledger_path, 'r') as f:
            ledger = json.load(f)

        gcrs = ledger["gcr_ledger"]
        metadata = ledger["metadata"]

        # Check total count
        assert len(gcrs) == metadata["total_gcrs"], "total_gcrs count mismatch"

        # Check approved count
        approved = sum(1 for gcr in gcrs if gcr["status"] == "APPROVED")
        assert approved == metadata["approved_gcrs"], "approved_gcrs count mismatch"

        # Check pending count
        pending = sum(1 for gcr in gcrs if gcr["status"] == "PROPOSED")
        assert pending == metadata["pending_gcrs"], "pending_gcrs count mismatch"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
