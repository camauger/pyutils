"""NPC (Non-Player Character) generator with stat blocks.

Generate complete NPCs with stats, personality, equipment, and background.
Supports D&D 5e-style stat blocks with Markdown and JSON output.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class NPCGeneratorError(RuntimeError):
    """Raised when NPC generation fails."""


# D&D 5e classes
CLASSES = [
    "Barbarian",
    "Bard",
    "Cleric",
    "Druid",
    "Fighter",
    "Monk",
    "Paladin",
    "Ranger",
    "Rogue",
    "Sorcerer",
    "Warlock",
    "Wizard",
]

# Common backgrounds
BACKGROUNDS = [
    "Acolyte",
    "Criminal",
    "Folk Hero",
    "Noble",
    "Sage",
    "Soldier",
    "Merchant",
    "Sailor",
    "Entertainer",
    "Outlander",
]

# Personality traits
PERSONALITY_TRAITS = [
    "I am always polite and respectful",
    "I am haunted by memories of war",
    "I judge others by their actions, not their words",
    "I have a joke for every occasion",
    "I am easily distracted by the promise of information",
    "I am suspicious of strangers",
    "I have a strong sense of fair play",
    "I am slow to trust others",
]

IDEALS = [
    "Respect - People deserve to be treated with dignity",
    "Freedom - Everyone should be free to pursue their own destiny",
    "Charity - I always help those in need",
    "Power - I seek to become powerful",
    "Honor - I don't steal from others",
    "Knowledge - The path to power is through knowledge",
]

BONDS = [
    "My family is the most important thing in my life",
    "I owe my life to my mentor",
    "I seek revenge on those who wronged me",
    "I protect those who cannot protect themselves",
    "I am searching for someone important to me",
    "My honor is my life",
]

FLAWS = [
    "I can't resist a pretty face",
    "I am too greedy for my own good",
    "I have a weakness for vice",
    "I turn tail and run when things look bad",
    "I am convinced that no one could be as smart as me",
    "I have a secret that could ruin me",
]

# Simple equipment by class
EQUIPMENT = {
    "Barbarian": ["Greataxe", "Handaxe", "Hide Armor", "Explorer's Pack"],
    "Bard": ["Rapier", "Lute", "Leather Armor", "Diplomat's Pack"],
    "Cleric": ["Mace", "Chain Mail", "Shield", "Holy Symbol", "Priest's Pack"],
    "Druid": ["Quarterstaff", "Leather Armor", "Druidic Focus", "Explorer's Pack"],
    "Fighter": ["Longsword", "Shield", "Chain Mail", "Dungeoner's Pack"],
    "Monk": ["Quarterstaff", "Darts (10)", "Explorer's Pack"],
    "Paladin": ["Longsword", "Shield", "Chain Mail", "Holy Symbol", "Priest's Pack"],
    "Ranger": ["Longbow", "Quiver (20 arrows)", "Leather Armor", "Explorer's Pack"],
    "Rogue": ["Shortsword", "Shortbow", "Leather Armor", "Burglar's Pack", "Thieves' Tools"],
    "Sorcerer": ["Dagger", "Component Pouch", "Explorer's Pack"],
    "Warlock": ["Dagger", "Leather Armor", "Component Pouch", "Scholar's Pack"],
    "Wizard": ["Quarterstaff", "Component Pouch", "Scholar's Pack", "Spellbook"],
}


def roll_ability_score(method: str = "standard", seed: int | None = None) -> int:
    """Roll an ability score.

    Args:
        method: Method to use (standard=4d6 drop lowest, array=use standard array)
        seed: Random seed

    Returns:
        Ability score (3-18)
    """
    if seed is not None:
        random.seed(seed)

    if method == "standard":
        # 4d6 drop lowest
        rolls = sorted([random.randint(1, 6) for _ in range(4)])
        return sum(rolls[1:])  # Drop the lowest

    # This shouldn't be called for array method
    return 10


def get_ability_modifier(score: int) -> int:
    """Calculate ability modifier from score.

    Args:
        score: Ability score

    Returns:
        Modifier
    """
    return (score - 10) // 2


def generate_ability_scores(method: str = "standard") -> Dict[str, int]:
    """Generate full set of ability scores.

    Args:
        method: Generation method (standard, array)

    Returns:
        Dict of ability scores
    """
    abilities = ["STR", "DEX", "CON", "INT", "WIS", "CHA"]

    if method == "array":
        # Standard array: 15, 14, 13, 12, 10, 8
        scores = [15, 14, 13, 12, 10, 8]
        random.shuffle(scores)
        return dict(zip(abilities, scores))

    # Standard method: 4d6 drop lowest for each
    return {ability: roll_ability_score(method) for ability in abilities}


def generate_npc(
    race: str | None = None,
    char_class: str | None = None,
    level: int = 1,
    method: str = "standard",
    seed: int | None = None,
) -> Dict[str, Any]:
    """Generate a complete NPC.

    Args:
        race: Race (human, elf, etc.) - random if None
        char_class: Class - random if None
        level: Character level
        method: Ability score method (standard, array)
        seed: Random seed

    Returns:
        NPC dictionary
    """
    if seed is not None:
        random.seed(seed)

    # Import name generator for race-appropriate names
    from . import name_generator

    # Determine race
    races = ["human", "elf", "dwarf", "halfling", "orc"]
    if race is None:
        race = random.choice(races)
    race = race.lower()

    # Generate name
    gender = random.choice(["male", "female"])
    name = name_generator.generate_character_name(race, gender, surname=True)

    # Determine class
    if char_class is None:
        char_class = random.choice(CLASSES)

    # Generate ability scores
    abilities = generate_ability_scores(method)

    # Calculate proficiency bonus
    proficiency = 2 + ((level - 1) // 4)

    # Hit points (use class hit die + CON modifier)
    hit_dice = {
        "Barbarian": 12,
        "Fighter": 10,
        "Paladin": 10,
        "Ranger": 10,
        "Bard": 8,
        "Cleric": 8,
        "Druid": 8,
        "Monk": 8,
        "Rogue": 8,
        "Warlock": 8,
        "Sorcerer": 6,
        "Wizard": 6,
    }
    hd = hit_dice.get(char_class, 8)
    con_mod = get_ability_modifier(abilities["CON"])
    hp = hd + con_mod + (level - 1) * (hd // 2 + 1 + con_mod)
    hp = max(1, hp)  # Minimum 1 HP

    # Armor class (simplified)
    dex_mod = get_ability_modifier(abilities["DEX"])
    ac = 10 + dex_mod  # Base, can be improved with armor

    # Generate personality
    personality = {
        "trait": random.choice(PERSONALITY_TRAITS),
        "ideal": random.choice(IDEALS),
        "bond": random.choice(BONDS),
        "flaw": random.choice(FLAWS),
    }

    # Select background
    background = random.choice(BACKGROUNDS)

    # Get equipment
    equipment = EQUIPMENT.get(char_class, ["Basic equipment"])

    return {
        "name": name,
        "race": race.capitalize(),
        "class": char_class,
        "level": level,
        "background": background,
        "alignment": "Neutral",  # Could be randomized
        "ability_scores": abilities,
        "ability_modifiers": {
            ability: get_ability_modifier(score)
            for ability, score in abilities.items()
        },
        "proficiency_bonus": proficiency,
        "armor_class": ac,
        "hit_points": hp,
        "hit_dice": f"{level}d{hd}",
        "personality": personality,
        "equipment": equipment,
    }


def format_npc_markdown(npc: Dict[str, Any]) -> str:
    """Format NPC as Markdown stat block.

    Args:
        npc: NPC dictionary

    Returns:
        Markdown string
    """
    lines = [
        f"# {npc['name']}",
        f"",
        f"*{npc['race']} {npc['class']} {npc['level']}, {npc['alignment']}*",
        f"",
        f"**Armor Class:** {npc['armor_class']}  ",
        f"**Hit Points:** {npc['hit_points']} ({npc['hit_dice']})  ",
        f"**Proficiency Bonus:** +{npc['proficiency_bonus']}",
        f"",
        f"---",
        f"",
        f"### Ability Scores",
        f"",
    ]

    # Ability scores table
    abilities = npc["ability_scores"]
    modifiers = npc["ability_modifiers"]

    for ability in ["STR", "DEX", "CON", "INT", "WIS", "CHA"]:
        score = abilities[ability]
        mod = modifiers[ability]
        mod_str = f"+{mod}" if mod >= 0 else str(mod)
        lines.append(f"**{ability}:** {score} ({mod_str})  ")

    lines.extend(
        [
            f"",
            f"---",
            f"",
            f"### Personality",
            f"",
            f"**Background:** {npc['background']}  ",
            f"**Trait:** {npc['personality']['trait']}  ",
            f"**Ideal:** {npc['personality']['ideal']}  ",
            f"**Bond:** {npc['personality']['bond']}  ",
            f"**Flaw:** {npc['personality']['flaw']}",
            f"",
            f"---",
            f"",
            f"### Equipment",
            f"",
        ]
    )

    for item in npc["equipment"]:
        lines.append(f"- {item}")

    return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate NPC stat blocks for D&D 5e-style games.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  npc_generator.py --class Fighter --level 5
  npc_generator.py --race elf --class Wizard --markdown
  npc_generator.py --num 3 --json
  npc_generator.py --method array --level 10 --output fighter.md
        """,
    )
    parser.add_argument(
        "--race",
        choices=["human", "elf", "dwarf", "halfling", "orc"],
        help="NPC race (random if not specified)",
    )
    parser.add_argument(
        "--class",
        dest="char_class",
        choices=CLASSES,
        help="NPC class (random if not specified)",
    )
    parser.add_argument("--level", type=int, default=1, help="Character level")
    parser.add_argument(
        "--method",
        choices=["standard", "array"],
        default="standard",
        help="Ability score generation method",
    )
    parser.add_argument(
        "--num", type=int, default=1, help="Number of NPCs to generate"
    )
    parser.add_argument(
        "--markdown", action="store_true", help="Output as Markdown stat block"
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", help="Output file (otherwise print to stdout)")
    parser.add_argument("--seed", type=int, help="Random seed for reproducibility")
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

    if args.level < 1 or args.level > 20:
        logger.error("Level must be between 1 and 20")
        return 2

    if args.num < 1:
        logger.error("--num must be at least 1")
        return 2

    try:
        npcs: List[Dict[str, Any]] = []

        for i in range(args.num):
            # Use seed for first NPC, then None
            current_seed = args.seed if args.seed is not None and i == 0 else None

            npc = generate_npc(
                race=args.race,
                char_class=args.char_class,
                level=args.level,
                method=args.method,
                seed=current_seed,
            )
            npcs.append(npc)

    except NPCGeneratorError as ex:
        logger.error(str(ex))
        return 1
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Unexpected error: {ex}")
        return 1

    # Format output
    if args.markdown:
        output = "\n\n---\n\n".join(format_npc_markdown(npc) for npc in npcs)
    elif args.json:
        if args.num == 1:
            output = json.dumps(npcs[0], indent=2)
        else:
            output = json.dumps(npcs, indent=2)
    else:
        # Simple text format
        lines = []
        for npc in npcs:
            lines.append(
                f"{npc['name']} - {npc['race']} {npc['class']} {npc['level']}"
            )
        output = "\n".join(lines)

    # Write output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            logger.info(f"NPC(s) written to {args.output}")
        except IOError as ex:
            logger.error(f"Failed to write file: {ex}")
            return 1
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
