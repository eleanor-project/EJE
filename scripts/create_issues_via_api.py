#!/usr/bin/env python3
"""
Create GitHub issues for gap analysis via GitHub REST API
Alternative to gh CLI when not available
"""

import json
import requests
from pathlib import Path
import os
import sys

# Configuration
REPO_OWNER = "eleanor-project"
REPO_NAME = "EJE"
GITHUB_API = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/issues"

# Issue files to create
ISSUE_FILES = [
    {
        "file": ".github/issues/gap-8-governance-tests.md",
        "title": "[GAP #8] Governance & Constitutional Test Suites in CI/CD",
        "labels": ["enhancement", "spec-alignment", "eleanor-v2.1", "high-priority", "testing"]
    },
    {
        "file": ".github/issues/gap-7-immutable-logging.md",
        "title": "[GAP #7] Immutable Evidence Logging & Cryptographic Security",
        "labels": ["enhancement", "spec-alignment", "eleanor-v2.1", "high-priority", "security"]
    },
    {
        "file": ".github/issues/gap-1-precedent-embeddings.md",
        "title": "[GAP #1] Precedent Vector Embeddings & Semantic Retrieval",
        "labels": ["enhancement", "spec-alignment", "eleanor-v2.1", "high-priority", "ml"]
    },
    {
        "file": ".github/issues/gap-4-gcr-completion.md",
        "title": "[GAP #4] Complete GCR Process, Migration Maps & Versioning",
        "labels": ["enhancement", "spec-alignment", "eleanor-v2.1", "high-priority", "governance"]
    }
]

def create_issue(title, body, labels, token):
    """Create a GitHub issue via REST API"""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    payload = {
        "title": title,
        "body": body,
        "labels": labels
    }

    response = requests.post(GITHUB_API, json=payload, headers=headers)

    if response.status_code == 201:
        issue = response.json()
        return issue
    else:
        print(f"❌ Failed to create issue: {response.status_code}")
        print(f"   Response: {response.text}")
        return None

def main():
    # Check for GitHub token
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        print("")
        print("To use this script:")
        print("  1. Create a GitHub Personal Access Token:")
        print("     https://github.com/settings/tokens")
        print("     (Needs 'repo' scope)")
        print("")
        print("  2. Set environment variable:")
        print("     export GITHUB_TOKEN='your_token_here'")
        print("")
        print("  3. Run this script:")
        print("     python scripts/create_issues_via_api.py")
        print("")
        sys.exit(1)

    print(f"🚀 Creating {len(ISSUE_FILES)} issues in {REPO_OWNER}/{REPO_NAME}...")
    print("")

    created_issues = []

    for issue_config in ISSUE_FILES:
        # Read issue body from file
        file_path = Path(issue_config["file"])
        if not file_path.exists():
            print(f"⚠️  Skipping {issue_config['title']} - file not found: {file_path}")
            continue

        # Read file content (skip YAML frontmatter)
        with open(file_path, 'r') as f:
            lines = f.readlines()

        # Skip YAML frontmatter (between --- markers)
        body_lines = []
        in_frontmatter = False
        frontmatter_count = 0

        for line in lines:
            if line.strip() == "---":
                frontmatter_count += 1
                if frontmatter_count == 2:
                    in_frontmatter = False
                    continue
                else:
                    in_frontmatter = True
                    continue

            if not in_frontmatter and frontmatter_count >= 2:
                body_lines.append(line)

        body = ''.join(body_lines).strip()

        # Create issue
        print(f"Creating: {issue_config['title']}...")
        issue = create_issue(
            title=issue_config['title'],
            body=body,
            labels=issue_config['labels'],
            token=token
        )

        if issue:
            created_issues.append(issue)
            print(f"  ✅ Created: #{issue['number']} - {issue['html_url']}")
        else:
            print(f"  ❌ Failed to create issue")

        print("")

    print("")
    print(f"✅ Created {len(created_issues)} issues successfully!")
    print("")
    print("View all issues:")
    for issue in created_issues:
        print(f"  - #{issue['number']}: {issue['html_url']}")

if __name__ == "__main__":
    main()
