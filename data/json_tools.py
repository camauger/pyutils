"""JSON processing utilities - query, transform, and validate JSON files."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def query_json(data: Any, path: str) -> Any:
    """Simple JSONPath-like query.

    Supports basic paths like:
    - "users" - top level key
    - "users.0" - array index
    - "users.0.name" - nested access
    """
    parts = path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        elif isinstance(current, list):
            try:
                index = int(part)
                current = current[index]
            except (ValueError, IndexError):
                return None
        else:
            return None

        if current is None:
            return None

    return current


def flatten_json(data: Any, prefix: str = "") -> dict[str, Any]:
    """Flatten nested JSON structure."""
    result = {}

    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                result.update(flatten_json(value, new_key))
            else:
                result[new_key] = value
    elif isinstance(data, list):
        for i, item in enumerate(data):
            new_key = f"{prefix}.{i}" if prefix else str(i)
            if isinstance(item, (dict, list)):
                result.update(flatten_json(item, new_key))
            else:
                result[new_key] = item
    else:
        result[prefix] = data

    return result


def merge_json(files: list[Path]) -> Any:
    """Merge multiple JSON files."""
    merged = {}

    for file in files:
        with file.open("r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                merged.update(data)
            else:
                logger.warning(f"Skipping non-dict file: {file}")

    return merged


def to_yaml(data: Any) -> str:
    """Convert JSON to YAML format (simple implementation)."""
    try:
        import yaml

        return yaml.dump(data, default_flow_style=False)
    except ImportError:
        logger.error("PyYAML not installed. Install with: pip install pyyaml")
        return ""


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="JSON processing utilities",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Query command
    query_parser = subparsers.add_parser("query", help="Query JSON with path")
    query_parser.add_argument("file", type=Path, help="JSON file")
    query_parser.add_argument("path", help="Query path (e.g., 'users.0.name')")

    # Pretty command
    pretty_parser = subparsers.add_parser("pretty", help="Pretty print JSON")
    pretty_parser.add_argument("file", type=Path, help="JSON file")
    pretty_parser.add_argument("--indent", type=int, default=2, help="Indentation spaces")
    pretty_parser.add_argument("--output", type=Path, help="Output file")

    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge JSON files")
    merge_parser.add_argument("files", nargs="+", type=Path, help="JSON files to merge")
    merge_parser.add_argument("--output", type=Path, required=True, help="Output file")

    # Flatten command
    flatten_parser = subparsers.add_parser("flatten", help="Flatten nested JSON")
    flatten_parser.add_argument("file", type=Path, help="JSON file")
    flatten_parser.add_argument("--output", type=Path, help="Output file")

    # to-yaml command
    yaml_parser = subparsers.add_parser("to-yaml", help="Convert to YAML")
    yaml_parser.add_argument("file", type=Path, help="JSON file")
    yaml_parser.add_argument("--output", type=Path, help="Output file")

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(levelname)s: %(message)s",
    )

    if not args.command:
        logger.error("No command specified")
        return 1

    try:
        if args.command == "query":
            with args.file.open("r") as f:
                data = json.load(f)

            result = query_json(data, args.path)

            if result is None:
                logger.warning(f"Path '{args.path}' not found")
                return 1

            print(json.dumps(result, indent=2))

        elif args.command == "pretty":
            with args.file.open("r") as f:
                data = json.load(f)

            pretty = json.dumps(data, indent=args.indent)

            if args.output:
                args.output.write_text(pretty)
                logger.info(f"Pretty JSON written to {args.output}")
            else:
                print(pretty)

        elif args.command == "merge":
            merged = merge_json(args.files)
            logger.info(f"Merged {len(args.files)} files")

            args.output.write_text(json.dumps(merged, indent=2))
            logger.info(f"Merged JSON written to {args.output}")

        elif args.command == "flatten":
            with args.file.open("r") as f:
                data = json.load(f)

            flattened = flatten_json(data)
            output_str = json.dumps(flattened, indent=2)

            if args.output:
                args.output.write_text(output_str)
                logger.info(f"Flattened JSON written to {args.output}")
            else:
                print(output_str)

        elif args.command == "to-yaml":
            with args.file.open("r") as f:
                data = json.load(f)

            yaml_str = to_yaml(data)
            if not yaml_str:
                return 1

            if args.output:
                args.output.write_text(yaml_str)
                logger.info(f"YAML written to {args.output}")
            else:
                print(yaml_str)

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

