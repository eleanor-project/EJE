# Audit Log Security Guide

Comprehensive guide for securing EJE audit logs with encryption, signatures, and WORM storage.

## Security Architecture

EJE implements **defense-in-depth** for audit log security:

### 1. **Cryptographic Signatures** (Tamper Detection)
- HMAC-SHA256 signatures on all audit entries
- Detects any modification to logged decisions
- Provides non-repudiation
- Supports key rotation with versioning

### 2. **Encryption at Rest** (Confidentiality)
- AES-256-GCM authenticated encryption
- Protects sensitive decision data
- Built-in authentication tag
- Separate encryption and signing keys

### 3. **WORM Storage** (Immutability)
- Write-Once-Read-Many pattern
- Filesystem-level immutability (optional)
- Prevents deletion or modification
- Append-only operations

## Quick Start

### 1. Generate Secure Keys

```bash
# Generate signing and encryption keys
python tools/audit_verify.py generate-keys

# Output (example - use your own generated keys!):
# EJC_AUDIT_SIGNING_KEY=a1b2c3d4e5f6...
# EJC_AUDIT_ENCRYPTION_KEY=f6e5d4c3b2a1...
```

### 2. Configure Environment

Add keys to `.env` file:

```bash
# Required: HMAC signing key for tamper detection
EJC_AUDIT_SIGNING_KEY=your_signing_key_here

# Optional: AES encryption key for confidentiality
EJC_AUDIT_ENCRYPTION_KEY=your_encryption_key_here

# Optional: Custom database URI
EJC_DB_URI=sqlite:///eleanor_data/audit.db
```

**⚠️ IMPORTANT:** Never commit keys to version control! Add `.env` to `.gitignore`.

### 3. Choose Security Level

#### Level 1: Signatures Only (Tamper Detection)
```python
from ejc.core.signed_audit_log import SignedAuditLogger

logger = SignedAuditLogger()
logger.log_decision(decision_bundle)
```

Benefits:
- ✅ Tamper detection
- ✅ Non-repudiation
- ✅ Integrity verification
- ❌ No encryption (data readable)

#### Level 2: Signatures + Encryption (Full Security)
```python
from ejc.core.encrypted_audit_log import EncryptedAuditLogger

logger = EncryptedAuditLogger()
logger.log_decision(decision_bundle)
```

Benefits:
- ✅ Tamper detection
- ✅ Non-repudiation
- ✅ Integrity verification
- ✅ Confidentiality (encrypted at rest)
- ✅ Authenticated encryption (GCM)

## Verification

### Verify All Entries

```bash
# Verify all audit entries for tampering
python tools/audit_verify.py verify-all

# With encryption
python tools/audit_verify.py verify-all --encryption
```

Output:
```
🔍 Verifying all audit entries...

📊 Verification Results:
   Total Entries: 1234
   Valid Signatures: 1234
   Tampered Entries: 0
   Integrity Status: INTACT

✅ All audit entries verified successfully!
```

### Verify Single Entry

```bash
# Verify specific entry by request ID
python tools/audit_verify.py verify-entry <request_id>
```

### Check Statistics

```bash
# View audit log statistics
python tools/audit_verify.py stats --encryption
```

Output:
```
📊 Audit Log Statistics

Total Entries: 1234
Key Versions: {'v1': 1234}
Current Key Version: v1
Security Status: ENABLED
Encryption Enabled: True
Encryption Algorithm: AES-256-GCM
Encryption Key Version: v1
```

## WORM Storage Setup

### Linux Systems

#### 1. Set File Permissions (Read-Only)

```bash
# Make database read-only
chmod 444 eleanor_data/signed_audit_log.db

# Or remove write for owner only
chmod 644 eleanor_data/signed_audit_log.db
```

#### 2. Set Immutable Flag (Recommended)

```bash
# Set immutable flag (requires root)
sudo chattr +i eleanor_data/signed_audit_log.db

# Verify
lsattr eleanor_data/signed_audit_log.db
# Output: ----i----------- eleanor_data/signed_audit_log.db

# Remove immutable flag (when needed)
sudo chattr -i eleanor_data/signed_audit_log.db
```

#### 3. Verify WORM Properties

```bash
python tools/audit_verify.py check-worm eleanor_data/signed_audit_log.db
```

### macOS Systems

```bash
# Set user immutable flag
chflags uchg eleanor_data/signed_audit_log.db

# Verify
ls -lO eleanor_data/signed_audit_log.db
# Shows: uchg flag

# Remove flag (when needed)
chflags nouchg eleanor_data/signed_audit_log.db
```

### Windows Systems

```powershell
# Set read-only attribute
attrib +R eleanor_data\signed_audit_log.db

# Remove attribute (when needed)
attrib -R eleanor_data\signed_audit_log.db
```

## Key Management

### Key Rotation

When rotating keys, use versioned keys to maintain backward compatibility:

```python
# Old entries use v1
old_logger = SignedAuditLogger(key_version="v1")

# New entries use v2
new_logger = SignedAuditLogger(key_version="v2")

# Both versions can be verified independently
```

### Key Storage Best Practices

1. **Environment Variables** (Development)
   - Store in `.env` file
   - Never commit to version control
   - Use in local/dev environments only

2. **Secrets Manager** (Production)
   - AWS Secrets Manager
   - HashiCorp Vault
   - Azure Key Vault
   - Google Secret Manager

3. **Hardware Security Modules** (Enterprise)
   - HSM for key storage
   - FIPS 140-2 compliance
   - Maximum security

### Key Backup

```bash
# Backup keys securely
cp .env .env.backup
chmod 600 .env.backup

# Store backup offline or in secure vault
```

## Security Monitoring

### Automated Verification

Set up automated integrity checks:

```bash
# Add to cron (daily verification)
0 2 * * * cd /path/to/EJE && python tools/audit_verify.py verify-all --encryption
```

### Alert on Tampering

```bash
# Script with alerting
#!/bin/bash
python tools/audit_verify.py verify-all --encryption
if [ $? -ne 0 ]; then
    # Send alert (email, Slack, PagerDuty, etc.)
    echo "SECURITY ALERT: Audit log tampering detected!" | mail -s "EJE Security Alert" admin@example.com
fi
```

## Compliance & Standards

EJE audit security aligns with:

- **NIST SP 800-53**: AU-9 (Protection of Audit Information)
- **PCI DSS**: Requirement 10 (Track and monitor access)
- **HIPAA**: §164.312(b) (Audit controls)
- **SOC 2**: CC6.1 (Logical and physical access controls)
- **GDPR**: Article 32 (Security of processing)

## Troubleshooting

### "EJC_AUDIT_SIGNING_KEY not set"

**Solution:** Generate and set signing key:
```bash
python tools/audit_verify.py generate-keys
# Add output to .env file
```

### "Signature verification failed"

**Possible Causes:**
1. Wrong signing key
2. Data tampered with
3. Key version mismatch

**Solution:** Check key version and verify with correct key.

### "Decryption failed"

**Possible Causes:**
1. Wrong encryption key
2. Ciphertext tampered with
3. Key version mismatch

**Solution:** Verify encryption key and check for tampering.

### "Permission denied" when setting immutable flag

**Solution:** Use sudo:
```bash
sudo chattr +i eleanor_data/signed_audit_log.db
```

## Performance Considerations

### Encryption Overhead

- AES-256-GCM: ~10-20% overhead
- HMAC-SHA256: ~5-10% overhead
- Total: ~15-30% latency increase

For high-throughput systems:
- Consider batch logging
- Use async write operations
- Optimize database configuration

### Storage Requirements

- Encrypted entries: ~20-30% larger
- Signatures: +64 bytes per entry
- Plan storage accordingly

## API Reference

### SignedAuditLogger

```python
from ejc.core.signed_audit_log import SignedAuditLogger

logger = SignedAuditLogger(
    db_uri="sqlite:///audit.db",  # Optional
    signing_key="your_key",        # Optional (from env)
    key_version="v1"               # Optional
)

# Log decision
logger.log_decision(decision_bundle)

# Verify entry
is_valid = logger.verify_entry_by_id(entry_id)

# Verify all
results = logger.verify_all_entries()
```

### EncryptedAuditLogger

```python
from ejc.core.encrypted_audit_log import EncryptedAuditLogger

logger = EncryptedAuditLogger(
    db_uri="sqlite:///audit.db",      # Optional
    signing_key="your_signing_key",    # Optional (from env)
    encryption_key="your_enc_key",     # Optional (from env)
    key_version="v1"                   # Optional
)

# Log encrypted decision
logger.log_decision(decision_bundle)

# Retrieve and decrypt
decrypted = logger.get_decrypted_entry(request_id)

# Verify encryption + signature
result = logger.verify_entry(request_id)
```

## Additional Resources

- [NIST Cryptographic Standards](https://csrc.nist.gov/projects/cryptographic-standards-and-guidelines)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- [EJE Security Architecture](./SECURITY.md)
- [Key Management Best Practices](./KEY_MANAGEMENT.md)

## Support

For security concerns or questions:
- GitHub Issues: [eleanor-project/EJE/issues](https://github.com/eleanor-project/EJE/issues)
- Security Email: security@example.com
- Documentation: [docs.eleanor-project.org](https://docs.eleanor-project.org)
