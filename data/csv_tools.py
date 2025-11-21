"""CSV processing utilities without pandas dependency."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def filter_rows(
    data: List[Dict[str, Any]],
    column: str,
    operator: str,
    value: str,
) -> List[Dict[str, Any]]:
    """Filter rows by column criteria."""
    filtered = []
    for row in data:
        if column not in row:
            continue

        row_value = row[column]
        try:
            # Try numeric comparison
            num_val = float(value)
            num_row = float(row_value)
            if operator == "eq" and num_row == num_val:
                filtered.append(row)
            elif operator == "ne" and num_row != num_val:
                filtered.append(row)
            elif operator == "gt" and num_row > num_val:
                filtered.append(row)
            elif operator == "lt" and num_row < num_val:
                filtered.append(row)
            elif operator == "gte" and num_row >= num_val:
                filtered.append(row)
            elif operator == "lte" and num_row <= num_val:
                filtered.append(row)
        except ValueError:
            # String comparison
            if operator == "eq" and row_value == value:
                filtered.append(row)
            elif operator == "ne" and row_value != value:
                filtered.append(row)
            elif operator == "contains" and value in str(row_value):
                filtered.append(row)

    return filtered


def select_columns(data: List[Dict[str, Any]], columns: List[str]) -> List[Dict[str, Any]]:
    """Select specific columns."""
    return [{col: row.get(col, "") for col in columns} for row in data]


def merge_csv_files(files: List[Path]) -> List[Dict[str, Any]]:
    """Merge multiple CSV files."""
    merged_data = []
    for file in files:
        with file.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            merged_data.extend(list(reader))
    return merged_data


def to_markdown_table(data: List[Dict[str, Any]]) -> str:
    """Convert CSV data to Markdown table."""
    if not data:
        return ""

    headers = list(data[0].keys())
    lines = []

    # Header
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    # Rows
    for row in data:
        lines.append("| " + " | ".join(str(row.get(h, "")) for h in headers) + " |")

    return "\n".join(lines)


def get_stats(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get statistics about CSV data."""
    if not data:
        return {}

    stats = {
        "row_count": len(data),
        "columns": list(data[0].keys()),
        "column_count": len(data[0]),
        "unique_values": {},
    }

    for col in data[0].keys():
        values = [row.get(col) for row in data]
        stats["unique_values"][col] = len(set(v for v in values if v))

    return stats


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CSV processing utilities",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Filter command
    filter_parser = subparsers.add_parser("filter", help="Filter rows")
    filter_parser.add_argument("file", type=Path, help="CSV file")
    filter_parser.add_argument("--column", required=True, help="Column to filter on")
    filter_parser.add_argument(
        "--op",
        choices=["eq", "ne", "gt", "lt", "gte", "lte", "contains"],
        default="eq",
        help="Comparison operator",
    )
    filter_parser.add_argument("--value", required=True, help="Value to compare")
    filter_parser.add_argument("--output", type=Path, help="Output file")

    # Select command
    select_parser = subparsers.add_parser("select", help="Select columns")
    select_parser.add_argument("file", type=Path, help="CSV file")
    select_parser.add_argument("--columns", required=True, help="Comma-separated columns")
    select_parser.add_argument("--output", type=Path, help="Output file")

    # Merge command
    merge_parser = subparsers.add_parser("merge", help="Merge CSV files")
    merge_parser.add_argument("files", nargs="+", type=Path, help="CSV files to merge")
    merge_parser.add_argument("--output", type=Path, required=True, help="Output file")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Get statistics")
    stats_parser.add_argument("file", type=Path, help="CSV file")

    # to-json command
    json_parser = subparsers.add_parser("to-json", help="Convert to JSON")
    json_parser.add_argument("file", type=Path, help="CSV file")
    json_parser.add_argument("--output", type=Path, help="Output file")

    # to-markdown command
    md_parser = subparsers.add_parser("to-markdown", help="Convert to Markdown table")
    md_parser.add_argument("file", type=Path, help="CSV file")
    md_parser.add_argument("--output", type=Path, help="Output file")

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )

    return parser.parse_args()


def read_csv(file: Path) -> List[Dict[str, Any]]:
    """Read CSV file into list of dicts."""
    with file.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(data: List[Dict[str, Any]], file: Path) -> None:
    """Write list of dicts to CSV file."""
    if not data:
        return

    with file.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        writer.writeheader()
        writer.writerows(data)


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
        if args.command == "filter":
            data = read_csv(args.file)
            filtered = filter_rows(data, args.column, args.op, args.value)
            logger.info(f"Filtered {len(data)} rows to {len(filtered)} rows")

            if args.output:
                write_csv(filtered, args.output)
            else:
                for row in filtered:
                    print(json.dumps(row))

        elif args.command == "select":
            data = read_csv(args.file)
            columns = [c.strip() for c in args.columns.split(",")]
            selected = select_columns(data, columns)

            if args.output:
                write_csv(selected, args.output)
            else:
                write_csv(selected, Path("/dev/stdout") if sys.platform != "win32" else Path("CON"))

        elif args.command == "merge":
            merged = merge_csv_files(args.files)
            logger.info(f"Merged {len(args.files)} files into {len(merged)} rows")
            write_csv(merged, args.output)

        elif args.command == "stats":
            data = read_csv(args.file)
            stats = get_stats(data)
            print(json.dumps(stats, indent=2))

        elif args.command == "to-json":
            data = read_csv(args.file)
            json_str = json.dumps(data, indent=2)

            if args.output:
                args.output.write_text(json_str)
            else:
                print(json_str)

        elif args.command == "to-markdown":
            data = read_csv(args.file)
            md_table = to_markdown_table(data)

            if args.output:
                args.output.write_text(md_table)
            else:
                print(md_table)

    except Exception as e:
        logger.error(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

