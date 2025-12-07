"""Command line interface for the Eleanor Judicial Engine (EJE) API.

This CLI is built on top of the official Python SDK and provides quick
access to common API operations:

- Evaluate a case
- Search precedents
- Check service health

Environment variables:
- ``EJE_BASE_URL``: Default API base URL if ``--base-url`` is not set
- ``EJE_API_KEY``: Default API key if ``--api-key`` is not set
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urlparse

from .client import EJEAPIError, EJEClient


def _parse_headers(header_items: Optional[Iterable[str]]) -> Dict[str, str]:
    """Parse custom header values from ``KEY:VALUE`` strings."""

    headers: Dict[str, str] = {}
    if not header_items:
        return headers

    for item in header_items:
        if ":" not in item:
            raise ValueError(f"Invalid header format '{item}'. Expected KEY:VALUE")
        key, value = item.split(":", 1)
        headers[key.strip()] = value.strip()
    return headers


def _parse_json(label: str, value: Optional[str]) -> Dict[str, Any]:
    """Safely parse a JSON string into a dictionary."""

    if not value:
        return {}

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid JSON for {label}: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")

    return parsed


def _load_json_file(label: str, path: str) -> Dict[str, Any]:
    """Load a JSON object from disk."""

    file_path = Path(path)
    if not file_path.exists():
        raise ValueError(f"{label} file not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValueError(f"Unable to read {label} file: {exc}") from exc

    parsed = _parse_json(label, content)
    return parsed


def _validate_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return None

    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("base URL must include scheme and host, e.g. https://api.example.com")

    return base_url


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="EJE command line client")
    parser.add_argument("--base-url", dest="base_url", help="EJE API base URL")
    parser.add_argument("--api-key", dest="api_key", help="API key for authentication")
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=int,
        default=30,
        help="Request timeout in seconds (default: 30)",
    )
    parser.add_argument(
        "-H",
        "--header",
        dest="headers",
        action="append",
        help="Custom header in KEY:VALUE format. Repeatable.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    eval_parser = subparsers.add_parser("evaluate", help="Evaluate a case")
    eval_parser.add_argument("prompt", help="Case prompt or question")
    eval_parser.add_argument(
        "--context",
        help="JSON object with contextual data",
    )
    eval_parser.add_argument(
        "--context-file",
        dest="context_file",
        help="Path to JSON file containing contextual data",
    )
    eval_parser.add_argument("--case-id", dest="case_id", help="Optional case identifier")
    eval_parser.add_argument(
        "--require-human-review",
        dest="require_human_review",
        action="store_true",
        help="Force escalation to human review",
    )

    search_parser = subparsers.add_parser("search", help="Search precedents")
    search_parser.add_argument("prompt", help="Search prompt")
    search_parser.add_argument("--context", help="JSON object with contextual data")
    search_parser.add_argument(
        "--context-file",
        dest="context_file",
        help="Path to JSON file containing contextual data",
    )
    search_parser.add_argument(
        "--top-k",
        dest="top_k",
        type=int,
        default=10,
        help="Number of results to return (default: 10)",
    )
    search_parser.add_argument(
        "--min-similarity",
        dest="min_similarity",
        type=float,
        default=0.70,
        help="Minimum similarity threshold (default: 0.70)",
    )
    search_parser.add_argument(
        "--search-mode",
        dest="search_mode",
        choices=["exact", "semantic", "hybrid"],
        default="hybrid",
        help="Search mode: exact, semantic, or hybrid (default: hybrid)",
    )

    parser.add_argument(
        "-o",
        "--output",
        dest="output",
        help="Write command result to the given file (pretty-printed JSON)",
    )

    subparsers.add_parser("health", help="Check API health")

    return parser


def run(argv: Optional[Iterable[str]] = None, client_factory=None, out=sys.stdout, err=sys.stderr) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        base_url = _validate_base_url(args.base_url or os.getenv("EJE_BASE_URL"))
        if not base_url:
            err.write("Error: --base-url or EJE_BASE_URL is required\n")
            return 2

        api_key = args.api_key or os.getenv("EJE_API_KEY")
        headers = _parse_headers(args.headers)

        inline_context = getattr(args, "context", None)
        context_file = getattr(args, "context_file", None)
        if inline_context and context_file:
            raise ValueError("Use either --context or --context-file, not both")

        if context_file:
            context = _load_json_file("context", context_file)
        else:
            context = _parse_json("context", inline_context)
    except ValueError as exc:
        err.write(f"Error: {exc}\n")
        return 2

    client_factory = client_factory or (
        lambda: EJEClient(
            base_url=base_url,
            api_key=api_key,
            timeout=args.timeout,
            headers=headers,
        )
    )

    client = client_factory()

    try:
        if args.command == "evaluate":
            result = client.evaluate_case(
                prompt=args.prompt,
                context=context,
                case_id=args.case_id,
                require_human_review=args.require_human_review,
            )
        elif args.command == "search":
            result = client.search_precedents(
                prompt=args.prompt,
                context=context,
                top_k=args.top_k,
                min_similarity=args.min_similarity,
                search_mode=args.search_mode,
            )
        elif args.command == "health":
            result = client.health()
        else:  # pragma: no cover - argparse guards this
            parser.print_help()
            return 2

        rendered = json.dumps(result, indent=2)
        out.write(rendered + "\n")

        if args.output:
            output_path = Path(args.output)
            try:
                output_path.write_text(rendered + "\n", encoding="utf-8")
            except OSError as exc:  # pragma: no cover - filesystem dependent
                err.write(f"Error writing output file: {exc}\n")
                return 2
        return 0
    except EJEAPIError as exc:
        err.write(f"API error: {exc}\n")
        return 1
    finally:
        if hasattr(client, "close"):
            client.close()


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":  # pragma: no cover
    main()
