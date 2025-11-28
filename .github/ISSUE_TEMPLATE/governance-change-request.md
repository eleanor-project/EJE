---
name: Governance Change Request (GCR)
about: Propose a change to EJC governance logic, schemas, or thresholds
title: 'GCR: [Brief description]'
labels: 'governance, gcr'
assignees: ''
---

## GCR Metadata

**GCR ID**: GCR-YYYY-NNN (assigned by maintainers after approval)
**Proposed By**: @username
**Priority**: HIGH | MEDIUM | LOW
**Target Version**: vX.X.X

---

## Change Description

**Brief Summary**:
(1-2 sentences describing the proposed change)

**Detailed Description**:
(Comprehensive explanation of what is being changed and why)

---

## Rationale

**Problem Statement**:
(What problem does this change solve? What gap does it address?)

**Proposed Solution**:
(How does this change solve the problem?)

**Alternatives Considered**:
(What other approaches were considered and why was this chosen?)

---

## Impact Analysis

### Affected Components
- [ ] Critic logic
- [ ] Aggregation rules
- [ ] Schema definitions (data structures)
- [ ] API contracts
- [ ] Precedent system
- [ ] Database schema
- [ ] Configuration files
- [ ] Other: ___

### Breaking Changes?
- [ ] Yes (requires major version bump and migration)
- [ ] No (backward compatible)

**If YES, describe breaking changes**:

### Migration Required?
- [ ] Yes - data migration needed
- [ ] No - configuration/code only

**If YES, describe migration strategy**:

---

## Implementation Plan

### Steps
1.
2.
3.

### Estimated Effort
- Development: ___ hours
- Testing: ___ hours
- Documentation: ___ hours
- **Total**: ___ hours

### Dependencies
- Depends on: (other GCRs, features, or external factors)
- Blocks: (GCRs or work that depends on this)

---

## Testing Strategy

### Test Coverage
- [ ] Unit tests
- [ ] Integration tests
- [ ] Migration tests
- [ ] Regression tests
- [ ] Manual validation

**Test Plan**:
(Describe how this change will be tested)

### Expected Test Results
(What should the tests verify?)

---

## Rollback Plan

**If this change causes issues, how can it be reverted?**

- [ ] Simple rollback (revert commit)
- [ ] Requires data rollback
- [ ] Cannot be easily rolled back

**Rollback Steps**:
1.
2.

---

## Documentation

### Required Documentation Updates
- [ ] Migration map created: `governance/migration_maps/xxx.py`
- [ ] Tests written: `tests/test_xxx.py`
- [ ] User documentation updated
- [ ] API documentation updated
- [ ] Deployment guide updated
- [ ] GCR ledger updated

### Documentation Plan
(Describe what documentation will be created/updated)

---

## Security & Privacy Considerations

**Does this change affect**:
- [ ] Audit logging
- [ ] Data privacy
- [ ] Authentication/authorization
- [ ] Data retention
- [ ] Cryptographic operations

**If YES, describe considerations**:

---

## Performance Impact

**Expected performance impact**:
- [ ] Positive (faster/more efficient)
- [ ] Neutral (no significant change)
- [ ] Negative (slower/more resources)

**If Negative, describe mitigation**:

---

## Compliance & Governance

**Does this change affect compliance with**:
- [ ] ELEANOR specification v2.1
- [ ] RBJA principles
- [ ] Regulatory requirements (GDPR, CCPA, etc.)
- [ ] Organizational policies

**If YES, describe how compliance is maintained**:

---

## Approval Checklist

### Before Approval
- [ ] Impact analysis complete
- [ ] Implementation plan reviewed
- [ ] Test strategy approved
- [ ] Documentation plan approved
- [ ] Security review (if applicable)
- [ ] Performance impact assessed

### Before Implementation
- [ ] GCR approved by governance team
- [ ] GCR ID assigned
- [ ] GCR ledger updated
- [ ] Migration map implemented (if needed)
- [ ] Tests written

### Before Merge
- [ ] All tests passing
- [ ] Documentation complete
- [ ] Migration tested (if applicable)
- [ ] Code review approved
- [ ] CI/CD checks passed

---

## Additional Notes

(Any other information relevant to this GCR)

---

## References

- Related GCRs:
- Related Issues:
- Specification Sections:
- External Resources:

---

**Submission Date**: YYYY-MM-DD
**Last Updated**: YYYY-MM-DD
