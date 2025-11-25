# Migration Maps

This directory contains migration scripts for handling version transitions in EJE.

---

## Purpose

Migration maps ensure **forward and backward compatibility** when schemas, data formats, or governance logic change between versions.

---

## When to Add a Migration Map

Add a migration map when your GCR includes:
- Schema changes (precedents, audit logs, configs)
- Data format changes
- Breaking API changes
- Configuration structure changes

---

## Naming Convention

```
[component]_[from_version]_to_[to_version].py
```

Examples:
- `precedent_v1_to_v2.py`
- `config_v1_3_to_v1_4.py`
- `audit_log_v2_to_v3.py`

---

## Template

```python
"""
Migration: [Component] from vX.X to vY.Y
GCR: GCR-YYYY-NNN
Date: YYYY-MM-DD
Author: @username
"""

def migrate_forward(old_data: dict) -> dict:
    """
    Migrate from version X.X to Y.Y

    Args:
        old_data: Data in vX.X format

    Returns:
        Data in vY.Y format

    Raises:
        ValueError: If old_data is invalid
    """
    # Validate input
    if "version" not in old_data:
        raise ValueError("Missing version field")

    # Transform data
    new_data = {
        "version": "Y.Y",
        # ... migration logic ...
    }

    return new_data


def migrate_backward(new_data: dict) -> dict:
    """
    Rollback from version Y.Y to X.X

    Args:
        new_data: Data in vY.Y format

    Returns:
        Data in vX.X format

    Raises:
        ValueError: If new_data is invalid

    Note:
        Some data loss may occur during rollback if new fields
        have no equivalent in old version.
    """
    # Validate input
    if "version" not in new_data:
        raise ValueError("Missing version field")

    # Transform data (may lose information)
    old_data = {
        "version": "X.X",
        # ... rollback logic ...
    }

    return old_data


def validate_migration(old_data: dict, new_data: dict) -> bool:
    """
    Validate that migration preserved essential data

    Args:
        old_data: Original data
        new_data: Migrated data

    Returns:
        True if migration is valid
    """
    # Check critical fields are preserved
    assert old_data["critical_field"] == new_data["critical_field"]
    return True
```

---

## Testing Requirements

Every migration map must have corresponding tests in `tests/`:

```python
# tests/test_migration_[component]_[version].py

import pytest
from governance.migration_maps.[module] import (
    migrate_forward,
    migrate_backward,
    validate_migration
)

class TestMigration:
    def test_forward_migration(self):
        old = {...}
        new = migrate_forward(old)
        assert new["version"] == "Y.Y"
        assert validate_migration(old, new)

    def test_backward_migration(self):
        new = {...}
        old = migrate_backward(new)
        assert old["version"] == "X.X"

    def test_round_trip(self):
        original = {...}
        migrated = migrate_forward(original)
        rolled_back = migrate_backward(migrated)
        # Check critical fields preserved
        assert original["critical_field"] == rolled_back["critical_field"]

    def test_invalid_input(self):
        with pytest.raises(ValueError):
            migrate_forward({})  # missing required fields
```

---

## CI Integration

Migrations are tested automatically in CI:

```bash
# Run all migration tests
pytest tests/test_migration_*.py

# Check test coverage
pytest tests/test_migration_*.py --cov=governance/migration_maps --cov-report=html
```

---

## Usage in Production

Migration scripts are invoked by deployment tools:

```python
from governance.migration_maps.precedent_v1_to_v2 import migrate_forward

# During upgrade
for precedent in load_all_precedents():
    if precedent["version"] == "1.0":
        upgraded = migrate_forward(precedent)
        save_precedent(upgraded)
```

---

## Best Practices

1. **Always provide rollback**: Implement `migrate_backward` even if it loses data
2. **Validate inputs**: Check for required fields and valid values
3. **Document data loss**: Clearly note if rollback loses information
4. **Test thoroughly**: Include edge cases and invalid inputs
5. **Version everything**: All data should have explicit version field
6. **Keep it simple**: One migration per version transition
7. **Idempotent**: Running migration twice should be safe

---

## Example: Precedent Schema v1 → v2

### Changes in v2
- Renamed `case` → `case_input`
- Renamed `critics` → `critic_verdicts`
- Added `embedding` field (optional)
- Added `migration_status` field

### Migration Implementation

```python
def migrate_forward(old_precedent):
    return {
        "version": "2.0",
        "hash": old_precedent["hash"],
        "case_input": old_precedent["case"],  # renamed
        "critic_verdicts": old_precedent["critics"],  # renamed
        "embedding": None,  # new field, computed lazily
        "migration_status": "MIGRATED",  # track migration
        "original_version": old_precedent["version"]
    }

def migrate_backward(new_precedent):
    return {
        "version": "1.0",
        "hash": new_precedent["hash"],
        "case": new_precedent["case_input"],  # renamed back
        "critics": new_precedent["critic_verdicts"]  # renamed back
        # Note: embedding and migration_status are lost
    }
```

---

## References

- **GCR Process**: governance/README.md
- **Gap Analysis**: FEATURE_GAP_ANALYSIS.md, Gap #4
- **ELEANOR Spec v2.1**: Section on Migration Maps

---

**Last Updated**: 2025-11-25
