"""Dice roller with standard RPG notation support.

Supports standard dice notation (d20, 3d6+2), advantage/disadvantage,
keep highest/lowest, and multiple rolls with detailed output.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class DiceRollerError(RuntimeError):
    """Raised when dice rolling fails."""


def parse_dice_notation(notation: str) -> Tuple[int, int, int, str]:
    """Parse dice notation into components.

    Args:
        notation: Dice notation like "3d6+2", "d20", "4d6k3"

    Returns:
        Tuple of (num_dice, num_sides, modifier, keep_mode)
        keep_mode can be: "" (none), "kh3" (keep highest 3), "kl2" (keep lowest 2)

    Raises:
        DiceRollerError: If notation is invalid
    """
    notation = notation.strip().lower().replace(" ", "")

    # Match patterns like: d20, 3d6, 2d8+5, 4d6k3, 4d6kh3, 4d6kl2
    pattern = r"^(\d*)d(\d+)(k[hl]?\d+)?([+\-]\d+)?$"
    match = re.match(pattern, notation)

    if not match:
        raise DiceRollerError(f"Invalid dice notation: {notation}")

    num_dice = int(match.group(1)) if match.group(1) else 1
    num_sides = int(match.group(2))
    keep_expr = match.group(3) or ""
    modifier = int(match.group(4)) if match.group(4) else 0

    if num_dice < 1:
        raise DiceRollerError("Number of dice must be at least 1")
    if num_sides < 2:
        raise DiceRollerError("Number of sides must be at least 2")

    return num_dice, num_sides, modifier, keep_expr


def parse_keep_expression(keep_expr: str, num_dice: int) -> Tuple[str, int]:
    """Parse keep expression like 'k3', 'kh3', 'kl2'.

    Returns:
        Tuple of (mode, count) where mode is 'highest' or 'lowest'
    """
    if not keep_expr:
        return "", 0

    if keep_expr.startswith("kh"):
        return "highest", int(keep_expr[2:])
    elif keep_expr.startswith("kl"):
        return "lowest", int(keep_expr[2:])
    elif keep_expr.startswith("k"):
        # Default to keep highest
        return "highest", int(keep_expr[1:])

    return "", 0


def roll_dice(
    num_dice: int,
    num_sides: int,
    modifier: int = 0,
    keep_mode: str = "",
    seed: int | None = None,
) -> Dict[str, Any]:
    """Roll dice and return results.

    Args:
        num_dice: Number of dice to roll
        num_sides: Number of sides per die
        modifier: Modifier to add to total
        keep_mode: Keep expression like "kh3" or "kl2"
        seed: Random seed for reproducibility

    Returns:
        Dict with rolls, kept_rolls, dropped_rolls, total, and details
    """
    if seed is not None:
        random.seed(seed)

    # Roll all dice
    rolls = [random.randint(1, num_sides) for _ in range(num_dice)]

    # Handle keep logic
    kept_rolls = rolls.copy()
    dropped_rolls: List[int] = []

    if keep_mode:
        mode, count = parse_keep_expression(keep_mode, num_dice)
        if count >= num_dice:
            logger.warning(
                f"Keep count ({count}) >= num dice ({num_dice}), keeping all"
            )
        elif count < 1:
            raise DiceRollerError("Keep count must be at least 1")
        else:
            sorted_rolls = sorted(rolls, reverse=(mode == "highest"))
            kept_rolls = sorted_rolls[:count]
            dropped_rolls = sorted_rolls[count:]

    total = sum(kept_rolls) + modifier

    return {
        "rolls": rolls,
        "kept_rolls": kept_rolls,
        "dropped_rolls": dropped_rolls,
        "modifier": modifier,
        "total": total,
        "notation": f"{num_dice}d{num_sides}{keep_mode}{'+' if modifier > 0 else ''}{modifier if modifier else ''}",
    }


def roll_advantage(num_sides: int = 20, seed: int | None = None) -> Dict[str, Any]:
    """Roll with advantage (roll twice, keep higher).

    Args:
        num_sides: Number of sides (default 20 for d20)
        seed: Random seed

    Returns:
        Dict with both rolls and the result
    """
    if seed is not None:
        random.seed(seed)

    roll1 = random.randint(1, num_sides)
    roll2 = random.randint(1, num_sides)
    result = max(roll1, roll2)

    return {
        "type": "advantage",
        "rolls": [roll1, roll2],
        "kept": result,
        "dropped": min(roll1, roll2),
        "total": result,
    }


def roll_disadvantage(num_sides: int = 20, seed: int | None = None) -> Dict[str, Any]:
    """Roll with disadvantage (roll twice, keep lower).

    Args:
        num_sides: Number of sides (default 20 for d20)
        seed: Random seed

    Returns:
        Dict with both rolls and the result
    """
    if seed is not None:
        random.seed(seed)

    roll1 = random.randint(1, num_sides)
    roll2 = random.randint(1, num_sides)
    result = min(roll1, roll2)

    return {
        "type": "disadvantage",
        "rolls": [roll1, roll2],
        "kept": result,
        "dropped": max(roll1, roll2),
        "total": result,
    }


def format_roll_result(result: Dict[str, Any], verbose: bool = False) -> str:
    """Format roll result for display.

    Args:
        result: Result dict from roll_dice or roll_advantage/disadvantage
        verbose: Whether to show detailed breakdown

    Returns:
        Formatted string
    """
    if result.get("type") in ["advantage", "disadvantage"]:
        if verbose:
            return (
                f"{result['type'].capitalize()}: "
                f"[{', '.join(map(str, result['rolls']))}] "
                f"→ kept {result['kept']}, dropped {result['dropped']} "
                f"= {result['total']}"
            )
        return f"{result['type'].capitalize()}: {result['total']}"

    # Standard dice roll
    if verbose:
        output = f"Rolled {result['notation']}: "
        output += f"[{', '.join(map(str, result['rolls']))}]"

        if result["dropped_rolls"]:
            output += f" (kept: {result['kept_rolls']}, dropped: {result['dropped_rolls']})"

        if result["modifier"]:
            output += f" {'+' if result['modifier'] > 0 else ''}{result['modifier']}"

        output += f" = {result['total']}"
        return output

    return f"{result['notation']} = {result['total']}"


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Roll dice using standard RPG notation.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  dice_roller.py d20                    # Roll a d20
  dice_roller.py 3d6+2                  # Roll 3d6 and add 2
  dice_roller.py 4d6k3                  # Roll 4d6, keep highest 3
  dice_roller.py 4d6kl2                 # Roll 4d6, keep lowest 2
  dice_roller.py d20 --advantage        # Roll d20 with advantage
  dice_roller.py d20 --disadvantage     # Roll d20 with disadvantage
  dice_roller.py 2d10+5 --repeat 3      # Roll 3 times
  dice_roller.py 3d6 --json             # Output as JSON
        """,
    )
    parser.add_argument(
        "notation",
        nargs="?",
        default="d20",
        help="Dice notation (e.g., d20, 3d6+2, 4d6k3)",
    )
    parser.add_argument(
        "--advantage",
        action="store_true",
        help="Roll with advantage (2d20, keep higher)",
    )
    parser.add_argument(
        "--disadvantage",
        action="store_true",
        help="Roll with disadvantage (2d20, keep lower)",
    )
    parser.add_argument(
        "--repeat", type=int, default=1, help="Number of times to roll"
    )
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
    parser.add_argument(
        "--verbose", action="store_true", help="Show detailed roll breakdown"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
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

    if args.advantage and args.disadvantage:
        logger.error("Cannot use both --advantage and --disadvantage")
        return 2

    results: List[Dict[str, Any]] = []

    try:
        for i in range(args.repeat):
            # Use seed for first roll, then None for subsequent rolls
            current_seed = args.seed if args.seed is not None and i == 0 else None

            if args.advantage:
                result = roll_advantage(seed=current_seed)
            elif args.disadvantage:
                result = roll_disadvantage(seed=current_seed)
            else:
                num_dice, num_sides, modifier, keep_mode = parse_dice_notation(
                    args.notation
                )
                result = roll_dice(
                    num_dice, num_sides, modifier, keep_mode, seed=current_seed
                )

            results.append(result)
    except DiceRollerError as ex:
        logger.error(str(ex))
        return 1
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Unexpected error: {ex}")
        return 1

    if args.json:
        if args.repeat == 1:
            print(json.dumps(results[0], indent=2))
        else:
            print(json.dumps(results, indent=2))
    else:
        for i, result in enumerate(results):
            if args.repeat > 1:
                print(f"Roll {i + 1}: {format_roll_result(result, args.verbose)}")
            else:
                print(format_roll_result(result, args.verbose))

        # Show summary if multiple rolls
        if args.repeat > 1 and not args.verbose:
            totals = [r["total"] for r in results]
            print(f"\nSummary: min={min(totals)}, max={max(totals)}, avg={sum(totals) / len(totals):.1f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
