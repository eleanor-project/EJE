#!/usr/bin/env python3
"""
Audit Log Verification Tool

Command-line tool for verifying audit log integrity, including:
- Signature verification
- Encryption verification
- WORM storage checks
- Tamper detection
- Bulk verification

Usage:
    python tools/audit_verify.py verify-all
    python tools/audit_verify.py verify-entry <request_id>
    python tools/audit_verify.py check-worm <db_path>
    python tools/audit_verify.py stats
"""

import sys
import os
import click
import stat
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.ejc.core.signed_audit_log import SignedAuditLogger
from src.ejc.core.encrypted_audit_log import EncryptedAuditLogger


@click.group()
def cli():
    """Audit Log Verification Tool for EJE"""
    pass


@cli.command()
@click.option('--db-uri', default=None, help='Database URI (default: from env or SQLite)')
@click.option('--encryption/--no-encryption', default=False, help='Use encrypted audit logger')
def verify_all(db_uri: Optional[str], encryption: bool):
    """Verify all audit entries for tampering."""
    click.echo("🔍 Verifying all audit entries...\n")

    try:
        if encryption:
            logger = EncryptedAuditLogger(db_uri=db_uri)
            click.echo("Using encrypted audit logger")
        else:
            logger = SignedAuditLogger(db_uri=db_uri)
            click.echo("Using signed audit logger")

        results = logger.signed_logger.verify_all_entries() if encryption else logger.verify_all_entries()

        # Display results
        click.echo(f"\n📊 Verification Results:")
        click.echo(f"   Total Entries: {results['total_entries']}")
        click.echo(f"   Valid Signatures: {results['valid_signatures']}")
        click.echo(f"   Tampered Entries: {results['tampered_entries']}")
        click.echo(f"   Integrity Status: {results['integrity_status']}")

        if results['tampered_ids']:
            click.echo(f"\n⚠️  WARNING: Tampered entry IDs: {results['tampered_ids']}")
            sys.exit(1)
        else:
            click.echo("\n✅ All audit entries verified successfully!")
            sys.exit(0)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('request_id')
@click.option('--db-uri', default=None, help='Database URI')
@click.option('--encryption/--no-encryption', default=False, help='Use encrypted audit logger')
def verify_entry(request_id: str, db_uri: Optional[str], encryption: bool):
    """Verify a specific audit entry by request ID."""
    click.echo(f"🔍 Verifying audit entry: {request_id}\n")

    try:
        if encryption:
            logger = EncryptedAuditLogger(db_uri=db_uri)
            result = logger.verify_entry(request_id)
        else:
            logger = SignedAuditLogger(db_uri=db_uri)
            entry = logger.get_entry_by_request_id(request_id)

            if not entry:
                click.echo(f"❌ Entry not found: {request_id}")
                sys.exit(1)

            is_valid = logger.verify_signature(entry)
            result = {
                "found": True,
                "signature_valid": is_valid,
                "status": "VALID" if is_valid else "INVALID"
            }

        # Display results
        click.echo(f"📊 Verification Results:")
        click.echo(f"   Found: {result['found']}")
        click.echo(f"   Signature Valid: {result['signature_valid']}")
        if encryption:
            click.echo(f"   Decryption Successful: {result['decryption_successful']}")
        click.echo(f"   Status: {result['status']}")

        if result['status'] == 'VALID':
            click.echo("\n✅ Entry verified successfully!")
            sys.exit(0)
        else:
            click.echo(f"\n❌ Entry verification failed: {result['status']}")
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('db_path', type=click.Path(exists=True))
def check_worm(db_path: str):
    """Check WORM (Write-Once-Read-Many) storage properties of audit database."""
    click.echo(f"🔍 Checking WORM properties of: {db_path}\n")

    try:
        path = Path(db_path)

        # Check file permissions
        file_stat = path.stat()
        mode = file_stat.st_mode

        # Check if writable by owner
        owner_writable = bool(mode & stat.S_IWUSR)
        group_writable = bool(mode & stat.S_IWGRP)
        other_writable = bool(mode & stat.S_IWOTH)

        # Check if immutable (Linux only - may not work on all systems)
        immutable = False
        if sys.platform.startswith('linux'):
            try:
                import fcntl
                # FS_IOC_GETFLAGS = 0x80086601
                # FS_IMMUTABLE_FL = 0x00000010
                with open(db_path, 'r') as f:
                    flags = fcntl.ioctl(f.fileno(), 0x80086601, 0)
                    immutable = bool(flags & 0x00000010)
            except:
                pass

        click.echo("📊 WORM Property Check:")
        click.echo(f"   Path: {db_path}")
        click.echo(f"   Size: {file_stat.st_size} bytes")
        click.echo(f"   Owner Writable: {owner_writable}")
        click.echo(f"   Group Writable: {group_writable}")
        click.echo(f"   Other Writable: {other_writable}")
        click.echo(f"   Immutable Flag: {immutable}")

        # WORM recommendations
        click.echo("\n💡 WORM Best Practices:")
        if owner_writable:
            click.echo("   ⚠️  Consider removing write permissions: chmod 444")
        if group_writable or other_writable:
            click.echo("   ⚠️  Remove group/other write permissions")
        if not immutable and sys.platform.startswith('linux'):
            click.echo("   ⚠️  Consider setting immutable flag: chattr +i")
        if sys.platform == 'darwin':
            click.echo("   ℹ️  macOS: Use 'chflags uchg' for user immutable flag")

        # Overall assessment
        worm_compliant = not (owner_writable or group_writable or other_writable) or immutable

        if worm_compliant:
            click.echo("\n✅ Database has WORM-like properties")
            sys.exit(0)
        else:
            click.echo("\n⚠️  Database does not fully comply with WORM principles")
            sys.exit(1)

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
@click.option('--db-uri', default=None, help='Database URI')
@click.option('--encryption/--no-encryption', default=False, help='Use encrypted audit logger')
def stats(db_uri: Optional[str], encryption: bool):
    """Display audit log statistics."""
    click.echo("📊 Audit Log Statistics\n")

    try:
        if encryption:
            logger = EncryptedAuditLogger(db_uri=db_uri)
        else:
            logger = SignedAuditLogger(db_uri=db_uri)

        stats = logger.get_statistics()

        click.echo(f"Total Entries: {stats['total_entries']}")
        click.echo(f"Key Versions: {stats['key_versions']}")
        click.echo(f"Current Key Version: {stats['current_key_version']}")
        click.echo(f"Security Status: {stats['security_status']}")

        if encryption:
            click.echo(f"Encryption Enabled: {stats['encryption_enabled']}")
            click.echo(f"Encryption Algorithm: {stats['encryption_algorithm']}")
            click.echo(f"Encryption Key Version: {stats['encryption_key_version']}")

        click.echo("\n✅ Statistics retrieved successfully")

    except Exception as e:
        click.echo(f"\n❌ Error: {str(e)}", err=True)
        sys.exit(1)


@cli.command()
def generate_keys():
    """Generate secure random keys for audit encryption and signing."""
    import secrets

    click.echo("🔐 Generating Secure Audit Keys\n")

    signing_key = secrets.token_hex(32)  # 256 bits
    encryption_key = secrets.token_hex(32)  # 256 bits

    click.echo("Add these to your environment (.env file):\n")
    click.echo(f"EJC_AUDIT_SIGNING_KEY={signing_key}")
    click.echo(f"EJC_AUDIT_ENCRYPTION_KEY={encryption_key}")
    click.echo("\n⚠️  Store these keys securely! Do not commit to version control.")


if __name__ == '__main__':
    cli()
