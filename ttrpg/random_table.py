"""Random table processor for TTRPG random encounters and events.

Load and roll on random tables from JSON/CSV, supporting weighted
entries, nested tables, and multiple roll formats (d100, d20, etc.).
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class RandomTableError(RuntimeError):
    """Raised when random table operations fail."""


def load_table_from_json(file_path: str) -> Dict[str, Any]:
    """Load random table from JSON file.

    Expected format:
    {
        "name": "Table Name",
        "dice": "d100",  // or "d20", "d6", "weighted"
        "entries": [
            {"range": "1-20", "result": "Common event"},
            {"range": "21-40", "result": "Uncommon event"},
            {"range": "41-100", "result": "Rare event"}
        ]
    }

    Or for weighted:
    {
        "name": "Weighted Table",
        "dice": "weighted",
        "entries": [
            {"weight": 50, "result": "Very common"},
            {"weight": 30, "result": "Common"},
            {"weight": 15, "result": "Uncommon"},
            {"weight": 5, "result": "Rare"}
        ]
    }

    Args:
        file_path: Path to JSON file

    Returns:
        Table dictionary
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            table = json.load(f)

        if "entries" not in table:
            raise RandomTableError("Table must have 'entries' field")

        return table
    except json.JSONDecodeError as ex:
        raise RandomTableError(f"Invalid JSON: {ex}") from ex
    except FileNotFoundError as ex:
        raise RandomTableError(f"File not found: {file_path}") from ex


def load_table_from_csv(file_path: str, dice: str = "d100") -> Dict[str, Any]:
    """Load random table from CSV file.

    Expected format (for range-based):
    range,result
    1-20,Common event
    21-40,Uncommon event
    41-100,Rare event

    Or for weighted:
    weight,result
    50,Very common
    30,Common
    15,Uncommon
    5,Rare

    Args:
        file_path: Path to CSV file
        dice: Dice type (d100, d20, d6, weighted)

    Returns:
        Table dictionary
    """
    try:
        entries: List[Dict[str, Any]] = []

        with open(file_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for row in reader:
                if dice == "weighted":
                    if "weight" not in row or "result" not in row:
                        raise RandomTableError(
                            "CSV must have 'weight' and 'result' columns for weighted tables"
                        )
                    entries.append(
                        {"weight": int(row["weight"]), "result": row["result"]}
                    )
                else:
                    if "range" not in row or "result" not in row:
                        raise RandomTableError(
                            "CSV must have 'range' and 'result' columns"
                        )
                    entries.append({"range": row["range"], "result": row["result"]})

        return {
            "name": Path(file_path).stem,
            "dice": dice,
            "entries": entries,
        }
    except FileNotFoundError as ex:
        raise RandomTableError(f"File not found: {file_path}") from ex
    except (ValueError, KeyError) as ex:
        raise RandomTableError(f"Invalid CSV format: {ex}") from ex


def parse_dice_type(dice_str: str) -> int:
    """Parse dice type to number of sides.

    Args:
        dice_str: Dice string like "d100", "d20", "d6"

    Returns:
        Number of sides
    """
    dice_str = dice_str.lower().strip()

    if dice_str.startswith("d"):
        try:
            return int(dice_str[1:])
        except ValueError as ex:
            raise RandomTableError(f"Invalid dice type: {dice_str}") from ex

    raise RandomTableError(f"Invalid dice type: {dice_str}")


def parse_range(range_str: str) -> Tuple[int, int]:
    """Parse range string like "1-20" or "42".

    Args:
        range_str: Range string

    Returns:
        Tuple of (min, max)
    """
    range_str = range_str.strip()

    if "-" in range_str:
        parts = range_str.split("-")
        if len(parts) != 2:
            raise RandomTableError(f"Invalid range: {range_str}")
        return int(parts[0]), int(parts[1])

    # Single number
    num = int(range_str)
    return num, num


def roll_on_range_table(
    table: Dict[str, Any], seed: int | None = None
) -> Dict[str, Any]:
    """Roll on a range-based table.

    Args:
        table: Table dictionary
        seed: Random seed

    Returns:
        Result dictionary with roll and result
    """
    if seed is not None:
        random.seed(seed)

    dice_type = table.get("dice", "d100")
    num_sides = parse_dice_type(dice_type)

    roll = random.randint(1, num_sides)

    # Find matching entry
    for entry in table["entries"]:
        min_val, max_val = parse_range(entry["range"])

        if min_val <= roll <= max_val:
            return {
                "table": table.get("name", "Unknown"),
                "dice": dice_type,
                "roll": roll,
                "result": entry["result"],
            }

    # No match found
    raise RandomTableError(f"No entry found for roll {roll} on {dice_type}")


def roll_on_weighted_table(
    table: Dict[str, Any], seed: int | None = None
) -> Dict[str, Any]:
    """Roll on a weighted table.

    Args:
        table: Table dictionary
        seed: Random seed

    Returns:
        Result dictionary
    """
    if seed is not None:
        random.seed(seed)

    entries = table["entries"]
    weights = [entry["weight"] for entry in entries]
    results = [entry["result"] for entry in entries]

    chosen = random.choices(results, weights=weights, k=1)[0]

    return {
        "table": table.get("name", "Unknown"),
        "dice": "weighted",
        "result": chosen,
    }


def roll_on_table(table: Dict[str, Any], seed: int | None = None) -> Dict[str, Any]:
    """Roll on a table (auto-detect type).

    Args:
        table: Table dictionary
        seed: Random seed

    Returns:
        Result dictionary
    """
    dice_type = table.get("dice", "d100").lower()

    if dice_type == "weighted":
        return roll_on_weighted_table(table, seed)

    return roll_on_range_table(table, seed)


def create_example_table(table_type: str) -> str:
    """Create an example table file.

    Args:
        table_type: Type of table (d100, d20, weighted)

    Returns:
        JSON string of example table
    """
    if table_type == "d100":
        table = {
            "name": "Random Encounters (d100)",
            "dice": "d100",
            "entries": [
                {"range": "1-10", "result": "Goblin ambush (1d4 goblins)"},
                {"range": "11-25", "result": "Wandering merchant"},
                {"range": "26-40", "result": "Pack of wolves (2d4 wolves)"},
                {"range": "41-55", "result": "Abandoned campsite"},
                {"range": "56-70", "result": "Travelling minstrel"},
                {"range": "71-80", "result": "Orc war party (1d6+2 orcs)"},
                {"range": "81-90", "result": "Hidden treasure (100gp)"},
                {"range": "91-95", "result": "Dragon flying overhead"},
                {"range": "96-100", "result": "Ancient ruins"},
            ],
        }
    elif table_type == "d20":
        table = {
            "name": "Tavern Events (d20)",
            "dice": "d20",
            "entries": [
                {"range": "1-5", "result": "Quiet evening, nothing happens"},
                {"range": "6-10", "result": "Local drunk starts a fight"},
                {"range": "11-14", "result": "Mysterious stranger offers quest"},
                {"range": "15-17", "result": "Bard performs for coin"},
                {"range": "18-19", "result": "Guards arrive looking for criminal"},
                {"range": "20", "result": "Fire breaks out in kitchen"},
            ],
        }
    else:  # weighted
        table = {
            "name": "Loot Quality (Weighted)",
            "dice": "weighted",
            "entries": [
                {"weight": 50, "result": "Common (1d10 gold)"},
                {"weight": 30, "result": "Uncommon (2d10 gold, simple magic item)"},
                {"weight": 15, "result": "Rare (5d10 gold, rare magic item)"},
                {"weight": 4, "result": "Very Rare (10d10 gold, very rare item)"},
                {"weight": 1, "result": "Legendary (50d10 gold, legendary item)"},
            ],
        }

    return json.dumps(table, indent=2)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Roll on random tables for TTRPG encounters and events.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  # Roll on a table from JSON
  random_table.py encounters.json

  # Roll multiple times
  random_table.py encounters.json --repeat 5

  # Create example tables
  random_table.py --example d100 --output encounters.json
  random_table.py --example weighted --output loot.json

  # Load from CSV
  random_table.py table.csv --csv --dice d20
        """,
    )
    parser.add_argument(
        "table_file", nargs="?", help="Path to table file (JSON or CSV)"
    )
    parser.add_argument(
        "--csv",
        action="store_true",
        help="Load from CSV instead of JSON",
    )
    parser.add_argument(
        "--dice",
        default="d100",
        help="Dice type for CSV tables (d100, d20, d6, weighted)",
    )
    parser.add_argument(
        "--repeat", type=int, default=1, help="Number of times to roll"
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument(
        "--example",
        choices=["d100", "d20", "weighted"],
        help="Create example table of given type",
    )
    parser.add_argument(
        "--output", help="Output file for example table (use with --example)"
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="WARNING",
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.WARNING),
        format="%(message)s",
        stream=sys.stderr,
    )

    # Handle example generation
    if args.example:
        example = create_example_table(args.example)

        if args.output:
            try:
                with open(args.output, "w", encoding="utf-8") as f:
                    f.write(example)
                logger.info(f"Example table written to {args.output}")
            except IOError as ex:
                logger.error(f"Failed to write file: {ex}")
                return 1
        else:
            print(example)

        return 0

    # Validate arguments
    if not args.table_file:
        logger.error("Please provide a table file or use --example")
        return 2

    if args.repeat < 1:
        logger.error("--repeat must be at least 1")
        return 2

    # Load table
    try:
        if args.csv:
            table = load_table_from_csv(args.table_file, args.dice)
        else:
            table = load_table_from_json(args.table_file)
    except RandomTableError as ex:
        logger.error(str(ex))
        return 1

    # Roll on table
    results: List[Dict[str, Any]] = []

    try:
        for i in range(args.repeat):
            # Use seed for first roll, then None
            current_seed = args.seed if args.seed is not None and i == 0 else None
            result = roll_on_table(table, seed=current_seed)
            results.append(result)
    except RandomTableError as ex:
        logger.error(str(ex))
        return 1

    # Output results
    if args.json:
        if args.repeat == 1:
            print(json.dumps(results[0], indent=2))
        else:
            print(json.dumps(results, indent=2))
    else:
        for i, result in enumerate(results):
            if args.repeat > 1:
                print(f"Roll {i + 1}:", end=" ")

            if "roll" in result:
                print(f"[{result['roll']}] {result['result']}")
            else:
                print(result["result"])

    return 0


if __name__ == "__main__":
    sys.exit(main())
