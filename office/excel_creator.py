"""Excel utility: inspect and modify sheets via a simple CLI.

Requires `pandas` (and `openpyxl` for .xlsx I/O):
    pip install pandas openpyxl
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelError(RuntimeError):
    """Raised when Excel operations fail."""


def load_workbook(path: Path, sheet_name: str) -> Tuple[pd.DataFrame, list[int | str]]:
    """Load a sheet into a DataFrame and return (df, sheet_names)."""
    try:
        xls = pd.ExcelFile(path)
        sheet_names = xls.sheet_names
        df = pd.read_excel(xls, sheet_name=sheet_name)
        return df, sheet_names
    except Exception as ex:  # noqa: BLE001
        raise ExcelError(f"Failed to read '{path}': {ex}") from ex


def save_workbook(df: pd.DataFrame, path: Path, sheet_name: str) -> None:
    try:
        df.to_excel(path, sheet_name=sheet_name, index=False, engine="openpyxl")
    except Exception as ex:  # noqa: BLE001
        raise ExcelError(f"Failed to write '{path}': {ex}") from ex


def get_cell(df: pd.DataFrame, row: int, col: int) -> Any:
    return df.iat[row, col]


def set_cell(df: pd.DataFrame, row: int, col: int, value: Any) -> None:
    df.iat[row, col] = value


def append_row(df: pd.DataFrame, values: Sequence[Any]) -> pd.DataFrame:
    if len(values) != len(df.columns):
        raise ExcelError(
            f"Row length {len(values)} does not match number of columns {len(df.columns)}"
        )
    new_df = pd.concat(
        [df, pd.DataFrame([values], columns=df.columns)], ignore_index=True
    )
    return new_df


def append_column(
    df: pd.DataFrame, name: str, default_value: Any = None
) -> pd.DataFrame:
    if name in df.columns:
        raise ExcelError(f"Column already exists: {name}")
    new_df = df.copy()
    new_df[name] = default_value
    return new_df


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect and modify Excel files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Path to input .xlsx file")
    parser.add_argument("--sheet", type=str, default="Sheet1", help="Sheet name")
    parser.add_argument(
        "--output", type=Path, help="Path to save .xlsx; defaults to input"
    )

    ops = parser.add_mutually_exclusive_group()
    ops.add_argument("--show", action="store_true", help="Print DataFrame and schema")
    ops.add_argument(
        "--get-cell",
        nargs=2,
        type=int,
        metavar=("ROW", "COL"),
        help="Read a cell by (row, col) 0-based",
    )
    ops.add_argument(
        "--set-cell",
        nargs=3,
        metavar=("ROW", "COL", "VALUE"),
        help="Write a cell (value is treated as string)",
    )
    ops.add_argument(
        "--append-row", type=str, help="JSON array of values to append as a row"
    )
    ops.add_argument(
        "--append-col",
        nargs=2,
        metavar=("NAME", "DEFAULT"),
        help="Append a new column with default value",
    )

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    if not args.input.exists():
        logger.error(f"Input not found: {args.input}")
        return 2

    try:
        df, sheet_names = load_workbook(args.input, args.sheet)
    except ExcelError as ex:
        logger.error(str(ex))
        return 2

    if args.show:
        logger.info(f"Available sheets: {', '.join(str(s) for s in sheet_names)}")
        logger.info(f"Shape: {df.shape[0]} rows x {df.shape[1]} cols")
        logger.info(f"Columns: {list(df.columns)}")
        print(df)
        return 0

    if args.get_cell is not None:
        r, c = args.get_cell
        try:
            value = get_cell(df, r, c)
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to read cell ({r}, {c}): {ex}")
            return 1
        print(value)
        return 0

    modified_df = df

    if args.set_cell is not None:
        r_str, c_str, val = args.set_cell
        try:
            r, c = int(r_str), int(c_str)
            set_cell(modified_df, r, c, val)
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to write cell ({r_str}, {c_str}): {ex}")
            return 1

    if args.append_row is not None:
        try:
            values = json.loads(args.append_row)
            if not isinstance(values, list):
                raise ValueError("append-row must be a JSON array")
            modified_df = append_row(modified_df, values)
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to append row: {ex}")
            return 1

    if args.append_col is not None:
        name, default = args.append_col
        try:
            modified_df = append_column(modified_df, name, default)
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to append column '{name}': {ex}")
            return 1

    if modified_df is df and args.output is None:
        logger.info("No modifications made; nothing to save.")
        return 0

    out_path = args.output or args.input
    try:
        save_workbook(modified_df, out_path, args.sheet)
    except ExcelError as ex:
        logger.error(str(ex))
        return 1

    logger.info(f"Saved to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
