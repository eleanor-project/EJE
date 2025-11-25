# Governance Directory

This directory contains governance artifacts for the Ethics Jurisprudence Engine (EJE), implementing the Governance Change Request (GCR) process specified in ELEANOR Specification v2.1.

---

## Directory Structure

```
governance/
├── gcr_ledger.json          # Formal ledger of all governance changes
├── migration_maps/          # Migration scripts for schema/logic changes
│   └── README.md           # Migration map documentation
└── README.md               # This file
```

---

## Governance Change Request (GCR) Process

### What is a GCR?

A **Governance Change Request (GCR)** is a formal proposal to modify:
- Governance logic or algorithms
- Data schemas (precedents, audit logs, configs)
- Constitutional rules or principles
- Critic evaluation thresholds or weights
- Aggregation strategies
- Security or privacy mechanisms

GCRs ensure that all changes to EJE's governance layer are:
- **Transparent**: Publicly documented and reviewable
- **Traceable**: Recorded in the ledger with full history
- **Impact-assessed**: Analyzed for breaking changes and risks
- **Migration-supported**: Provide forward/backward compatibility
- **Constitutionally aligned**: Respect ELEANOR principles

---

## When to Create a GCR

Create a GCR when making changes to:

✅ **Requires GCR**:
- Decision engine logic or flow
- Precedent storage schema or retrieval algorithms
- Critic evaluation contracts or outputs
- Aggregation formulas or weights
- Constitutional rules or principles
- Security/privacy mechanisms
- Audit log schema or immutability guarantees

❌ **Does NOT require GCR**:
- Bug fixes (no behavior change)
- Performance optimizations (no logic change)
- Documentation updates
- Test additions
- Refactoring (preserves behavior)
- Dashboard UI improvements (no governance impact)

**When in doubt**, create a GCR. It's better to be thorough.

---

## How to Create a GCR

### Step 1: Open GitHub Issue
Use the **GCR issue template**:
1. Go to Issues → New Issue
2. Select "Governance Change Request (GCR)"
3. Fill in all required sections

### Step 2: Community Review
- Post in discussions for community feedback
- Minimum 7-day review period for major changes
- Address all comments and concerns

### Step 3: Impact Analysis
- Identify affected components
- Determine if migration is required
- Create migration map if needed
- Write migration tests

### Step 4: Approval
Required approvals:
- [ ] Technical Lead
- [ ] Governance Lead
- [ ] Constitutional Compliance Review
- [ ] Security Review (if security-related)

### Step 5: Implementation
- Implement the change
- Write/update tests
- Update documentation
- Add entry to GCR ledger
- Create migration map if needed

### Step 6: Record in Ledger
Add entry to `gcr_ledger.json`:
```json
{
  "gcr_id": "GCR-YYYY-NNN",
  "title": "Brief description",
  "proposed_by": "username",
  "date_proposed": "YYYY-MM-DD",
  "date_approved": "YYYY-MM-DD",
  "status": "IMPLEMENTED",
  "impact_analysis": {...},
  "migration_map": "governance/migration_maps/name.py",
  "version": "X.X.X"
}
```

---

## GCR Ledger Format

The `gcr_ledger.json` file tracks all governance changes:

```json
{
  "version": "1.0",
  "last_updated": "YYYY-MM-DD",
  "gcr_ledger": [
    {
      "gcr_id": "GCR-YYYY-NNN",
      "title": "Brief description",
      "proposed_by": "username",
      "date_proposed": "YYYY-MM-DD",
      "date_approved": "YYYY-MM-DD",
      "status": "PROPOSED|UNDER_REVIEW|APPROVED|REJECTED|IMPLEMENTED",
      "impact_analysis": {
        "affected_components": ["list"],
        "breaking_changes": true|false,
        "migration_required": true|false
      },
      "description": "Detailed description",
      "migration_map": "path/to/migration.py",
      "test_coverage": "path/to/tests.py",
      "version": "X.X.X"
    }
  ]
}
```

---

## Migration Maps

Migration maps handle version transitions for data and configurations.

### When to Create a Migration Map

Create a migration map when:
- Schema changes (adding/removing/renaming fields)
- Logic changes affecting stored data
- Configuration format changes
- Breaking changes to APIs

### Migration Map Structure

```python
# governance/migration_maps/precedent_v1_to_v2.py

def migrate_forward(old_data: dict) -> dict:
    """
    Migrate from v1.0 to v2.0

    Args:
        old_data: Data in v1.0 format

    Returns:
        Data in v2.0 format
    """
    return {
        "version": "2.0",
        "hash": old_data["hash"],
        "case_input": old_data["case"],  # renamed
        "embedding": None,  # new field
        "migration_status": "MIGRATED"
    }

def migrate_backward(new_data: dict) -> dict:
    """
    Rollback from v2.0 to v1.0

    Args:
        new_data: Data in v2.0 format

    Returns:
        Data in v1.0 format
    """
    return {
        "version": "1.0",
        "hash": new_data["hash"],
        "case": new_data["case_input"],  # renamed back
        # Note: embedding field is lost in rollback
    }
```

### Migration Tests

Every migration map must have tests:

```python
# tests/test_migration_precedent_v2.py

def test_forward_migration():
    old_precedent = {"version": "1.0", "case": {...}}
    new_precedent = migrate_forward(old_precedent)
    assert new_precedent["version"] == "2.0"
    assert "embedding" in new_precedent

def test_backward_migration():
    new_precedent = {"version": "2.0", "case_input": {...}}
    old_precedent = migrate_backward(new_precedent)
    assert old_precedent["version"] == "1.0"
```

---

## CI/CD Integration

### Automated Checks

CI pipeline checks for GCR compliance:

```yaml
# .github/workflows/governance.yml
- name: Check GCR Ledger
  run: |
    # Ensure ledger is valid JSON
    python -m json.tool governance/gcr_ledger.json

    # Check for required migration maps
    python scripts/check_gcr_compliance.py
```

### Migration Tests

Run migration tests in CI:

```bash
pytest tests/test_migration_*.py --cov=governance/migration_maps
```

---

## Version Compatibility Matrix

Track version compatibility in the ledger:

| From Version | To Version | Migration Required | Migration Map |
|--------------|------------|-------------------|---------------|
| 1.0.0        | 1.1.0      | No                | -             |
| 1.1.0        | 1.2.0      | Yes               | precedent_v1_to_v2.py |
| 1.2.0        | 2.0.0      | Yes               | major_v2_migration.py |

---

## References

- **ELEANOR Spec v2.1**: Section on GCR Process
- **Feature Gap Analysis**: FEATURE_GAP_ANALYSIS.md, Gap #4
- **Issue Template**: `.github/ISSUE_TEMPLATE/gcr.md`

---

## Questions?

For questions about the GCR process:
1. Check this README
2. See FEATURE_GAP_ANALYSIS.md, Gap #4
3. Open a discussion on GitHub
4. Contact the governance team

---

**Last Updated**: 2025-11-25
**Maintained By**: Eleanor Project Governance Lab
