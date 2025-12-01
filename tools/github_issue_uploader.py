"""Upload issues to GitHub from a CSV file.

The CSV must contain the columns: title, body, labels, milestone.
Labels should be comma-separated. Milestone values are matched by title.

Usage example:
    python tools/github_issue_uploader.py \
        --repo owner/repo \
        --csv tools/data/v7_core_issue_list.csv \
        --token $GITHUB_TOKEN \
        --create-missing-labels

Set GITHUB_TOKEN or GH_TOKEN to avoid passing --token explicitly.
"""

import argparse
import csv
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence

import requests


@dataclass
class IssueRow:
    title: str
    body: str
    labels: List[str]
    milestone: Optional[str]


def parse_rows(csv_path: str) -> List[IssueRow]:
    rows: List[IssueRow] = []
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for line_number, raw in enumerate(reader, start=2):
            label_string = raw.get("labels", "") or ""
            labels = [label.strip() for label in label_string.split(",") if label.strip()]
            milestone = (raw.get("milestone") or "").strip() or None
            title = (raw.get("title") or "").strip()
            body = (raw.get("body") or "").strip()
            if not title:
                raise ValueError(f"Row {line_number}: 'title' is required")
            if not body:
                raise ValueError(f"Row {line_number}: 'body' is required")

            rows.append(
                IssueRow(
                    title=title,
                    body=body,
                    labels=labels,
                    milestone=milestone,
                )
            )
    return rows


def make_session(token: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "issue-uploader-script",
        }
    )
    return session


def fetch_all_milestones(session: requests.Session, repo: str) -> Dict[str, int]:
    milestones: Dict[str, int] = {}
    page = 1
    while True:
        response = session.get(
            f"https://api.github.com/repos/{repo}/milestones",
            params={"state": "all", "per_page": 100, "page": page},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        for milestone in payload:
            milestones[milestone["title"].strip().lower()] = milestone["number"]
        if len(payload) < 100:
            break
        page += 1
    return milestones


def ensure_label(
    session: requests.Session,
    repo: str,
    label: str,
    allow_create: bool,
    label_cache: Dict[str, bool],
) -> None:
    normalized = label.lower()
    if normalized in label_cache:
        return
    response = session.get(
        f"https://api.github.com/repos/{repo}/labels/{label}",
        timeout=30,
    )
    if response.status_code == 404:
        if not allow_create:
            raise ValueError(f"Label '{label}' does not exist and auto-create is disabled")
        creation = session.post(
            f"https://api.github.com/repos/{repo}/labels",
            json={"name": label, "color": "ededed"},
            timeout=30,
        )
        creation.raise_for_status()
        label_cache[normalized] = True
        return
    response.raise_for_status()
    label_cache[normalized] = True


def create_issue(
    session: requests.Session,
    repo: str,
    issue: IssueRow,
    milestone_number: Optional[int],
    dry_run: bool,
) -> None:
    payload: Dict[str, object] = {
        "title": issue.title,
        "body": issue.body,
        "labels": issue.labels,
    }
    if milestone_number is not None:
        payload["milestone"] = milestone_number

    if dry_run:
        print(
            f"[DRY-RUN] Would create issue: {issue.title} → milestone {milestone_number} "
            f"with labels {issue.labels}"
        )
        return

    response = session.post(
        f"https://api.github.com/repos/{repo}/issues",
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    issue_url = response.json().get("html_url", "<unknown>")
    print(f"Created issue: {issue_url}")


def process_issues(
    repo: str,
    issues: Sequence[IssueRow],
    token: str,
    dry_run: bool,
    create_missing_labels: bool,
) -> None:
    session = make_session(token)
    milestone_map = fetch_all_milestones(session, repo)
    label_cache: Dict[str, bool] = {}

    for issue in issues:
        milestone_number = None
        if issue.milestone:
            key = issue.milestone.strip().lower()
            if key not in milestone_map:
                raise ValueError(f"Milestone '{issue.milestone}' not found in repository {repo}")
            milestone_number = milestone_map[key]

        for label in issue.labels:
            ensure_label(session, repo, label, create_missing_labels, label_cache)

        create_issue(session, repo, issue, milestone_number, dry_run)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload GitHub issues from a CSV file.")
    parser.add_argument("--repo", required=True, help="Target repository in the form owner/name")
    parser.add_argument("--csv", default="tools/data/v7_core_issue_list.csv", help="Path to CSV file")
    parser.add_argument("--token", help="GitHub token (falls back to GITHUB_TOKEN or GH_TOKEN env vars)")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without creating issues")
    parser.add_argument(
        "--create-missing-labels",
        action="store_true",
        help="Create labels that do not already exist",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = args.token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("A GitHub token is required via --token, GITHUB_TOKEN, or GH_TOKEN")

    issues = parse_rows(args.csv)
    if not issues:
        raise SystemExit(f"No issues found in {args.csv}")

    process_issues(
        repo=args.repo,
        issues=issues,
        token=token,
        dry_run=args.dry_run,
        create_missing_labels=args.create_missing_labels,
    )


if __name__ == "__main__":
    main()
