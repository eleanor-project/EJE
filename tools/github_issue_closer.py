"""Utility for closing GitHub issues by number.

Example:
    python tools/github_issue_closer.py \
        --repo owner/repo \
        --issues 140 155 \
        --token $GITHUB_TOKEN

Token resolution order: explicit --token argument, GITHUB_TOKEN env var,
then GH_TOKEN env var.
"""

from __future__ import annotations

import argparse
import os
from typing import Iterable, List, Sequence

import requests


class IssueClosingError(RuntimeError):
    """Raised when an issue cannot be closed."""


class TokenNotProvidedError(SystemExit):
    """Raised when no GitHub token is available."""


def parse_issue_numbers(raw_values: Sequence[str]) -> List[int]:
    numbers: List[int] = []
    for raw in raw_values:
        for chunk in raw.split(","):
            value = chunk.strip()
            if not value:
                continue
            if not value.isdigit():
                raise ValueError(f"Invalid issue number: '{value}'")
            numbers.append(int(value))
    if not numbers:
        raise ValueError("At least one issue number is required")
    return numbers


def resolve_token(explicit: str | None) -> str:
    token = explicit or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        raise TokenNotProvidedError(
            "GitHub token is required (set --token, GITHUB_TOKEN, or GH_TOKEN)"
        )
    return token


def make_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "issue-closer-script",
        }
    )
    return session


def close_issue(
    session: requests.Session,
    repo: str,
    issue_number: int,
    dry_run: bool = False,
) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would close issue #{issue_number} in {repo}")
        return

    response = session.patch(
        f"https://api.github.com/repos/{repo}/issues/{issue_number}",
        json={"state": "closed"},
        timeout=30,
    )
    if response.status_code == 404:
        raise IssueClosingError(f"Issue #{issue_number} not found in {repo}")
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:  # pragma: no cover - thin guard
        raise IssueClosingError(
            f"Failed to close issue #{issue_number}: {response.text}"
        ) from exc
    print(f"Closed issue #{issue_number} in {repo}")


def close_issues(
    repo: str, issue_numbers: Iterable[int], token: str, dry_run: bool
) -> None:
    session = make_session(token)
    for number in issue_numbers:
        close_issue(session, repo, number, dry_run=dry_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Close GitHub issues by number.")
    parser.add_argument("--repo", required=True, help="Target repository in owner/name format")
    parser.add_argument(
        "--issues",
        nargs="+",
        required=True,
        help="Issue numbers to close (separate with spaces or commas)",
    )
    parser.add_argument("--token", help="GitHub token (falls back to env vars)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended actions without calling the GitHub API",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    numbers = parse_issue_numbers(args.issues)
    token = resolve_token(args.token)
    close_issues(args.repo, numbers, token=token, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
