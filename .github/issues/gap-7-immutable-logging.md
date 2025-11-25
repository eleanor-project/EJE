---
name: Feature Gap Implementation
about: Track implementation of a feature gap from ELEANOR Spec v2.1
title: '[GAP #7] Immutable Evidence Logging & Cryptographic Security'
labels: ['enhancement', 'spec-alignment', 'eleanor-v2.1', 'high-priority', 'security']
assignees: ''
---

## Feature Gap Reference

**Gap Number**: #7 (from FEATURE_GAP_ANALYSIS.md)
**Gap Title**: Immutable Evidence Logging & Security
**Specification Reference**: ELEANOR Spec v2.1, Security & Audit Requirements

---

## Priority & Effort

**Priority**: **HIGH** 🔴 (Security Critical)
**Estimated Effort**: 8-12 hours
**Target Version**: v1.1.0 (Next 2 months)

---

## Current Implementation Status

- [x] Phase 1 in progress
- [ ] Phase 1 complete
- [ ] Phase 2 in progress
- [ ] Phase 2 complete
- [ ] Phase 3 in progress
- [ ] Phase 3 complete

**What Exists**:
- ✅ SQLAlchemy-based audit logging
- ✅ Append-only pattern (no updates/deletes in code)
- ✅ Comprehensive decision trails

**What's Missing**:
- ❌ Cryptographic signatures on log entries
- ❌ WORM (Write-Once-Read-Many) storage enforcement
- ❌ Encryption at rest (deployment-dependent)
- ❌ Encryption in transit (deployment-dependent)
- ❌ Integrity verification tools
- ❌ Audit log tamper detection

---

## Implementation Phases

### Phase 1: Cryptographic Signatures (4-5 hours)
**Description**: Sign each audit entry with HMAC-SHA256
**Deliverables**:
- [ ] Generate signing key pair (store securely in config)
- [ ] Add `signature` field to audit log schema
- [ ] Implement HMAC-SHA256 signing on all entries
- [ ] Add `verify_entry()` method for tamper detection
- [ ] Create migration script for existing logs
- [ ] Tests written and passing
- [ ] Documentation updated (key management, rotation)

**Code Implementation**:
```python
# src/eje/core/audit_log.py
import hmac
import hashlib
import json
from datetime import datetime

class SignedAuditLog:
    def __init__(self, signing_key: str):
        self.signing_key = signing_key.encode()

    def log_decision(self, decision: Dict) -> Dict:
        """Log decision with cryptographic signature"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "decision": decision,
            "version": "1.0"
        }

        # Sign the entry
        entry_json = json.dumps(entry, sort_keys=True)
        signature = hmac.new(
            self.signing_key,
            entry_json.encode(),
            hashlib.sha256
        ).hexdigest()

        entry["signature"] = signature
        return entry

    def verify_entry(self, entry: Dict) -> bool:
        """Verify entry signature to detect tampering"""
        signature = entry.pop("signature")
        entry_json = json.dumps(entry, sort_keys=True)
        expected_sig = hmac.new(
            self.signing_key,
            entry_json.encode(),
            hashlib.sha256
        ).hexdigest()
        entry["signature"] = signature  # restore
        return hmac.compare_digest(signature, expected_sig)
```

### Phase 2: WORM Enforcement (2-3 hours)
**Description**: Enforce write-once-read-many at database level
**Deliverables**:
- [ ] Add database constraints (prevent UPDATE/DELETE)
- [ ] Document WORM-compliant deployment options
- [ ] Create integrity verification script
- [ ] Add periodic integrity checks
- [ ] Tests for tamper detection
- [ ] Documentation updated

**Database Constraints**:
```sql
-- PostgreSQL example
CREATE OR REPLACE RULE audit_no_update AS
  ON UPDATE TO audit_logs
  DO INSTEAD NOTHING;

CREATE OR REPLACE RULE audit_no_delete AS
  ON DELETE FROM audit_logs
  DO INSTEAD NOTHING;

-- Or use PostgreSQL table partitioning with immutable partitions
```

### Phase 3: Encryption & Key Management (2-4 hours)
**Description**: Document and enable encryption in transit and at rest
**Deliverables**:
- [ ] Add TLS enforcement for API endpoints
- [ ] Document at-rest encryption options (DB encryption, disk encryption)
- [ ] Implement key rotation procedures
- [ ] Add key management documentation
- [ ] Security audit checklist
- [ ] Tests written and passing
- [ ] Documentation updated

**Deployment Configurations**:
```yaml
# config/security.yaml
audit_log:
  signing_key_env: "EJE_AUDIT_SIGNING_KEY"  # Load from environment
  signature_algorithm: "HMAC-SHA256"
  key_rotation_days: 90
  enforce_worm: true

encryption:
  in_transit:
    tls_required: true
    tls_min_version: "1.2"
  at_rest:
    database_encryption: true  # Enable PostgreSQL encryption
    disk_encryption: true      # Enable at OS level
```

---

## Dependencies

**Requires**:
- [ ] Secure key storage solution (environment variables, secrets manager, vault)
- [ ] WORM-capable database or storage (PostgreSQL with constraints, or S3 Object Lock)
- [x] Existing audit log infrastructure

**Blocks**:
- Production deployments (should not deploy without audit security)
- Compliance certifications (SOC2, HIPAA, etc.)
- Gap #8 Governance Tests (needs secure audit for validation)

---

## Acceptance Criteria

- [ ] All audit entries cryptographically signed
- [ ] Tamper detection works (modified entries detected)
- [ ] Database enforces WORM (no UPDATE/DELETE allowed)
- [ ] TLS enforced for all API communication
- [ ] At-rest encryption documented and enabled
- [ ] Key rotation procedures documented
- [ ] Integrity verification script runs successfully
- [ ] Tests cover signature verification, tamper detection
- [ ] Security audit checklist completed
- [ ] Documentation updated (README, docs/security.md)
- [ ] Code review approved
- [ ] CI/CD pipeline passes

---

## Technical Notes

**Security Considerations**:
1. **Key Storage**: Never commit signing keys to git
   - Use environment variables (`EJE_AUDIT_SIGNING_KEY`)
   - Or use secrets manager (AWS Secrets Manager, HashiCorp Vault)

2. **Key Rotation**: Plan for periodic key rotation
   - Store key version with each entry
   - Support multiple active keys for verification
   - Rotate every 90 days

3. **Signature Algorithm**: Use HMAC-SHA256
   - Fast and secure
   - Industry standard
   - Symmetric (same key for sign/verify)

4. **WORM Storage Options**:
   - PostgreSQL: Use triggers or rules to prevent modifications
   - S3: Use Object Lock for compliance
   - Specialized WORM storage (for high-security deployments)

**Performance Impact**:
- Signature overhead: ~0.1ms per entry (negligible)
- Verification overhead: ~0.1ms per entry
- No impact on read performance

**Backwards Compatibility**:
- Existing unsigned entries need migration
- Add signature verification only for new entries initially
- Gradually migrate old entries in background

---

## Migration Strategy

### For Existing Audit Logs

```python
# scripts/migrate_audit_signatures.py
from eje.core.audit_log import SignedAuditLog

def migrate_unsigned_logs():
    """Add signatures to existing audit logs"""
    audit = SignedAuditLog(signing_key=get_signing_key())

    # Find all unsigned entries
    unsigned_entries = db.query(AuditLog).filter(
        AuditLog.signature == None
    ).all()

    for entry in unsigned_entries:
        # Generate signature for existing entry
        signed_entry = audit.log_decision(entry.to_dict())
        entry.signature = signed_entry["signature"]
        db.commit()

    print(f"Migrated {len(unsigned_entries)} entries")
```

---

## References

- **Gap Analysis**: FEATURE_GAP_ANALYSIS.md, Section 7
- **Related Enhancements**: FUTURE_ENHANCEMENTS.md, Item #10 (Plugin Sandboxing)
- **Specification**: ELEANOR Spec v2.1, Security & Immutability Requirements
- **Security Standards**:
  - NIST SP 800-57 (Key Management)
  - NIST FIPS 180-4 (SHA-256)
  - OWASP Top 10

---

## Questions & Discussion

### Q: What happens if the signing key is compromised?
**A**:
1. Rotate to new key immediately
2. Re-sign all entries with new key
3. Keep compromised key for verification of old entries
4. Investigate scope of compromise

### Q: Do we need to encrypt audit log contents?
**A**:
- Signatures ensure **integrity** (tamper detection)
- Encryption ensures **confidentiality** (privacy)
- For most cases, signatures are sufficient
- Add encryption if logs contain PII/sensitive data

### Q: Should we use symmetric (HMAC) or asymmetric (RSA) signatures?
**A**: HMAC-SHA256 (symmetric) is recommended:
- Faster than RSA
- Smaller signatures
- Adequate for internal audit logs
- Use RSA if logs shared externally for verification

---

## Implementation Checklist

**Tonight (Quick Wins)** 🚀:
- [ ] Create `src/eje/core/signed_audit_log.py` with signature implementation
- [ ] Add signing key to `.env.example` with instructions
- [ ] Write test: `test_signature_verification()`
- [ ] Write test: `test_tamper_detection()`
- [ ] Run tests locally

**Week 1**:
- [ ] Complete Phase 1 (signatures)
- [ ] Add `signature` field to database schema
- [ ] Migrate existing logs
- [ ] Document key management

**Week 2**:
- [ ] Complete Phase 2 (WORM enforcement)
- [ ] Add database constraints
- [ ] Create integrity verification script
- [ ] Test tamper detection

**Week 3-4**:
- [ ] Complete Phase 3 (encryption docs)
- [ ] Add TLS enforcement
- [ ] Document deployment security
- [ ] Security audit

---

**CRITICAL**: This is a security-critical feature. Please conduct security review before production deployment!

**Suggested First Task**: Implement `SignedAuditLog` class with HMAC-SHA256 signatures. This is the foundation for all audit security.
