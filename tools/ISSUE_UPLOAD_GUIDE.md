# GitHub Issue Upload Guide

Use `tools/github_issue_uploader.py` to create GitHub issues from the curated CSV that matches the attached list (`tools/data/v7_core_issue_list.csv`).

When tasks are finished, close them directly in the GitHub issue tracker using the automation helper described below so the tracker stays in sync with the progress log.

## Prerequisites
- Python 3.9+
- `requests` (installed via `pip install -r requirements.txt`)
- GitHub personal access token in `GITHUB_TOKEN` or `GH_TOKEN` (or provide `--token`)

## Upload steps
1. Choose the target repository in `owner/repo` format.
2. Ensure milestones already exist in the repo (e.g., `V7-Core`, `V7-Docs`, etc.).
3. Run the uploader from the project root:
   ```bash
   python tools/github_issue_uploader.py \
     --repo <owner>/<repo> \
     --csv tools/data/v7_core_issue_list.csv \
     --create-missing-labels
   ```
   - Add `--dry-run` to preview without creating issues.
   - Omit `--create-missing-labels` if labels must already exist.

## Notes
- The CSV contains 115 issues with `title`, `body`, `labels`, and `milestone` fields matching the attached list.
- Milestones are matched by title; missing milestones will raise an error.
- Labels are created with a neutral color when `--create-missing-labels` is supplied.

## Closing completed issues

Run `tools/github_issue_closer.py` to close issues in the tracker once the work is done.

```bash
python tools/github_issue_closer.py \
  --repo <owner>/<repo> \
  --issues 140 150 151 \  # accepts a space- or comma-separated list
  --token $GITHUB_TOKEN
```

Tips:

- Provide `--dry-run` to verify the list before making changes.
- Supply `--state-reason completed` (or `not_planned`) to record why the issue was closed.
- Tokens are resolved from `--token`, `GITHUB_TOKEN`, or `GH_TOKEN`.
- Use this to close the documentation Issue #140 and the Activity 22.x CLI issues once merged.
