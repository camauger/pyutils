"""Fantasy name generator for NPCs, places, and items.

Generates names using syllable patterns and Markov chains for various
fantasy races, locations, and magical items.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class NameGeneratorError(RuntimeError):
    """Raised when name generation fails."""


# Syllable banks for different name types
NAME_PATTERNS: Dict[str, Dict[str, List[str]]] = {
    "human_male": {
        "first": ["Ald", "Bran", "Ced", "Dar", "Ed", "Finn", "Gar", "Hal", "Ian"],
        "middle": ["ar", "or", "er", "an", "on", "en", "al", "ol"],
        "last": ["ric", "win", "ton", "wald", "bert", "fred", "red", "mund"],
    },
    "human_female": {
        "first": ["Al", "Bel", "Cel", "Del", "El", "Fel", "Gwen", "Hel", "Il"],
        "middle": ["a", "i", "e", "la", "na", "ra", "sa", "ta"],
        "last": ["ria", "dra", "na", "ra", "la", "ssa", "nda", "tha"],
    },
    "elf_male": {
        "first": ["Aeg", "Cael", "Gal", "Luth", "Sil", "Thran", "Leg", "El"],
        "middle": ["a", "o", "i", "or", "and", "ion", "dir"],
        "last": ["las", "dor", "mir", "dir", "ion", "oth", "wen", "rion"],
    },
    "elf_female": {
        "first": ["Ar", "Gal", "Cel", "Luth", "Sil", "Aer", "Nim"],
        "middle": ["wen", "iel", "eth", "iel", "anna", "reth"],
        "last": ["wen", "driel", "iel", "eth", "riel", "las", "anna"],
    },
    "dwarf_male": {
        "first": ["Bal", "Dur", "Gim", "Thor", "Bom", "Gro", "Dwa"],
        "middle": ["in", "li", "im", "or", "ur", "om"],
        "last": ["in", "li", "ur", "im", "or", "bur", "dil", "rim"],
    },
    "dwarf_female": {
        "first": ["Dis", "Gret", "Hild", "Kar", "Ris"],
        "middle": ["a", "i", "el", "da"],
        "last": ["da", "na", "tha", "dris", "nir"],
    },
    "orc": {
        "first": ["Grom", "Durg", "Thrak", "Ug", "Mag", "Grok", "Skar"],
        "middle": ["ash", "nak", "gul", "rak", "ush"],
        "last": ["ug", "tar", "ash", "gul", "nak", "rim"],
    },
    "halfling": {
        "first": ["Bil", "Mer", "Pip", "Sam", "Fro", "Tob"],
        "middle": ["bo", "ry", "pin", "wi", "do"],
        "last": ["bo", "pins", "wise", "gins", "dle"],
    },
}

PLACE_PATTERNS: Dict[str, List[str]] = {
    "prefix": [
        "North",
        "South",
        "East",
        "West",
        "New",
        "Old",
        "High",
        "Low",
        "Silver",
        "Gold",
        "Iron",
        "Stone",
        "River",
        "Lake",
        "Mountain",
        "Forest",
        "Shadow",
        "Dragon",
        "King",
        "Queen",
    ],
    "suffix": [
        "dale",
        "haven",
        "ford",
        "shire",
        "ton",
        "ville",
        "port",
        "burg",
        "wood",
        "mere",
        "mount",
        "fall",
        "gate",
        "keep",
        "hold",
    ],
}

ITEM_PATTERNS: Dict[str, List[str]] = {
    "prefix": [
        "Flaming",
        "Frost",
        "Thunder",
        "Lightning",
        "Shadow",
        "Vorpal",
        "Holy",
        "Unholy",
        "Keen",
        "Returning",
        "Dancing",
        "Defending",
    ],
    "base": [
        "Sword",
        "Blade",
        "Axe",
        "Hammer",
        "Staff",
        "Wand",
        "Bow",
        "Dagger",
        "Mace",
        "Spear",
    ],
    "suffix": [
        "of Power",
        "of the Bear",
        "of the Eagle",
        "of Slaying",
        "of Protection",
        "of Speed",
        "of Wisdom",
        "of Valor",
        "+1",
        "+2",
    ],
}

SURNAME_PATTERNS: List[str] = [
    "Smith",
    "Miller",
    "Cooper",
    "Fletcher",
    "Mason",
    "Thatcher",
    "Carter",
    "Tanner",
    "Weaver",
    "Baker",
    "Brewer",
    "Fisher",
    "Hunter",
]


def generate_character_name(
    race: str, gender: str | None = None, surname: bool = False, seed: int | None = None
) -> str:
    """Generate a character name for a given race.

    Args:
        race: Race type (human, elf, dwarf, orc, halfling)
        gender: Gender (male/female), random if None
        surname: Whether to add a surname
        seed: Random seed

    Returns:
        Generated name
    """
    if seed is not None:
        random.seed(seed)

    # Normalize race
    race = race.lower()
    if race not in ["human", "elf", "dwarf", "orc", "halfling"]:
        race = "human"

    # Handle gender
    if gender is None:
        gender = random.choice(["male", "female"])
    gender = gender.lower()

    # Orcs and halflings don't have gender-specific patterns
    if race in ["orc", "halfling"]:
        pattern_key = race
    else:
        pattern_key = f"{race}_{gender}"

    if pattern_key not in NAME_PATTERNS:
        raise NameGeneratorError(f"Unknown name pattern: {pattern_key}")

    pattern = NAME_PATTERNS[pattern_key]

    # Build first name
    first = random.choice(pattern["first"])
    if "middle" in pattern and random.random() > 0.3:
        first += random.choice(pattern["middle"])
    if "last" in pattern:
        first += random.choice(pattern["last"])

    # Add surname if requested
    if surname:
        last = random.choice(SURNAME_PATTERNS)
        return f"{first} {last}"

    return first


def generate_place_name(compound: bool = True, seed: int | None = None) -> str:
    """Generate a place name.

    Args:
        compound: Whether to use compound names (e.g., Silverdale)
        seed: Random seed

    Returns:
        Generated place name
    """
    if seed is not None:
        random.seed(seed)

    if compound:
        prefix = random.choice(PLACE_PATTERNS["prefix"])
        suffix = random.choice(PLACE_PATTERNS["suffix"])
        return f"{prefix}{suffix}"

    # Simple name
    return random.choice(PLACE_PATTERNS["prefix"]) + random.choice(
        PLACE_PATTERNS["suffix"]
    )


def generate_item_name(
    magical: bool = True, prefix_chance: float = 0.7, seed: int | None = None
) -> str:
    """Generate an item name.

    Args:
        magical: Whether to generate magical item names
        prefix_chance: Probability of adding a prefix (0.0-1.0)
        seed: Random seed

    Returns:
        Generated item name
    """
    if seed is not None:
        random.seed(seed)

    base = random.choice(ITEM_PATTERNS["base"])

    if not magical:
        return base

    # Build magical name
    name_parts = []

    if random.random() < prefix_chance:
        name_parts.append(random.choice(ITEM_PATTERNS["prefix"]))

    name_parts.append(base)

    if random.random() > 0.4:
        name_parts.append(random.choice(ITEM_PATTERNS["suffix"]))

    return " ".join(name_parts)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate fantasy names for characters, places, and items.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  name_generator.py character --race human --gender male
  name_generator.py character --race elf --surname --num 5
  name_generator.py place --num 10
  name_generator.py item --magical --num 3
  name_generator.py character --race dwarf --json
        """,
    )
    subparsers = parser.add_subparsers(dest="type", help="Type of name to generate")

    # Character name parser
    char_parser = subparsers.add_parser("character", help="Generate character names")
    char_parser.add_argument(
        "--race",
        choices=["human", "elf", "dwarf", "orc", "halfling"],
        default="human",
        help="Character race",
    )
    char_parser.add_argument(
        "--gender", choices=["male", "female"], help="Character gender (random if not specified)"
    )
    char_parser.add_argument(
        "--surname", action="store_true", help="Include surname"
    )

    # Place name parser
    place_parser = subparsers.add_parser("place", help="Generate place names")
    place_parser.add_argument(
        "--compound", action="store_true", default=True, help="Use compound names"
    )

    # Item name parser
    item_parser = subparsers.add_parser("item", help="Generate item names")
    item_parser.add_argument(
        "--magical", action="store_true", default=True, help="Generate magical items"
    )
    item_parser.add_argument(
        "--prefix-chance",
        type=float,
        default=0.7,
        help="Chance of prefix (0.0-1.0)",
    )

    # Common arguments
    for subparser in [char_parser, place_parser, item_parser]:
        subparser.add_argument(
            "--num", type=int, default=1, help="Number of names to generate"
        )
        subparser.add_argument(
            "--seed", type=int, help="Random seed for reproducibility"
        )
        subparser.add_argument("--json", action="store_true", help="Output as JSON")
        subparser.add_argument(
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

    if not args.type:
        logger.error("Please specify a name type: character, place, or item")
        return 2

    if args.num < 1:
        logger.error("--num must be at least 1")
        return 2

    try:
        names: List[str] = []

        for i in range(args.num):
            # Use seed for first generation, then None
            current_seed = args.seed if args.seed is not None and i == 0 else None

            if args.type == "character":
                name = generate_character_name(
                    args.race, args.gender, args.surname, seed=current_seed
                )
            elif args.type == "place":
                name = generate_place_name(args.compound, seed=current_seed)
            elif args.type == "item":
                name = generate_item_name(
                    args.magical, args.prefix_chance, seed=current_seed
                )
            else:
                logger.error(f"Unknown name type: {args.type}")
                return 2

            names.append(name)

    except NameGeneratorError as ex:
        logger.error(str(ex))
        return 1
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Unexpected error: {ex}")
        return 1

    if args.json:
        if args.num == 1:
            print(json.dumps({"name": names[0]}, indent=2))
        else:
            print(json.dumps({"names": names}, indent=2))
    else:
        for name in names:
            print(name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
