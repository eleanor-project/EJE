# Governance Change Request (GCR) System

This directory contains the complete governance change management system for the EJC project.

## Overview

All changes to governance logic, schemas, thresholds, or critical system components must be tracked through the Governance Change Request (GCR) system.

## GCR Process

### 1. Identify Need for GCR

A GCR is required when making changes to:
- Critic Logic
- Aggregation Rules  
- Schema Definitions
- API Contracts
- Precedent System
- Governance Thresholds

### 2. Create GCR Issue

Use: `.github/ISSUE_TEMPLATE/governance-change-request.md`

### 3. Update GCR Ledger

Add entry to `governance/gcr_ledger.json`

### 4. Create Migration Map (if needed)

Create script in `governance/migration_maps/`

### 5. CI/CD validates automatically

See: `.github/workflows/gcr-validation.yml`

## GCR Statuses

- **PROPOSED**: Pending review
- **APPROVED**: Ready for implementation  
- **REJECTED**: Will not be implemented
- **IMPLEMENTED**: Changes merged

**Maintained By**: Eleanor Project Governance Lab
