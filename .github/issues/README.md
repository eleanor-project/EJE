# Gap Analysis GitHub Issues

This directory contains detailed issue descriptions for implementing feature gaps from FEATURE_GAP_ANALYSIS.md.

## High Priority Issues (v1.1.0)

### 🔴 Gap #8: Governance & Constitutional Test Suites
**File**: `gap-8-governance-tests.md`
**Priority**: HIGH
**Effort**: 16-24 hours
**Quick Start Tonight**: Create test data corpus and implement privacy/transparency tests

### 🔴 Gap #7: Immutable Evidence Logging & Security
**File**: `gap-7-immutable-logging.md`
**Priority**: HIGH (Security Critical)
**Effort**: 8-12 hours
**Quick Start Tonight**: Implement SignedAuditLog with HMAC-SHA256 signatures

### 🔴 Gap #1: Precedent Vector Embeddings & Semantic Retrieval
**File**: `gap-1-precedent-embeddings.md`
**Priority**: HIGH (Highest Value)
**Effort**: 16-24 hours across 3 phases
**Quick Start Tonight**: Install sentence-transformers and test embedding generation

### 🔴 Gap #4: Complete GCR Process & Migration Maps
**File**: `gap-4-gcr-completion.md`
**Priority**: HIGH
**Effort**: 12-16 hours (Phase 1 done, Phase 2-3 remaining)
**Quick Start Tonight**: Add version fields to core classes and create first migration map

---

## Creating GitHub Issues

### Option 1: Using GitHub CLI (gh)
```bash
# If gh is installed
./scripts/create_gap_issues.sh
```

### Option 2: Using GitHub API
```bash
# Set your GitHub token
export GITHUB_TOKEN='your_token_here'

# Run script
python scripts/create_issues_via_api.py
```

### Option 3: Manual Creation via Web UI
1. Go to https://github.com/eleanor-project/EJE/issues/new
2. Copy content from the markdown files in this directory
3. Remove YAML frontmatter (lines between `---`)
4. Add labels manually:
   - `enhancement`
   - `spec-alignment`
   - `eleanor-v2.1`
   - `high-priority`
   - (Plus specific label: `testing`, `security`, `ml`, or `governance`)

---

## Issue Structure

Each issue contains:

- **Gap Reference**: Links to FEATURE_GAP_ANALYSIS.md
- **Priority & Effort**: Estimated complexity
- **Implementation Status**: Phase tracking
- **What Exists / What's Missing**: Current state
- **Implementation Phases**: Detailed breakdown with deliverables
- **Code Examples**: Actual implementation stubs
- **Dependencies**: What's needed and what's blocked
- **Acceptance Criteria**: Definition of done
- **Technical Notes**: Architecture considerations
- **Quick Start Checklist**: What to do tonight!

---

## Recommended Order

**Tonight** (2-4 hours):
1. **Gap #8** - Create test corpus and basic governance tests
2. **Gap #7** - Implement SignedAuditLog class

**Week 1** (Focus on foundations):
1. **Gap #7** - Complete audit security (8-12h)
2. **Gap #4** - Add version fields and first migration map (8-10h)

**Week 2-3** (Build intelligence):
1. **Gap #8** - Complete governance test suite (16-24h)
2. **Gap #1 Phase 1** - Basic embeddings with sentence-transformers (8-10h)

**Month 2** (Production-grade):
1. **Gap #1 Phase 2** - FAISS integration (6-8h)
2. **Gap #4 Phase 3** - CI automation (4-6h)

---

## Success Metrics

Track progress with these metrics:

- [ ] All 4 HIGH priority issues created in GitHub
- [ ] At least 1 issue started within 24 hours
- [ ] 2-3 issues in progress within 1 week
- [ ] All Phase 1 work complete within 1 month
- [ ] v1.1.0 released within 2 months

---

## Questions?

- See FEATURE_GAP_ANALYSIS.md for strategic overview
- See governance/README.md for GCR process
- Open a discussion on GitHub for clarification

---

**Let's build the future of ethical AI governance! 🚀**
