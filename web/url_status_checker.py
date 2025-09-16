"""Concurrent HTTP status checker for URLs.

Usage examples:
  python -m web.url_status_checker https://example.com https://httpbin.org/status/404
  echo "https://example.com" | python -m web.url_status_checker --stdin --json
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {"User-Agent": "pyutils-url-status/1.0"}


@dataclass
class UrlStatusResult:
    """Container for the outcome of a single URL check."""

    url: str
    status: Optional[int]
    ok: bool
    method: str
    final_url: Optional[str]
    elapsed: Optional[float]
    error: Optional[str] = None


def positive_float(value: str) -> float:
    try:
        val = float(value)
    except ValueError as exc:  # pragma: no cover - argparse handles messaging
        raise argparse.ArgumentTypeError("must be a number") from exc
    if val <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return val


def positive_int(value: str) -> int:
    try:
        val = int(value)
    except ValueError as exc:  # pragma: no cover - argparse handles messaging
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if val <= 0:
        raise argparse.ArgumentTypeError("must be >= 1")
    return val


def parse_arguments(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check HTTP status codes for URLs concurrently.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("urls", nargs="*", help="URLs to check")
    parser.add_argument(
        "--file",
        type=Path,
        action="append",
        help="Read URLs from a file (one per line). Can be provided multiple times.",
    )
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read URLs from standard input even if the stream is a TTY.",
    )
    parser.add_argument(
        "--timeout",
        type=positive_float,
        default=10.0,
        help="Request timeout in seconds.",
    )
    parser.add_argument(
        "--max-workers",
        type=positive_int,
        default=8,
        help="Number of concurrent workers.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON instead of a table.",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity.",
    )
    return parser.parse_args(argv)


def setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(levelname)s: %(message)s",
    )


def collect_urls(args: argparse.Namespace) -> List[str]:
    urls: List[str] = []
    urls.extend(args.urls)

    if args.file:
        for path in args.file:
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as exc:
                raise ValueError(f"Failed to read URLs from {path}: {exc}") from exc
            urls.extend(parse_urls_from_text(text.splitlines()))

    should_read_stdin = args.stdin or not sys.stdin.isatty()
    if should_read_stdin:
        urls.extend(parse_urls_from_text(sys.stdin))

    filtered = [url for url in (u.strip() for u in urls) if url]
    if not filtered:
        raise ValueError("No URLs provided.")
    return filtered


def parse_urls_from_text(lines: Iterable[str]) -> List[str]:
    parsed: List[str] = []
    for raw in lines:
        url = raw.strip()
        if not url or url.startswith("#"):
            continue
        parsed.append(url)
    return parsed


def check_url(url: str, timeout: float) -> UrlStatusResult:
    attempts = ("HEAD", "GET")
    last_error: Optional[str] = None
    for method in attempts:
        try:
            if method == "HEAD":
                response = requests.head(
                    url,
                    allow_redirects=True,
                    timeout=timeout,
                    headers=DEFAULT_HEADERS,
                )
            else:
                response = requests.get(
                    url,
                    allow_redirects=True,
                    timeout=timeout,
                    headers=DEFAULT_HEADERS,
                    stream=True,
                )
            try:
                status = response.status_code
                final_url = response.url
                elapsed = (
                    response.elapsed.total_seconds() if response.elapsed else None
                )
            finally:
                response.close()

            if method == "HEAD" and status in {405, 501}:
                last_error = f"HEAD returned status {status}"
                logger.debug("HEAD not allowed for %s; retrying with GET", url)
                continue

            ok = 200 <= status < 400
            return UrlStatusResult(
                url=url,
                status=status,
                ok=ok,
                method=method,
                final_url=final_url,
                elapsed=elapsed,
                error=last_error,
            )
        except requests.RequestException as exc:
            last_error = str(exc)
            if method == "HEAD":
                logger.debug(
                    "HEAD request failed for %s: %s; falling back to GET", url, exc
                )
                continue
            return UrlStatusResult(
                url=url,
                status=None,
                ok=False,
                method=method,
                final_url=None,
                elapsed=None,
                error=last_error,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            logger.debug("Unexpected error for %s via %s: %s", url, method, exc)
            return UrlStatusResult(
                url=url,
                status=None,
                ok=False,
                method=method,
                final_url=None,
                elapsed=None,
                error=last_error,
            )

    return UrlStatusResult(
        url=url,
        status=None,
        ok=False,
        method=attempts[-1],
        final_url=None,
        elapsed=None,
        error=last_error,
    )


def run_checks(urls: List[str], timeout: float, max_workers: int) -> List[UrlStatusResult]:
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(lambda u: check_url(u, timeout), urls))
    return results


def format_elapsed(elapsed: Optional[float]) -> str:
    if elapsed is None:
        return "-"
    return f"{elapsed:.3f}s"


def render_table(results: List[UrlStatusResult]) -> str:
    headers = ["URL", "Status", "OK", "Method", "Elapsed", "Final URL", "Error"]
    rows = []
    for result in results:
        rows.append(
            [
                result.url,
                str(result.status) if result.status is not None else "-",
                "yes" if result.ok else "no",
                result.method,
                format_elapsed(result.elapsed),
                result.final_url or "-",
                result.error or "",
            ]
        )
    widths = [len(header) for header in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def format_row(row: List[str]) -> str:
        return " | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row))

    lines = [format_row(headers), "-+-".join("-" * width for width in widths)]
    lines.extend(format_row(row) for row in rows)
    return "\n".join(lines)


def output_results(results: List[UrlStatusResult], as_json: bool) -> None:
    if as_json:
        payload = [asdict(result) for result in results]
        print(json.dumps(payload, indent=2))
    else:
        print(render_table(results))


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_arguments(argv)
    setup_logging(args.log_level)

    try:
        urls = collect_urls(args)
    except ValueError as exc:
        logger.error(str(exc))
        return 1

    logger.info(
        "Checking %d URL%s with max_workers=%d",
        len(urls),
        "s" if len(urls) != 1 else "",
        args.max_workers,
    )

    results = run_checks(urls, args.timeout, args.max_workers)
    output_results(results, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
