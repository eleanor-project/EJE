# GitHub Issue Upload Guide

Use `tools/github_issue_uploader.py` to create GitHub issues from the curated CSV that matches the attached list (`tools/data/v7_core_issue_list.csv`).

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
