---
name: Governance Change Request (GCR)
about: Formal request to modify governance logic, schemas, thresholds, or constitutional rules
title: '[GCR] '
labels: ['gcr', 'governance', 'constitutional']
assignees: ''
---

## GCR Metadata

**GCR ID**: GCR-YYYY-NNN (auto-assigned)
**Proposed By**: @[username]
**Date Proposed**: YYYY-MM-DD
**Status**: PROPOSED | UNDER_REVIEW | APPROVED | REJECTED | IMPLEMENTED

---

## Change Description

### What is being changed?
[Describe the governance change: logic, schema, thresholds, CriticMap, constitutional rules, etc.]

### Why is this change needed?
[Justification: bug fix, new requirement, constitutional alignment, performance, etc.]

### What is the expected impact?
[Describe expected effects on decisions, precedents, and system behavior]

---

## Impact Analysis

### Affected Components
- [ ] DecisionEngine
- [ ] PrecedentManager
- [ ] Critics (specify which): _________________
- [ ] Aggregator
- [ ] AuditLog
- [ ] Dashboard
- [ ] CLI
- [ ] Configuration schemas
- [ ] Other: _________________

### Breaking Changes
- [ ] Yes (requires migration)
- [ ] No (backward compatible)

**If yes, describe breaking changes**:
[List what will break and how users are affected]

### Migration Required
- [ ] Yes
- [ ] No

**If yes, provide migration strategy**:
[Describe how existing data/configs will be migrated]

---

## Technical Specification

### Current Behavior
```
[Code or configuration showing current state]
```

### Proposed Behavior
```
[Code or configuration showing proposed state]
```

### Schema Changes (if applicable)
```json
// Before
{
  "field": "old_value"
}

// After
{
  "field": "new_value",
  "new_field": "additional_data"
}
```

---

## Migration Map

**Migration Script Location**: `governance/migration_maps/[name].py`
**Migration Tests Location**: `tests/test_migration_[name].py`

### Migration Pseudocode
```python
def migrate_[name](old_data):
    """Migrate from version X to version Y"""
    # Describe migration logic
    pass
```

---

## Testing Requirements

### Test Coverage
- [ ] Unit tests for new logic
- [ ] Integration tests for affected flows
- [ ] Migration tests (forward and backward)
- [ ] Governance compliance tests
- [ ] Constitutional alignment tests
- [ ] Performance regression tests

### Test Scenarios
1. [Scenario 1: Description]
2. [Scenario 2: Description]
3. [Scenario 3: Description]

---

## Constitutional Alignment

Does this change affect constitutional principles?
- [ ] Yes
- [ ] No

**If yes, explain alignment**:
- [ ] Protection of rights and dignity
- [ ] Transparency
- [ ] Equity & fairness
- [ ] Operational pragmatism
- [ ] Traceability & explainability
- [ ] Respectful coexistence

[Detailed explanation]

---

## Rollout Plan

### Version Target
**Proposed for**: vX.X.X

### Deployment Strategy
- [ ] Feature flag (gradual rollout)
- [ ] All-at-once (requires downtime)
- [ ] Blue-green deployment
- [ ] Canary deployment

### Rollback Plan
[Describe how to rollback if issues arise]

---

## Approvals Required

- [ ] Technical Lead
- [ ] Governance Lead
- [ ] Security Review (if security-related)
- [ ] Community Feedback Period (7 days minimum)
- [ ] Constitutional Compliance Review

---

## GCR Ledger Entry

Once approved, this GCR will be recorded in `governance/gcr_ledger.json`:

```json
{
  "gcr_id": "GCR-YYYY-NNN",
  "title": "[Title]",
  "proposed_by": "@[username]",
  "date_proposed": "YYYY-MM-DD",
  "date_approved": "YYYY-MM-DD",
  "status": "APPROVED",
  "impact_analysis": {
    "affected_components": [],
    "breaking_changes": true|false,
    "migration_required": true|false
  },
  "migration_map": "governance/migration_maps/[name].py",
  "test_coverage": "tests/test_migration_[name].py",
  "version": "X.X.X"
}
```

---

## References

- **ELEANOR Spec v2.1**: [Section reference]
- **Gap Analysis**: FEATURE_GAP_ANALYSIS.md, Gap #4
- **Related Issues**: #[issue numbers]
- **Related GCRs**: GCR-YYYY-NNN

---

## Discussion & Decision Log

[Timeline of reviews, discussions, and decisions]

### [Date] - [Reviewer Name]
**Decision**: APPROVE | REQUEST_CHANGES | REJECT
**Comments**:
[Feedback and comments]

---

## Implementation Checklist

Once approved, track implementation progress:

- [ ] Code changes implemented
- [ ] Migration script written
- [ ] Tests written and passing
- [ ] Documentation updated
- [ ] GCR ledger entry added
- [ ] CHANGELOG.md updated
- [ ] Migration guide in docs/
- [ ] PR submitted and reviewed
- [ ] CI/CD pipeline passes
- [ ] Deployed to production
- [ ] GCR status updated to IMPLEMENTED
