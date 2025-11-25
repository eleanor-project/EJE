---
name: Feature Gap Implementation
about: Track implementation of a feature gap from ELEANOR Spec v2.1
title: '[GAP #4] Complete GCR Process, Migration Maps & Versioning'
labels: ['enhancement', 'spec-alignment', 'eleanor-v2.1', 'high-priority', 'governance']
assignees: ''
---

## Feature Gap Reference

**Gap Number**: #4 (from FEATURE_GAP_ANALYSIS.md)
**Gap Title**: Governance Change Requests (GCR), Migration Maps, & Versioning
**Specification Reference**: ELEANOR Spec v2.1, GCR Process & Migration

---

## Priority & Effort

**Priority**: **HIGH** 🔴
**Estimated Effort**: 12-16 hours (remaining work after initial setup)
**Target Version**: v1.1.0 - v1.3.0

---

## Current Implementation Status

- [x] Phase 1 in progress (PARTIALLY COMPLETE)
- [ ] Phase 1 complete
- [ ] Phase 2 in progress
- [ ] Phase 2 complete
- [ ] Phase 3 in progress
- [ ] Phase 3 complete

**What Exists** ✅:
- ✅ Git-based version control
- ✅ Conventional commit messages
- ✅ PR review process
- ✅ CHANGELOG.md for tracking changes
- ✅ GCR ledger initialized (`governance/gcr_ledger.json`)
- ✅ GCR process documentation (`governance/README.md`)
- ✅ GCR issue template (`.github/ISSUE_TEMPLATE/gcr.md`)
- ✅ Migration maps directory structure (`governance/migration_maps/`)

**What's Missing** ❌:
- ❌ Impact analysis automation
- ❌ Version parsing in core objects
- ❌ CI checks for migration map updates
- ❌ Backward compatibility tests
- ❌ Actual migration map implementations
- ❌ Automated GCR ledger validation

---

## Implementation Phases

### Phase 1: GCR Ledger & Templates ✅ COMPLETE
**Description**: Establish formal GCR process structure
**Status**: ✅ DONE (completed in previous commit)

**Completed**:
- [x] Created `governance/gcr_ledger.json`
- [x] Added GCR template in `.github/ISSUE_TEMPLATE/gcr.md`
- [x] Documented GCR approval process in `governance/README.md`
- [x] Created migration maps directory

### Phase 2: Migration Maps & Version Parsing (8-10 hours)
**Description**: Implement version parsing and migration infrastructure
**Deliverables**:
- [ ] Add `version` field to all core data classes
  - [ ] PrecedentRecord (currently missing)
  - [ ] AuditLogEntry (currently missing)
  - [ ] ConfigSchema (currently missing)
  - [ ] CriticOutput (currently missing)
- [ ] Implement version parsing utilities
- [ ] Create example migration map (`precedent_v1_to_v2.py`)
- [ ] Create migration runner script
- [ ] Add migration tests
- [ ] Tests written and passing
- [ ] Documentation updated

**Code Implementation**:

```python
# src/eje/core/schemas.py
from dataclasses import dataclass
from typing import Optional
from packaging import version as pkg_version

@dataclass
class Versioned:
    """Base class for versioned data"""
    version: str = "1.0"

    def get_version(self) -> pkg_version.Version:
        """Parse version as packaging.version.Version"""
        return pkg_version.parse(self.version)

    def needs_migration(self, target_version: str) -> bool:
        """Check if migration is needed to target version"""
        return self.get_version() < pkg_version.parse(target_version)

@dataclass
class PrecedentRecord(Versioned):
    """Versioned precedent record"""
    hash: str
    case: dict
    verdict: str
    critics: dict
    embedding: Optional[list] = None  # Added in v2.0
    migration_status: str = "NATIVE"  # NATIVE, MIGRATED, PARTIAL
    version: str = "2.0"

# src/eje/core/migration_runner.py
class MigrationRunner:
    """Runs migration maps for data version upgrades"""

    def __init__(self):
        self.migrations = self._discover_migrations()

    def _discover_migrations(self):
        """Auto-discover migration scripts in governance/migration_maps/"""
        import importlib
        import os
        from pathlib import Path

        migrations = {}
        maps_dir = Path("governance/migration_maps")

        for file in maps_dir.glob("*.py"):
            if file.stem == "README":
                continue

            # Parse filename: component_v1_to_v2.py
            parts = file.stem.split("_")
            if "to" in parts:
                component = parts[0]
                from_version = parts[parts.index("v") + 1]
                to_version = parts[parts.index("to") + 1].replace("v", "")

                # Import module
                module = importlib.import_module(
                    f"governance.migration_maps.{file.stem}"
                )

                migrations[(component, from_version, to_version)] = {
                    "forward": module.migrate_forward,
                    "backward": module.migrate_backward
                }

        return migrations

    def migrate(self, data: dict, component: str, target_version: str):
        """Migrate data to target version"""
        current_version = data.get("version", "1.0")

        # Find migration path
        migration_key = (component, current_version, target_version)
        if migration_key not in self.migrations:
            raise ValueError(
                f"No migration found: {component} v{current_version} -> v{target_version}"
            )

        # Run migration
        migrate_fn = self.migrations[migration_key]["forward"]
        migrated_data = migrate_fn(data)

        # Validate
        if migrated_data["version"] != target_version:
            raise ValueError(
                f"Migration failed: expected v{target_version}, "
                f"got v{migrated_data['version']}"
            )

        return migrated_data
```

**Example Migration Map**:

```python
# governance/migration_maps/precedent_v1_to_v2.py
"""
Migration: Precedent from v1.0 to v2.0
GCR: GCR-2025-002
Date: 2025-11-26
Author: william.parris

Changes in v2.0:
- Renamed 'case' → 'case_input'
- Renamed 'critics' → 'critic_verdicts'
- Added 'embedding' field (optional, computed lazily)
- Added 'migration_status' field
"""

def migrate_forward(old_precedent: dict) -> dict:
    """
    Migrate precedent from v1.0 to v2.0

    Args:
        old_precedent: Precedent in v1.0 format

    Returns:
        Precedent in v2.0 format
    """
    if old_precedent.get("version") != "1.0":
        raise ValueError(f"Expected v1.0, got {old_precedent.get('version')}")

    return {
        "version": "2.0",
        "hash": old_precedent["hash"],
        "case_input": old_precedent["case"],  # renamed
        "critic_verdicts": old_precedent["critics"],  # renamed
        "embedding": None,  # new field, computed on-demand
        "migration_status": "MIGRATED",
        "original_version": "1.0",
        "timestamp": old_precedent.get("timestamp"),
        "references": old_precedent.get("references", [])
    }

def migrate_backward(new_precedent: dict) -> dict:
    """
    Rollback precedent from v2.0 to v1.0

    Args:
        new_precedent: Precedent in v2.0 format

    Returns:
        Precedent in v1.0 format

    Note:
        Data loss: 'embedding' and 'migration_status' fields are dropped
    """
    if new_precedent.get("version") != "2.0":
        raise ValueError(f"Expected v2.0, got {new_precedent.get('version')}")

    return {
        "version": "1.0",
        "hash": new_precedent["hash"],
        "case": new_precedent["case_input"],  # renamed back
        "critics": new_precedent["critic_verdicts"],  # renamed back
        "timestamp": new_precedent.get("timestamp"),
        "references": new_precedent.get("references", [])
        # NOTE: 'embedding' and 'migration_status' are lost
    }

def validate_migration(old_data: dict, new_data: dict) -> bool:
    """Validate migration preserved critical fields"""
    assert old_data["hash"] == new_data["hash"], "Hash mismatch"
    assert old_data["case"] == new_data["case_input"], "Case mismatch"
    return True
```

### Phase 3: CI Automation (4-6 hours)
**Description**: Add CI checks for GCR compliance and migration validation
**Deliverables**:
- [ ] Add pytest migration tests to CI
- [ ] Add GCR ledger validation script
- [ ] CI check: Block PRs that change schemas without GCR entry
- [ ] CI check: Ensure migration maps exist for breaking changes
- [ ] Automated compatibility matrix generation
- [ ] Add GitHub Actions workflow for governance checks
- [ ] Tests written and passing
- [ ] Documentation updated

**CI Workflow**:

```yaml
# .github/workflows/gcr_compliance.yml
name: GCR Compliance

on:
  pull_request:
    paths:
      - 'src/eje/core/**/*.py'
      - 'governance/**'

jobs:
  check_gcr_compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Validate GCR Ledger
        run: |
          python -m json.tool governance/gcr_ledger.json > /dev/null
          echo "✅ GCR ledger is valid JSON"

      - name: Check for Breaking Changes
        run: |
          python scripts/check_breaking_changes.py
          # Fails if schema changes detected without GCR entry

      - name: Run Migration Tests
        run: |
          pytest tests/test_migration_*.py -v --cov=governance/migration_maps

      - name: Generate Compatibility Matrix
        run: |
          python scripts/generate_compatibility_matrix.py
          cat docs/compatibility_matrix.md
```

**Breaking Change Detection Script**:

```python
# scripts/check_breaking_changes.py
"""Detect schema changes that require GCR"""

import ast
import json
from pathlib import Path
from datetime import datetime, timedelta

def detect_schema_changes():
    """Check if schemas changed in recent commits"""
    # Run git diff to find schema changes
    import subprocess

    result = subprocess.run(
        ["git", "diff", "main", "--", "src/eje/core/schemas.py"],
        capture_output=True,
        text=True
    )

    if not result.stdout:
        print("✅ No schema changes detected")
        return

    # Schema changed - check for GCR entry
    with open("governance/gcr_ledger.json") as f:
        ledger = json.load(f)

    # Check if GCR added in last 7 days
    recent_gcrs = [
        gcr for gcr in ledger["gcr_ledger"]
        if (datetime.utcnow() - datetime.fromisoformat(gcr["date_proposed"])).days <= 7
    ]

    if not recent_gcrs:
        print("❌ Schema changed but no recent GCR found!")
        print("   Please create a GCR for this schema change.")
        exit(1)

    print(f"✅ Found recent GCR: {recent_gcrs[0]['gcr_id']}")

if __name__ == "__main__":
    detect_schema_changes()
```

---

## Dependencies

**Requires**:
- [x] Git and GitHub infrastructure
- [ ] `packaging` library for version parsing
- [ ] pytest for migration tests
- [ ] GitHub Actions for CI

**Blocks**:
- Gap #1: Precedent Embeddings (needs migration for schema change)
- Gap #7: Immutable Logging (schema changes need GCR)
- All future schema/governance changes

---

## Acceptance Criteria

### Phase 2 (v1.2.0)
- [ ] All core data classes have `version` field
- [ ] Version parsing utilities implemented and tested
- [ ] At least one example migration map (precedent v1→v2)
- [ ] Migration runner can auto-discover and run migrations
- [ ] Round-trip migration tests pass (v1→v2→v1)
- [ ] Documentation explains how to create migration maps
- [ ] Example GCR created for precedent schema change

### Phase 3 (v1.3.0)
- [ ] CI validates GCR ledger JSON format
- [ ] CI detects schema changes and requires GCR
- [ ] CI runs all migration tests automatically
- [ ] Compatibility matrix auto-generated
- [ ] GitHub Actions workflow passing
- [ ] Documentation updated with CI requirements

---

## Technical Notes

**Version Format**:
- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Breaking changes → bump MAJOR
- New features (backward-compatible) → bump MINOR
- Bug fixes → bump PATCH

**Migration Strategy**:
- **Forward migrations**: Always required for upgrades
- **Backward migrations**: Best effort (some data loss acceptable)
- **Idempotent**: Running migration twice should be safe

**When to Create a GCR**:
- Schema changes (adding/removing/renaming fields)
- Governance logic changes (aggregation, thresholds)
- Constitutional rule changes
- Breaking API changes

---

## References

- **Gap Analysis**: FEATURE_GAP_ANALYSIS.md, Section 4
- **GCR Process**: governance/README.md
- **Migration Maps**: governance/migration_maps/README.md
- **Related Enhancements**: FUTURE_ENHANCEMENTS.md, Item #11 (Type Hints)

---

## Questions & Discussion

### Q: What if we need to support multiple version transitions?
**A**: Migration runner should chain migrations: v1.0 → v1.1 → v2.0

### Q: Should we auto-migrate on startup?
**A**: No. Provide explicit migration command: `eje migrate --target-version 2.0`
Prevent accidental data modifications.

### Q: How do we handle partial migrations?
**A**: Track `migration_status`: `NATIVE`, `MIGRATED`, `PARTIAL`, `FAILED`

---

## Implementation Checklist

**TONIGHT (Phase 2 Start)** 🚀:
- [ ] Add `packaging` to requirements.txt
- [ ] Create `src/eje/core/schemas.py` with Versioned base class
- [ ] Add `version` field to PrecedentRecord
- [ ] Write first migration map: `governance/migration_maps/precedent_v1_to_v2.py`
- [ ] Create `tests/test_migration_precedent_v2.py`
- [ ] Test migration locally:
  ```bash
  pytest tests/test_migration_precedent_v2.py -v
  ```

**Week 1** (Phase 2):
- [ ] Add version fields to all core classes
- [ ] Implement MigrationRunner
- [ ] Create 2-3 example migration maps
- [ ] Write comprehensive migration tests
- [ ] Document migration creation process

**Week 2-3** (Phase 3):
- [ ] Create `scripts/check_breaking_changes.py`
- [ ] Create `scripts/validate_gcr_ledger.py`
- [ ] Add GitHub Actions workflow
- [ ] Test CI with sample PR
- [ ] Generate compatibility matrix

**Week 4**:
- [ ] Complete documentation
- [ ] Create GCR for any schema changes made during implementation
- [ ] Update all related docs
- [ ] Deploy to production

---

## Example: Creating a GCR for Schema Change

When you make a schema change, follow this process:

### 1. Create GitHub Issue with GCR Template
```markdown
Title: [GCR] Add embedding field to PrecedentRecord

## Change Description
Adding `embedding` field to support semantic precedent retrieval (Gap #1).

## Impact Analysis
- Affected: PrecedentManager, precedent storage
- Breaking: No (field is optional)
- Migration: Optional (embeddings computed lazily)

## Schema Changes
```python
# Before (v1.0)
{
  "hash": "...",
  "case": {...},
  "critics": {...}
}

# After (v2.0)
{
  "hash": "...",
  "case_input": {...},  # renamed
  "critic_verdicts": {...},  # renamed
  "embedding": [...],  # new
  "migration_status": "NATIVE"  # new
}
```

### 2. Create Migration Map
File: `governance/migration_maps/precedent_v1_to_v2.py`
(See example above)

### 3. Write Tests
File: `tests/test_migration_precedent_v2.py`

### 4. Update GCR Ledger
Add entry to `governance/gcr_ledger.json`

### 5. Submit PR
- Include GCR issue number in PR title
- Link migration map and tests
- CI will validate GCR compliance

---

## Success Metrics

- [ ] 100% of schema changes have corresponding GCR entries
- [ ] All migrations have tests with >90% coverage
- [ ] CI blocks PRs with breaking changes lacking GCR
- [ ] Migration success rate: 100% (no data corruption)
- [ ] GCR review time: <7 days average
- [ ] Documentation completeness: All GCR fields filled

---

## Related Issues

- Gap #1: Precedent Embeddings (needs precedent schema migration)
- Gap #7: Immutable Logging (needs audit log schema migration)
- Gap #8: Governance Tests (validates GCR compliance)

---

This is **foundational infrastructure** for all future EJE evolution. Get this right and all other gaps become easier! 🎯
