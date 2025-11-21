"""Tool creator CLI - Generate new pyutils tools with proper structure.

This script helps create new tools following pyutils conventions:
- Proper module structure with docstrings
- Type hints and error handling
- Argparse CLI setup
- Logging configuration
- Automatic addition to pyproject.toml
- Optional test file generation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

CATEGORIES = [
    "audio",
    "bulk",
    "data",
    "files",
    "images",
    "office",
    "pdf",
    "qr",
    "screenshots",
    "text_nlp",
    "video",
    "web",
]


def generate_tool_template(
    tool_name: str,
    category: str,
    short_description: str,
    long_description: str,
    author: str,
) -> str:
    """Generate tool file template."""
    template = f'''"""
{short_description}.

{long_description}

Author: {author}
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="{short_description}",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    # Add your arguments here
    parser.add_argument(
        "input",
        type=Path,
        help="Input file or directory",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="Output file or directory",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them",
    )

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

    try:
        # TODO: Implement your tool logic here
        logger.info("Tool logic not yet implemented")

        if args.dry_run:
            logger.info("Dry-run mode: no changes made")
            return 0

        # Your implementation here
        logger.info(f"Processing: {{args.input}}")

        return 0

    except Exception as e:
        logger.error(f"Error: {{e}}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''
    return template


def generate_test_template(tool_name: str, category: str, module_name: str) -> str:
    """Generate test file template."""
    template = f'''"""Tests for {category}.{module_name} module."""

from __future__ import annotations

from pathlib import Path

import pytest

from {category}.{module_name} import main  # Import your functions here


def test_basic_functionality(tmp_path: Path):
    """Test basic tool functionality."""
    # TODO: Implement your tests
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Add your test assertions
    assert test_file.exists()


def test_with_fixture(sample_text_file: Path):
    """Test using conftest fixture."""
    # TODO: Implement test with fixture
    assert sample_text_file.exists()


def test_error_handling():
    """Test error handling."""
    # TODO: Test error cases
    pass
'''
    return template


def add_to_pyproject(tool_name: str, category: str, module_name: str, pyproject_path: Path) -> bool:
    """Add tool to pyproject.toml console scripts."""
    try:
        content = pyproject_path.read_text()

        # Find the [project.scripts] section
        if "[project.scripts]" not in content:
            print("Warning: [project.scripts] section not found in pyproject.toml")
            return False

        # Generate the entry
        entry_point = f"{category}.{module_name}:main"
        new_line = f'{tool_name} = "{entry_point}"'

        # Find the last script entry
        lines = content.split("\n")
        insert_idx = None
        for i, line in enumerate(lines):
            if line.startswith("[tool.setuptools]"):
                insert_idx = i
                break

        if insert_idx:
            lines.insert(insert_idx, new_line)
            pyproject_path.write_text("\n".join(lines))
            print(f"✓ Added to pyproject.toml: {new_line}")
            return True
        else:
            print("Warning: Could not find insertion point in pyproject.toml")
            print("Manually add this line to [project.scripts]:")
            print(f"  {new_line}")
            return False

    except Exception as e:
        print(f"Error updating pyproject.toml: {e}")
        return False


def create_tool(
    tool_name: str,
    category: str,
    short_description: str,
    long_description: str,
    author: str,
    create_test: bool,
    root_dir: Path,
) -> bool:
    """Create a new tool with proper structure."""
    module_name = tool_name.replace("-", "_")

    # Determine target directory
    if category == "misc":
        tool_file = root_dir / f"{module_name}.py"
    else:
        category_dir = root_dir / category
        category_dir.mkdir(exist_ok=True)
        tool_file = category_dir / f"{module_name}.py"

    # Check if file already exists
    if tool_file.exists():
        print(f"Error: Tool file already exists: {tool_file}")
        return False

    # Generate and write tool file
    template = generate_tool_template(
        tool_name, category, short_description, long_description, author
    )
    tool_file.write_text(template)
    print(f"✓ Created tool file: {tool_file}")

    # Add to pyproject.toml
    pyproject_path = root_dir / "pyproject.toml"
    if pyproject_path.exists():
        add_to_pyproject(tool_name, category, module_name, pyproject_path)
    else:
        print("Warning: pyproject.toml not found")

    # Create test file
    if create_test:
        if category == "misc":
            test_file = root_dir / "tests" / f"test_{module_name}.py"
        else:
            test_dir = root_dir / "tests" / f"test_{category}"
            test_dir.mkdir(parents=True, exist_ok=True)
            test_file = test_dir / f"test_{module_name}.py"

        test_template = generate_test_template(tool_name, category, module_name)
        test_file.write_text(test_template)
        print(f"✓ Created test file: {test_file}")

    # Print next steps
    print("\n" + "=" * 60)
    print("✨ Tool created successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print(f"1. Edit {tool_file} and implement your logic")
    print(f"2. Run the tool: python -m {category}.{module_name} --help")
    if create_test:
        print(f"3. Write tests in {test_file}")
        print(f"4. Run tests: pytest {test_file}")
    print("5. Update web interface: cd web_interface && python tool_indexer.py")
    print("6. Install as command: pip install -e .")
    print(f"7. Run as command: {tool_name} --help")

    return True


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create a new pyutils tool with proper structure",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "tool_name",
        nargs="?",
        help="Tool name (use kebab-case, e.g., 'my-tool')",
    )

    parser.add_argument(
        "--category",
        choices=CATEGORIES + ["misc"],
        help="Tool category",
    )

    parser.add_argument(
        "--short-desc",
        help="Short description (action-oriented, ≤100 chars)",
    )

    parser.add_argument(
        "--long-desc",
        help="Long description (2-3 sentences, optional)",
    )

    parser.add_argument(
        "--author",
        default="Cam Auger",
        help="Author name",
    )

    parser.add_argument(
        "--no-test",
        dest="create_test",
        action="store_false",
        help="Don't create test file",
    )

    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory",
    )

    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Interactive mode: prompt for missing fields",
    )

    return parser.parse_args()


def prompt_choice(prompt: str, choices: list[str], default: str | None = None) -> str:
    """Prompt the user to select from a list of choices."""
    print(prompt)
    for idx, choice in enumerate(choices, start=1):
        print(f"  {idx}. {choice}")

    while True:
        value = input(
            f"Select option [1-{len(choices)}]{f' ({default})' if default else ''}: "
        ).strip()
        if not value and default:
            return default
        if value.isdigit():
            idx = int(value)
            if 1 <= idx <= len(choices):
                return choices[idx - 1]
        elif value in choices:
            return value
        print("Invalid selection, please try again.")


def prompt_text(prompt: str, default: str | None = None, required: bool = True) -> str:
    """Prompt for text input with optional default."""
    while True:
        value = input(f"{prompt}{f' ({default})' if default else ''}: ").strip()
        if not value and default is not None:
            return default
        if value:
            return value
        if not required:
            return ""
        print("Input required, please try again.")


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """Prompt for yes/no input."""
    default_str = "Y/n" if default else "y/N"
    while True:
        value = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please enter y/n.")


def run_interactive(args: argparse.Namespace) -> dict:
    """Collect tool info interactively."""
    print("\n=== Interactive Tool Creator ===\n")

    tool_name = args.tool_name or prompt_text("Tool name (kebab-case)", required=True)
    category = args.category or prompt_choice("Select category:", CATEGORIES + ["misc"])
    short_desc = args.short_desc or prompt_text(
        "Short description (action-oriented, ≤100 chars)", required=True
    )
    long_desc = args.long_desc or prompt_text(
        "Long description (2-3 sentences)", default=short_desc, required=False
    )
    author = prompt_text("Author name", default=args.author, required=True)
    create_test = prompt_yes_no("Create test file?", True)
    root_dir = prompt_text("Project root directory", default=str(args.root), required=True)

    return {
        "tool_name": tool_name,
        "category": category,
        "short_desc": short_desc,
        "long_desc": long_desc or short_desc,
        "author": author,
        "create_test": create_test,
        "root_dir": Path(root_dir).expanduser().resolve(),
    }


def main() -> int:
    """Main entry point."""
    args = parse_arguments()

    if args.interactive:
        inputs = run_interactive(args)
    else:
        missing = []
        if not args.category:
            missing.append("--category")
        if not args.short_desc:
            missing.append("--short-desc")
        if missing:
            print("Error: Missing required arguments:", ", ".join(missing))
            print("Tip: Run with --interactive for guided mode.")
            return 1

        inputs = {
            "tool_name": args.tool_name,
            "category": args.category,
            "short_desc": args.short_desc,
            "long_desc": args.long_desc or args.short_desc,
            "author": args.author,
            "create_test": args.create_test,
            "root_dir": args.root,
        }

    # Validate tool name
    if "_" in inputs["tool_name"]:
        print("Error: Use kebab-case (hyphens) not underscores in tool name")
        print(f"Example: '{inputs['tool_name'].replace('_', '-')}'")
        return 1

    # Validate short description length
    if len(inputs["short_desc"]) > 100:
        print(f"Warning: Short description is {len(inputs['short_desc'])} chars (recommended ≤100)")

    print(f"\nCreating tool: {inputs['tool_name']}")
    print(f"Category: {inputs['category']}")
    print(f"Description: {inputs['short_desc']}")
    print()

    success = create_tool(
        tool_name=inputs["tool_name"],
        category=inputs["category"],
        short_description=inputs["short_desc"],
        long_description=inputs["long_desc"],
        author=inputs["author"],
        create_test=inputs["create_test"],
        root_dir=inputs["root_dir"],
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
