#!/bin/bash
# Script to create GitHub issues for feature gaps
# Since gh CLI is not available, this provides instructions and alternatives

set -e

echo "================================================"
echo "Creating GitHub Issues for ELEANOR Gap Analysis"
echo "================================================"
echo ""

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

echo "📋 High Priority Gap Issues to Create:"
echo ""
echo "  1. [GAP #8] Governance & Constitutional Test Suites (HIGH)"
echo "  2. [GAP #7] Immutable Evidence Logging & Security (HIGH)"
echo "  3. [GAP #1] Precedent Vector Embeddings & Semantic Retrieval (HIGH)"
echo "  4. [GAP #4] Complete GCR Process & Migration Maps (HIGH)"
echo ""

# Check if gh CLI is available
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI (gh) is available!"
    echo ""
    read -p "Create issues using gh CLI? (y/n) " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo "Creating issues..."
        echo ""

        # Create Gap #8
        gh issue create \
            --title "[GAP #8] Governance & Constitutional Test Suites in CI/CD" \
            --label "enhancement,spec-alignment,eleanor-v2.1,high-priority,testing" \
            --body-file .github/issues/gap-8-governance-tests.md

        # Create Gap #7
        gh issue create \
            --title "[GAP #7] Immutable Evidence Logging & Cryptographic Security" \
            --label "enhancement,spec-alignment,eleanor-v2.1,high-priority,security" \
            --body-file .github/issues/gap-7-immutable-logging.md

        # Create Gap #1
        gh issue create \
            --title "[GAP #1] Precedent Vector Embeddings & Semantic Retrieval" \
            --label "enhancement,spec-alignment,eleanor-v2.1,high-priority,ml" \
            --body-file .github/issues/gap-1-precedent-embeddings.md

        # Create Gap #4
        gh issue create \
            --title "[GAP #4] Complete GCR Process, Migration Maps & Versioning" \
            --label "enhancement,spec-alignment,eleanor-v2.1,high-priority,governance" \
            --body-file .github/issues/gap-4-gcr-completion.md

        echo ""
        echo "✅ All issues created!"
        echo ""
        echo "View your issues: gh issue list"
        exit 0
    fi
fi

echo "⚠️  GitHub CLI not available or user declined."
echo ""
echo "📝 Manual Creation Options:"
echo ""
echo "Option 1: Install GitHub CLI"
echo "  brew install gh        # macOS"
echo "  sudo apt install gh    # Ubuntu/Debian"
echo "  Then run: ./scripts/create_gap_issues.sh"
echo ""
echo "Option 2: Create via GitHub Web UI"
echo "  1. Go to: https://github.com/eleanor-project/EJE/issues/new"
echo "  2. Use the issue content from:"
echo "     - .github/issues/gap-8-governance-tests.md"
echo "     - .github/issues/gap-7-immutable-logging.md"
echo "     - .github/issues/gap-1-precedent-embeddings.md"
echo "     - .github/issues/gap-4-gcr-completion.md"
echo ""
echo "Option 3: Use GitHub API"
echo "  See: scripts/create_issues_via_api.py"
echo ""

exit 0
