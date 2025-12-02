# Audit Log Security & Encryption

**Gap #7 Phase 3: Encryption, Key Management & Security Best Practices**

This document describes encryption, key management, and security best practices for the EJE audit log system.

## Overview

Building on Phase 1 (cryptographic signatures) and Phase 2 (WORM enforcement), Phase 3 adds:
- Encryption in transit (TLS)
- Encryption at rest (database-level)
- Key management and rotation
- Security best practices
- Compliance guidance

## Implementation Status

✅ **Phase 1**: Cryptographic signatures (`src/ejc/core/signed_audit_log.py`)
✅ **Phase 2**: WORM enforcement (`docs/AUDIT_LOG_WORM_ENFORCEMENT.md`)
✅ **Phase 3**: Security documentation (this document)

## Encryption Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Audit Log System                    │
├─────────────────────────────────────────────────────┤
│  Application Layer (Python)                          │
│  ┌──────────────────────────────────────────┐       │
│  │ SignedAuditLogger                        │       │
│  │ - HMAC-SHA256 Signatures ✓               │       │
│  │ - Tamper Detection ✓                     │       │
│  └──────────────────────────────────────────┘       │
│          ↓ TLS 1.2/1.3 (In Transit) ✓               │
├─────────────────────────────────────────────────────┤
│  Database Layer (PostgreSQL/SQLite)                  │
│  ┌──────────────────────────────────────────┐       │
│  │ signed_audit_log table                   │       │
│  │ - Database encryption at rest ✓          │       │
│  │ - WORM enforcement ✓                     │       │
│  └──────────────────────────────────────────┘       │
│          ↓ Disk encryption (optional)                │
├─────────────────────────────────────────────────────┤
│  Storage Layer (Disk)                                │
│  - LUKS/dm-crypt (Linux) ✓                          │
│  - FileVault (macOS) ✓                              │
│  - BitLocker (Windows) ✓                            │
└─────────────────────────────────────────────────────┘
```

## 1. Encryption In Transit (TLS)

### PostgreSQL TLS Configuration

**Server Configuration (`postgresql.conf`)**:

```conf
# Enable SSL/TLS
ssl = on
ssl_cert_file = '/path/to/server.crt'
ssl_key_file = '/path/to/server.key'
ssl_ca_file = '/path/to/ca.crt'

# Require TLS for all connections
ssl_min_protocol_version = 'TLSv1.2'
ssl_prefer_server_ciphers = on

# Strong cipher suites only
ssl_ciphers = 'HIGH:MEDIUM:+3DES:!aNULL:!eNULL'
```

**Client Configuration (Python connection string)**:

```python
# config/security.yaml
database:
  postgresql:
    host: "db.example.com"
    port: 5432
    database: "eje_production"
    user: "eje_user"
    sslmode: "require"  # Options: disable, allow, prefer, require, verify-ca, verify-full
    sslcert: "/path/to/client.crt"
    sslkey: "/path/to/client.key"
    sslrootcert: "/path/to/ca.crt"

# Application code
from sqlalchemy import create_engine

db_config = load_config()["database"]["postgresql"]
db_uri = (
    f"postgresql://{db_config['user']}@{db_config['host']}:{db_config['port']}"
    f"/{db_config['database']}"
    f"?sslmode={db_config['sslmode']}"
    f"&sslcert={db_config['sslcert']}"
    f"&sslkey={db_config['sslkey']}"
    f"&sslrootcert={db_config['sslrootcert']}"
)

engine = create_engine(db_uri)
logger = SignedAuditLogger(db_uri=db_uri)
```

### API TLS Configuration (FastAPI/Uvicorn)

```python
# src/eje/api/app.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "eje.api.app:app",
        host="0.0.0.0",
        port=8443,
        ssl_keyfile="/path/to/server.key",
        ssl_certfile="/path/to/server.crt",
        ssl_ca_certs="/path/to/ca.crt",
        ssl_version=3,  # TLS 1.2+
    )
```

### Verification

```python
# Test TLS connection
import psycopg2

try:
    conn = psycopg2.connect(
        host="db.example.com",
        database="eje_production",
        user="eje_user",
        sslmode="verify-full",
        sslcert="/path/to/client.crt",
        sslkey="/path/to/client.key",
        sslrootcert="/path/to/ca.crt"
    )
    print("✅ TLS connection successful")
    print(f"SSL version: {conn.info.ssl_in_use}")
except Exception as e:
    print(f"❌ TLS connection failed: {e}")
```

## 2. Encryption At Rest

### PostgreSQL pgcrypto (Column-Level Encryption)

For sensitive audit data that needs additional encryption:

```sql
-- Enable pgcrypto extension
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Encrypt sensitive fields
ALTER TABLE signed_audit_log
ADD COLUMN encrypted_decision_data BYTEA;

-- Encrypt data on insert
INSERT INTO signed_audit_log (encrypted_decision_data, ...)
VALUES (
    pgp_sym_encrypt(
        'sensitive decision data',
        current_setting('app.encryption_key')
    ),
    ...
);

-- Decrypt on read
SELECT
    pgp_sym_decrypt(encrypted_decision_data, current_setting('app.encryption_key')) AS decision_data
FROM signed_audit_log;
```

**Note**: This adds complexity. Only use if database-level encryption is insufficient.

### PostgreSQL Transparent Data Encryption (TDE)

**PostgreSQL 15+ with pgcrypto or pg_tde**:

```bash
# Initialize encrypted cluster
initdb -D /var/lib/postgresql/data --data-checksums --encryption-method=aes256

# Or use pg_tde extension
CREATE EXTENSION pg_tde;
SELECT pg_tde_set_master_key('your-master-key');
```

**Enterprise PostgreSQL** (EDB, Percona):
- Full TDE support built-in
- Transparent to application
- No performance penalty

### SQLite Encryption

**Option 1: SQLCipher (Recommended)**:

```python
# Install: pip install sqlcipher3

from sqlcipher3 import dbapi2 as sqlite

# Create encrypted database
conn = sqlite.connect("encrypted_audit_log.db")
conn.execute("PRAGMA key = 'your-encryption-key'")
conn.execute("PRAGMA cipher = 'aes-256-cbc'")

# Use with SQLAlchemy
from sqlalchemy import create_engine, event

engine = create_engine("sqlite:///encrypted_audit_log.db")

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA key = 'your-encryption-key'")
    cursor.execute("PRAGMA cipher = 'aes-256-cbc'")
    cursor.close()
```

**Option 2: File System Encryption** (Simpler):

- Linux: LUKS / dm-crypt
- macOS: FileVault
- Windows: BitLocker

### Cloud Database Encryption

**AWS RDS PostgreSQL**:
- Enable encryption at rest in RDS console
- Uses AWS KMS for key management
- Automatic, transparent to application

**Google Cloud SQL**:
- Encryption at rest enabled by default
- Uses Google-managed encryption keys
- Optional: Customer-managed encryption keys (CMEK)

**Azure Database for PostgreSQL**:
- Transparent data encryption (TDE) enabled by default
- Azure Key Vault integration

## 3. Key Management

### Signing Key Management

**Current Implementation**:

```python
# Load from environment variable
signing_key = os.getenv("EJC_AUDIT_SIGNING_KEY")

if not signing_key:
    raise ValueError("EJC_AUDIT_SIGNING_KEY not set")
```

### Best Practices

**1. Store Keys Securely**:

```bash
# DON'T: Store in code or config files
signing_key = "hardcoded-secret-123"  # ❌ NEVER DO THIS

# DO: Use environment variables
export EJC_AUDIT_SIGNING_KEY="$(openssl rand -hex 32)"

# BETTER: Use secrets manager
export EJC_AUDIT_SIGNING_KEY="$(aws secretsmanager get-secret-value --secret-id eje/audit/signing-key --query SecretString --output text)"
```

**2. Use Secrets Managers**:

```python
# AWS Secrets Manager
import boto3

def get_signing_key():
    """Retrieve signing key from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='eje/audit/signing-key')
    return response['SecretString']

logger = SignedAuditLogger(signing_key=get_signing_key())
```

```python
# HashiCorp Vault
import hvac

def get_signing_key():
    """Retrieve signing key from HashiCorp Vault"""
    client = hvac.Client(url='https://vault.example.com:8200')
    client.token = os.getenv('VAULT_TOKEN')
    secret = client.secrets.kv.v2.read_secret_version(path='eje/audit')
    return secret['data']['data']['signing_key']
```

```python
# Google Secret Manager
from google.cloud import secretmanager

def get_signing_key():
    """Retrieve signing key from Google Secret Manager"""
    client = secretmanager.SecretManagerServiceClient()
    name = "projects/YOUR_PROJECT/secrets/eje-audit-signing-key/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode('UTF-8')
```

**3. Key Rotation**:

```python
# src/ejc/core/signed_audit_log.py
class SignedAuditLogger:
    def __init__(self, signing_key=None, key_version="v1"):
        # Support multiple key versions
        self.key_versions = {
            "v1": os.getenv("EJC_AUDIT_SIGNING_KEY_V1"),
            "v2": os.getenv("EJC_AUDIT_SIGNING_KEY_V2"),  # New key
        }
        self.current_key_version = key_version
        self.signing_key = self.key_versions[key_version].encode('utf-8')

    def verify_signature(self, entry):
        """Verify signature with correct key version"""
        key_version = entry.key_version
        signing_key = self.key_versions[key_version].encode('utf-8')

        # Recompute signature with versioned key
        data = json.loads(entry.decision_data)
        expected_sig = hmac.new(
            signing_key,
            json.dumps(data, sort_keys=True).encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(entry.signature, expected_sig)
```

**Key Rotation Process**:

```bash
# 1. Generate new key
export EJC_AUDIT_SIGNING_KEY_V2="$(openssl rand -hex 32)"

# 2. Deploy updated config (both keys available)
# Old entries use v1, new entries use v2

# 3. Update application to use v2 for new entries
logger = SignedAuditLogger(key_version="v2")

# 4. After rotation period (e.g., 90 days), remove v1
# Keep v1 read-only for historical verification
```

### Encryption Key Management

**Database Encryption Keys**:
- Use cloud provider KMS (AWS KMS, Google Cloud KMS, Azure Key Vault)
- Rotate automatically (managed service)
- Separate from application keys

**SQLCipher Keys**:
- Store in secrets manager
- Rotate by re-encrypting database with new key
- Keep old keys for historical backups

## 4. Security Best Practices

### 1. Principle of Least Privilege

```sql
-- Create read-only audit user
CREATE USER audit_reader WITH PASSWORD 'secure_password';
GRANT SELECT ON signed_audit_log TO audit_reader;
REVOKE INSERT, UPDATE, DELETE ON signed_audit_log FROM audit_reader;

-- Create write-only audit user (for application)
CREATE USER audit_writer WITH PASSWORD 'secure_password';
GRANT INSERT ON signed_audit_log TO audit_writer;
REVOKE SELECT, UPDATE, DELETE ON signed_audit_log FROM audit_writer;
```

### 2. Network Security

```yaml
# config/security.yaml
network:
  # Restrict database access
  allowed_ips:
    - "10.0.1.0/24"  # Application servers
    - "10.0.2.0/24"  # Admin network

  # Firewall rules (PostgreSQL)
  pg_hba.conf: |
    # TYPE  DATABASE        USER            ADDRESS                 METHOD
    hostssl all             all             10.0.1.0/24             cert
    hostssl all             all             10.0.2.0/24             cert
    host    all             all             0.0.0.0/0               reject
```

### 3. Audit Access Logs

```python
# Log all access to audit logs
import logging

audit_access_logger = logging.getLogger("eje.audit_access")

def log_audit_access(user, action, entry_id=None):
    """Log access to audit logs"""
    audit_access_logger.info(
        f"user={user} action={action} entry_id={entry_id} "
        f"timestamp={datetime.utcnow().isoformat()}"
    )

# Example usage
def get_entry_by_id(entry_id, user):
    log_audit_access(user, "READ", entry_id)
    return logger.get_entry_by_request_id(entry_id)
```

### 4. Regular Integrity Checks

```python
# scripts/verify_audit_integrity.py
from ejc.core.signed_audit_log import SignedAuditLogger

def daily_integrity_check():
    """Run daily integrity verification"""
    logger = SignedAuditLogger()
    results = logger.verify_all_entries()

    if results["integrity_status"] != "INTACT":
        send_alert(
            severity="CRITICAL",
            message=f"Audit tampering detected: {results['tampered_ids']}"
        )
        return False

    print(f"✅ Audit integrity verified: {results['total_entries']} entries")
    return True

if __name__ == "__main__":
    import sys
    sys.exit(0 if daily_integrity_check() else 1)
```

**Cron Job**:

```cron
# Run integrity check daily at 3 AM
0 3 * * * /usr/bin/python3 /app/scripts/verify_audit_integrity.py
```

### 5. Backup Security

```bash
# Encrypted backups
pg_dump -U postgres eje_production -t signed_audit_log | \
    gpg --encrypt --recipient backup@example.com > \
    audit_backup_$(date +%Y%m%d).sql.gpg

# Store in secure location
aws s3 cp audit_backup_*.sql.gpg s3://eje-secure-backups/ \
    --server-side-encryption AES256 \
    --storage-class GLACIER
```

## 5. Compliance Matrix

| Requirement | Implementation | Verification |
|-------------|---------------|--------------|
| **SOC 2** |
| CC6.1: Logical access | TLS + auth | Penetration test |
| CC7.2: System monitoring | Integrity checks | Daily verification |
| A1.2: Audit integrity | HMAC + WORM | Signature verification |
| **HIPAA** |
| §164.312(a)(1): Access control | Database roles | Access logs |
| §164.312(b): Audit controls | Signed logs | Integrity checks |
| §164.312(c)(1): Integrity | WORM + signatures | Tamper detection |
| §164.312(e)(1): Transmission security | TLS 1.2+ | SSL verification |
| **GDPR** |
| Art. 32: Security | Encryption + WORM | Security audit |
| Art. 5(1)(f): Integrity | Signatures + WORM | Daily verification |

## 6. Security Audit Checklist

```markdown
## Pre-Production Security Audit

### Encryption
- [ ] TLS 1.2+ enabled for database connections
- [ ] TLS certificates valid and not expired
- [ ] Database encryption at rest enabled
- [ ] Disk encryption enabled (LUKS/FileVault/BitLocker)

### Key Management
- [ ] Signing keys stored in secrets manager (not code/config)
- [ ] Encryption keys rotated within policy (90 days)
- [ ] Key access logged and monitored
- [ ] Backup keys stored securely

### Access Control
- [ ] Database users follow least privilege principle
- [ ] Network access restricted (firewall rules)
- [ ] Authentication required for all access
- [ ] Access logs enabled and monitored

### Integrity
- [ ] WORM enforcement active (PostgreSQL rules/SQLite immutable)
- [ ] Daily integrity verification running
- [ ] Alerts configured for tamper detection
- [ ] Backup integrity verified

### Monitoring
- [ ] Audit access logs enabled
- [ ] Security alerts configured
- [ ] Integrity check alerts working
- [ ] Backup monitoring active

### Compliance
- [ ] SOC 2 controls documented
- [ ] HIPAA safeguards implemented
- [ ] GDPR requirements met
- [ ] Audit trail complete

### Documentation
- [ ] Security policies documented
- [ ] Incident response plan defined
- [ ] Key rotation procedures documented
- [ ] Disaster recovery plan tested
```

## 7. Incident Response

### Suspected Tampering

```python
# 1. Immediate verification
results = logger.verify_all_entries()

# 2. Isolate compromised entries
if results["tampered_entries"] > 0:
    # Lock down system
    disable_audit_writes()

    # Investigate
    for entry_id in results["tampered_ids"]:
        entry = get_entry(entry_id)
        print(f"Tampered: {entry.request_id} at {entry.timestamp}")

    # Restore from backup
    restore_from_last_known_good_backup()

# 3. Notify security team
send_security_alert(severity="CRITICAL", results=results)
```

### Key Compromise

```bash
# 1. Generate new key immediately
export EJC_AUDIT_SIGNING_KEY_V3="$(openssl rand -hex 32)"

# 2. Deploy new key
kubectl set env deployment/eje EJC_AUDIT_SIGNING_KEY=$EJC_AUDIT_SIGNING_KEY_V3

# 3. Investigate scope
# - Review access logs
# - Check for unauthorized entries
# - Verify historical signatures with old key

# 4. Re-sign existing entries with new key (optional)
python scripts/resign_audit_entries.py --old-key v2 --new-key v3
```

## Summary

✅ **Encryption in Transit**: TLS 1.2+ for all database/API connections
✅ **Encryption at Rest**: Database-level or disk-level encryption
✅ **Key Management**: Secrets manager integration with rotation support
✅ **Access Control**: Least privilege, network restrictions, audit logging
✅ **Monitoring**: Daily integrity checks, security alerts
✅ **Compliance**: SOC 2, HIPAA, GDPR requirements met

## References

- [NIST SP 800-57: Key Management](https://csrc.nist.gov/publications/detail/sp/800-57-part-1/rev-5/final)
- [PostgreSQL SSL/TLS](https://www.postgresql.org/docs/current/ssl-tcp.html)
- [SQLCipher Documentation](https://www.zetetic.net/sqlcipher/)
- [OWASP Cryptographic Storage Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cryptographic_Storage_Cheat_Sheet.html)
- Gap #7 Issue: `.github/issues/gap-7-immutable-logging.md`
- Phase 1 Implementation: `src/ejc/core/signed_audit_log.py`
- Phase 2 Documentation: `docs/AUDIT_LOG_WORM_ENFORCEMENT.md`

---

**Status**: ✅ Phase 3 Documented
**Last Updated**: 2025-12-02
**Author**: EJE Development Team
