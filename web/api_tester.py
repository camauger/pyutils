"""API testing tool for REST endpoints."""

from __future__ import annotations

import argparse
import base64
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)


def make_request(
    method: str,
    url: str,
    headers: Dict[str, str] | None = None,
    data: str | None = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Make HTTP request and return result."""
    headers = headers or {}

    try:
        if method.upper() in ["POST", "PUT", "PATCH"] and data:
            # Try to parse as JSON
            try:
                json_data = json.loads(data)
                response = requests.request(
                    method.upper(),
                    url,
                    json=json_data,
                    headers=headers,
                    timeout=timeout,
                )
            except json.JSONDecodeError:
                # Send as form data
                response = requests.request(
                    method.upper(),
                    url,
                    data=data,
                    headers=headers,
                    timeout=timeout,
                )
        else:
            response = requests.request(
                method.upper(),
                url,
                headers=headers,
                timeout=timeout,
            )

        result = {
            "success": True,
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
        }

        # Try to parse JSON response
        try:
            result["json"] = response.json()
        except json.JSONDecodeError:
            pass

        return result

    except requests.RequestException as e:
        return {
            "success": False,
            "error": str(e),
        }


def parse_headers(header_list: list[str]) -> Dict[str, str]:
    """Parse header strings into dict."""
    headers = {}
    for h in header_list:
        if ":" in h:
            key, value = h.split(":", 1)
            headers[key.strip()] = value.strip()
    return headers


def add_auth(headers: Dict[str, str], auth_type: str | None, auth_value: str | None) -> None:
    """Add authentication to headers."""
    if not auth_type or not auth_value:
        return

    if auth_type == "bearer":
        headers["Authorization"] = f"Bearer {auth_value}"
    elif auth_type == "basic":
        # Expect format: username:password
        encoded = base64.b64encode(auth_value.encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Test REST APIs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument("method", nargs="?", help="HTTP method (GET, POST, PUT, DELETE, PATCH)")
    parser.add_argument("url", nargs="?", help="URL to request")

    parser.add_argument("--data", help="Request body data (JSON or form)")
    parser.add_argument("--header", "-H", action="append", default=[], help="Custom header (repeatable)")
    parser.add_argument("--auth-type", choices=["bearer", "basic"], help="Authentication type")
    parser.add_argument("--auth-value", help="Authentication value")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds")

    parser.add_argument("--config", type=Path, help="JSON config file with batch tests")
    parser.add_argument("--output", type=Path, help="Save response to file")

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )

    return parser.parse_args()


def run_batch_tests(config_file: Path) -> int:
    """Run batch tests from config file."""
    with config_file.open("r") as f:
        config = json.load(f)

    tests = config.get("tests", [])
    results = []

    for test in tests:
        name = test.get("name", "Unnamed test")
        logger.info(f"Running test: {name}")

        headers = test.get("headers", {})
        if test.get("auth"):
            add_auth(headers, test["auth"].get("type"), test["auth"].get("value"))

        result = make_request(
            method=test.get("method", "GET"),
            url=test["url"],
            headers=headers,
            data=test.get("data"),
            timeout=test.get("timeout", 30),
        )

        result["test_name"] = name

        # Check assertions
        assertions = test.get("assert", {})
        if assertions:
            result["assertions"] = {}
            if "status_code" in assertions:
                expected = assertions["status_code"]
                actual = result.get("status_code")
                result["assertions"]["status_code"] = (expected == actual, f"Expected {expected}, got {actual}")

        results.append(result)

    # Print results
    print(json.dumps(results, indent=2))

    # Return 0 if all tests passed
    failed = sum(
        1
        for r in results
        if not r.get("success", False)
        or any(not passed for passed, _ in r.get("assertions", {}).values())
    )

    if failed:
        logger.error(f"{failed} test(s) failed")
        return 1

    logger.info("All tests passed")
    return 0


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s: %(message)s",
    )

    # Batch mode
    if args.config:
        return run_batch_tests(args.config)

    # Single request mode
    if not args.method or not args.url:
        logger.error("METHOD and URL required (or use --config for batch mode)")
        return 1

    headers = parse_headers(args.header)
    add_auth(headers, args.auth_type, args.auth_value)

    logger.info(f"{args.method} {args.url}")

    result = make_request(
        method=args.method,
        url=args.url,
        headers=headers,
        data=args.data,
        timeout=args.timeout,
    )

    output = json.dumps(result, indent=2)

    if args.output:
        args.output.write_text(output)
        logger.info(f"Response saved to {args.output}")
    else:
        print(output)

    return 0 if result.get("success", False) else 1


if __name__ == "__main__":
    sys.exit(main())

