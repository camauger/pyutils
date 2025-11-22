"""Procedural content generator for TTRPG adventures.

Generate quests, locations, encounters, plot hooks, and other
adventure content using templates and random elements.
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class ContentGeneratorError(RuntimeError):
    """Raised when content generation fails."""


# Quest templates
QUEST_GIVERS = [
    "a desperate village elder",
    "a mysterious hooded stranger",
    "a wealthy merchant",
    "the local lord",
    "a temple priest",
    "a dying adventurer",
    "a troubled innkeeper",
    "a royal messenger",
]

QUEST_OBJECTIVES = [
    "retrieve a stolen artifact",
    "rescue kidnapped villagers",
    "clear out a monster-infested dungeon",
    "deliver an urgent message",
    "investigate mysterious disappearances",
    "recover a lost heirloom",
    "escort a caravan through dangerous territory",
    "broker peace between warring factions",
    "find a cure for a deadly plague",
    "stop a ritual before it's completed",
]

QUEST_LOCATIONS = [
    "in ancient ruins to the north",
    "deep within the Darkwood Forest",
    "across the treacherous mountain pass",
    "in the haunted manor on the hill",
    "beneath the city in the old sewers",
    "on a remote island",
    "in the bandit-infested wilderness",
    "at the abandoned temple",
]

QUEST_REWARDS = [
    "100 gold pieces",
    "a magical weapon",
    "valuable information",
    "political favor",
    "a rare spell scroll",
    "land and title",
    "a powerful ally",
    "ancient knowledge",
]

QUEST_COMPLICATIONS = [
    "but time is running out",
    "but there's a traitor among your allies",
    "but the target is better protected than expected",
    "but another group seeks the same goal",
    "but the quest giver is hiding something",
    "but innocent lives are at stake",
    "but the journey is more dangerous than it seems",
    "but completing the quest may have dire consequences",
]

# Tavern/Inn names
TAVERN_ADJECTIVES = [
    "Prancing",
    "Dancing",
    "Golden",
    "Silver",
    "Rusty",
    "Drunken",
    "Sleeping",
    "Laughing",
    "Weeping",
    "Red",
]

TAVERN_NOUNS = [
    "Pony",
    "Dragon",
    "Unicorn",
    "Griffin",
    "Maiden",
    "Goblet",
    "Tankard",
    "Moon",
    "Star",
    "Crown",
]

# Location features
LOCATION_FEATURES = {
    "tavern": [
        "Has a roaring fireplace",
        "Known for its excellent ale",
        "Frequented by adventurers",
        "Has gambling tables in the back",
        "The bartender knows everything",
        "There's a secret room",
    ],
    "dungeon": [
        "Ancient and crumbling",
        "Recently excavated",
        "Built by a long-dead civilization",
        "Still partially occupied",
        "Filled with traps",
        "Contains a powerful artifact",
    ],
    "village": [
        "Peaceful farming community",
        "Plagued by recent troubles",
        "Known for its skilled craftsmen",
        "Isolated and suspicious of strangers",
        "Recently attacked by monsters",
        "Holds an annual festival",
    ],
}

# Monster types
MONSTER_TYPES = [
    "Goblin",
    "Orc",
    "Skeleton",
    "Zombie",
    "Giant Spider",
    "Wolf",
    "Bandit",
    "Cultist",
    "Troll",
    "Ogre",
]

MONSTER_TRAITS = [
    "cunning and tactical",
    "savage and brutal",
    "cowardly when alone",
    "fights to the death",
    "uses ambush tactics",
    "protects its territory fiercely",
    "hunts in packs",
    "surprisingly intelligent",
]

# Plot hooks
PLOT_HOOKS = [
    "A stranger offers you a map to hidden treasure",
    "You overhear guards talking about a secret prisoner",
    "A child tugs on your sleeve, begging for help",
    "You find a mysterious note in your pocket",
    "A prophet warns of coming disaster",
    "You witness a crime and become a target",
    "An old friend appears with urgent news",
    "You discover a conspiracy involving the local nobility",
    "A magical item you carry begins to glow",
    "You're approached by someone who mistakes you for another",
]


def generate_quest(seed: int | None = None) -> Dict[str, Any]:
    """Generate a random quest.

    Args:
        seed: Random seed

    Returns:
        Quest dictionary
    """
    if seed is not None:
        random.seed(seed)

    return {
        "type": "quest",
        "giver": random.choice(QUEST_GIVERS),
        "objective": random.choice(QUEST_OBJECTIVES),
        "location": random.choice(QUEST_LOCATIONS),
        "reward": random.choice(QUEST_REWARDS),
        "complication": random.choice(QUEST_COMPLICATIONS),
    }


def generate_tavern(seed: int | None = None) -> Dict[str, Any]:
    """Generate a tavern/inn.

    Args:
        seed: Random seed

    Returns:
        Tavern dictionary
    """
    if seed is not None:
        random.seed(seed)

    name = f"The {random.choice(TAVERN_ADJECTIVES)} {random.choice(TAVERN_NOUNS)}"
    features = random.sample(LOCATION_FEATURES["tavern"], k=min(3, len(LOCATION_FEATURES["tavern"])))

    return {
        "type": "tavern",
        "name": name,
        "features": features,
        "quality": random.choice(["Poor", "Modest", "Comfortable", "Wealthy", "Aristocratic"]),
        "cost_per_night": random.choice(["5 copper", "5 silver", "1 gold", "2 gold", "5 gold"]),
    }


def generate_dungeon(seed: int | None = None) -> Dict[str, Any]:
    """Generate a dungeon location.

    Args:
        seed: Random seed

    Returns:
        Dungeon dictionary
    """
    if seed is not None:
        random.seed(seed)

    # Import name generator
    from . import name_generator

    # Generate location name
    place_name = name_generator.generate_place_name(compound=True)

    dungeon_types = ["Crypt", "Cave", "Ruins", "Fortress", "Temple", "Sewers"]
    dungeon_type = random.choice(dungeon_types)

    features = random.sample(LOCATION_FEATURES["dungeon"], k=min(3, len(LOCATION_FEATURES["dungeon"])))

    # Generate encounter
    num_rooms = random.randint(5, 15)
    difficulty = random.choice(["Easy", "Medium", "Hard", "Deadly"])

    return {
        "type": "dungeon",
        "name": f"{place_name} {dungeon_type}",
        "dungeon_type": dungeon_type,
        "features": features,
        "estimated_rooms": num_rooms,
        "difficulty": difficulty,
    }


def generate_village(seed: int | None = None) -> Dict[str, Any]:
    """Generate a village.

    Args:
        seed: Random seed

    Returns:
        Village dictionary
    """
    if seed is not None:
        random.seed(seed)

    from . import name_generator

    name = name_generator.generate_place_name(compound=True)
    population = random.randint(50, 500)
    features = random.sample(LOCATION_FEATURES["village"], k=min(3, len(LOCATION_FEATURES["village"])))

    # Key NPCs
    has_elder = random.choice([True, False])
    has_merchant = random.choice([True, False])
    has_temple = random.choice([True, False])

    return {
        "type": "village",
        "name": name,
        "population": population,
        "features": features,
        "notable_locations": {
            "elder": has_elder,
            "merchant": has_merchant,
            "temple": has_temple,
        },
    }


def generate_encounter(cr: int = 1, seed: int | None = None) -> Dict[str, Any]:
    """Generate a monster encounter.

    Args:
        cr: Challenge rating (roughly)
        seed: Random seed

    Returns:
        Encounter dictionary
    """
    if seed is not None:
        random.seed(seed)

    monster = random.choice(MONSTER_TYPES)
    trait = random.choice(MONSTER_TRAITS)

    # Simple number based on CR
    num_monsters = max(1, random.randint(cr, cr + 3))

    tactics = random.choice([
        "Guards the entrance",
        "Patrols the area",
        "Sleeping, can be surprised",
        "Sets an ambush",
        "Fights defensively",
        "Calls for reinforcements",
    ])

    return {
        "type": "encounter",
        "monster": monster,
        "count": num_monsters,
        "trait": trait,
        "tactics": tactics,
        "challenge_rating": cr,
    }


def generate_plot_hook(seed: int | None = None) -> Dict[str, Any]:
    """Generate a plot hook.

    Args:
        seed: Random seed

    Returns:
        Plot hook dictionary
    """
    if seed is not None:
        random.seed(seed)

    return {
        "type": "plot_hook",
        "hook": random.choice(PLOT_HOOKS),
    }


def format_content_markdown(content: Dict[str, Any]) -> str:
    """Format generated content as Markdown.

    Args:
        content: Content dictionary

    Returns:
        Markdown string
    """
    content_type = content["type"]

    if content_type == "quest":
        return f"""## Quest

**Quest Giver:** {content['giver']}
**Objective:** {content['objective'].capitalize()} {content['location']}
**Reward:** {content['reward'].capitalize()}
**Complication:** {content['complication'].capitalize()}

### Description
You are approached by {content['giver']} who asks you to {content['objective']} {content['location']}.
In return, they offer {content['reward']}, {content['complication']}.
"""

    if content_type == "tavern":
        features_str = "\n".join(f"- {f}" for f in content["features"])
        return f"""## {content['name']}

**Type:** Tavern/Inn
**Quality:** {content['quality']}
**Cost per Night:** {content['cost_per_night']}

### Features
{features_str}
"""

    if content_type == "dungeon":
        features_str = "\n".join(f"- {f}" for f in content["features"])
        return f"""## {content['name']}

**Type:** {content['dungeon_type']}
**Estimated Rooms:** {content['estimated_rooms']}
**Difficulty:** {content['difficulty']}

### Features
{features_str}
"""

    if content_type == "village":
        features_str = "\n".join(f"- {f}" for f in content["features"])
        notables = []
        if content["notable_locations"]["elder"]:
            notables.append("Village Elder")
        if content["notable_locations"]["merchant"]:
            notables.append("Merchant")
        if content["notable_locations"]["temple"]:
            notables.append("Temple")

        notables_str = ", ".join(notables) if notables else "None"

        return f"""## {content['name']}

**Type:** Village
**Population:** {content['population']}
**Notable Locations:** {notables_str}

### Features
{features_str}
"""

    if content_type == "encounter":
        plural = "s" if content["count"] > 1 else ""
        return f"""## Encounter (CR {content['challenge_rating']})

**Monsters:** {content['count']} {content['monster']}{plural}
**Trait:** {content['trait'].capitalize()}
**Tactics:** {content['tactics']}
"""

    if content_type == "plot_hook":
        return f"""## Plot Hook

{content['hook']}
"""

    return str(content)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate procedural content for TTRPG adventures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        epilog="""
Examples:
  content_generator.py quest
  content_generator.py tavern --markdown
  content_generator.py dungeon --num 3 --output dungeons.md
  content_generator.py encounter --cr 5
  content_generator.py village --json
  content_generator.py plot-hook --num 5
        """,
    )
    subparsers = parser.add_subparsers(dest="content_type", help="Type of content to generate")

    # Quest generator
    subparsers.add_parser("quest", help="Generate a quest")

    # Tavern generator
    subparsers.add_parser("tavern", help="Generate a tavern/inn")

    # Dungeon generator
    subparsers.add_parser("dungeon", help="Generate a dungeon")

    # Village generator
    subparsers.add_parser("village", help="Generate a village")

    # Encounter generator
    encounter_parser = subparsers.add_parser("encounter", help="Generate an encounter")
    encounter_parser.add_argument(
        "--cr", type=int, default=1, help="Challenge rating (1-10)"
    )

    # Plot hook generator
    subparsers.add_parser("plot-hook", help="Generate a plot hook")

    # Common arguments for all subparsers
    for subparser in subparsers.choices.values():
        subparser.add_argument(
            "--num", type=int, default=1, help="Number of items to generate"
        )
        subparser.add_argument(
            "--seed", type=int, help="Random seed for reproducibility"
        )
        subparser.add_argument(
            "--markdown", action="store_true", help="Output as Markdown"
        )
        subparser.add_argument("--json", action="store_true", help="Output as JSON")
        subparser.add_argument("--output", help="Output file (otherwise print to stdout)")
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

    if not args.content_type:
        logger.error("Please specify a content type")
        return 2

    if args.num < 1:
        logger.error("--num must be at least 1")
        return 2

    try:
        content_items: List[Dict[str, Any]] = []

        for i in range(args.num):
            # Use seed for first item, then None
            current_seed = args.seed if args.seed is not None and i == 0 else None

            if args.content_type == "quest":
                item = generate_quest(seed=current_seed)
            elif args.content_type == "tavern":
                item = generate_tavern(seed=current_seed)
            elif args.content_type == "dungeon":
                item = generate_dungeon(seed=current_seed)
            elif args.content_type == "village":
                item = generate_village(seed=current_seed)
            elif args.content_type == "encounter":
                cr = getattr(args, "cr", 1)
                item = generate_encounter(cr=cr, seed=current_seed)
            elif args.content_type == "plot-hook":
                item = generate_plot_hook(seed=current_seed)
            else:
                logger.error(f"Unknown content type: {args.content_type}")
                return 2

            content_items.append(item)

    except ContentGeneratorError as ex:
        logger.error(str(ex))
        return 1
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Unexpected error: {ex}")
        return 1

    # Format output
    if args.markdown:
        output = "\n---\n\n".join(
            format_content_markdown(item) for item in content_items
        )
    elif args.json:
        if args.num == 1:
            output = json.dumps(content_items[0], indent=2)
        else:
            output = json.dumps(content_items, indent=2)
    else:
        # Simple text format
        output = json.dumps(content_items, indent=2)

    # Write output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            logger.info(f"Content written to {args.output}")
        except IOError as ex:
            logger.error(f"Failed to write file: {ex}")
            return 1
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
