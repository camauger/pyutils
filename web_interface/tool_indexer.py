"""Tool metadata extraction and indexing for pyutils web interface."""

import ast
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolIndexer:
    """Extract metadata from Python CLI tools."""

    TOOL_CATEGORIES = [
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

    def __init__(self, root_dir: Optional[str] = None):
        """Initialize indexer with project root directory."""
        self.root_dir = Path(root_dir or os.path.dirname(os.path.dirname(__file__)))
        self.tools = []

    def extract_docstring(self, file_path: Path) -> Optional[str]:
        """Extract module docstring from Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
                return ast.get_docstring(tree)
        except Exception as e:
            logger.debug(f"Could not extract docstring from {file_path}: {e}")
            return None

    def extract_typer_commands(self, file_path: Path) -> List[Dict]:
        """Extract Typer command information from Python file."""
        commands = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    # Look for @app.command() decorated functions
                    if isinstance(node, ast.FunctionDef):
                        has_command_decorator = any(
                            isinstance(d, ast.Call)
                            and isinstance(d.func, ast.Attribute)
                            and d.func.attr == "command"
                            for d in node.decorator_list
                        )

                        if has_command_decorator or node.name == "main":
                            cmd_info = {
                                "name": node.name,
                                "docstring": ast.get_docstring(node),
                                "args": [],
                            }

                            # Extract function arguments
                            for arg in node.args.args:
                                arg_name = arg.arg
                                arg_type = None
                                if arg.annotation:
                                    arg_type = ast.unparse(arg.annotation)
                                cmd_info["args"].append(
                                    {"name": arg_name, "type": arg_type}
                                )

                            commands.append(cmd_info)

        except Exception as e:
            logger.debug(f"Could not parse {file_path}: {e}")

        return commands

    def extract_tool_info(self, file_path: Path, category: str) -> Optional[Dict]:
        """Extract comprehensive metadata from a tool file."""
        tool_name = file_path.stem

        # Skip __init__ files
        if tool_name == "__init__":
            return None

        docstring = self.extract_docstring(file_path)
        commands = self.extract_typer_commands(file_path)

        # Read file to extract additional info
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for dependencies
            imports = []
            if "import typer" in content:
                imports.append("typer")
            if "from PIL" in content or "import PIL" in content:
                imports.append("Pillow")
            if "import openai" in content:
                imports.append("openai")
            if "transformers" in content:
                imports.append("transformers")
            if "moviepy" in content:
                imports.append("moviepy")
            if "pdfplumber" in content or "PyPDF2" in content:
                imports.append("PDF libraries")

        except Exception as e:
            logger.debug(f"Could not read {file_path}: {e}")
            imports = []

        return {
            "name": tool_name,
            "category": category,
            "file_path": str(file_path.relative_to(self.root_dir)),
            "description": docstring or f"{tool_name.replace('_', ' ').title()}",
            "commands": commands,
            "dependencies": imports,
            "module_path": f"{category}.{tool_name}",
        }

    def index_all_tools(self) -> List[Dict]:
        """Scan all categories and index tools."""
        self.tools = []

        for category in self.TOOL_CATEGORIES:
            category_dir = self.root_dir / category
            if not category_dir.exists():
                logger.warning(f"Category directory not found: {category_dir}")
                continue

            for py_file in category_dir.glob("*.py"):
                tool_info = self.extract_tool_info(py_file, category)
                if tool_info:
                    self.tools.append(tool_info)
                    logger.info(f"Indexed: {tool_info['name']} ({category})")

        # Also check root directory for standalone tools
        for py_file in self.root_dir.glob("*.py"):
            if py_file.stem not in ["setup", "test", "__init__"]:
                tool_info = self.extract_tool_info(py_file, "misc")
                if tool_info:
                    self.tools.append(tool_info)
                    logger.info(f"Indexed: {tool_info['name']} (misc)")

        logger.info(f"Total tools indexed: {len(self.tools)}")
        return self.tools

    def save_index(self, output_file: str = "tool_index.json"):
        """Save indexed tools to JSON file."""
        output_path = self.root_dir / "web_interface" / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.tools, f, indent=2)

        logger.info(f"Index saved to: {output_path}")
        return output_path

    def get_categories(self) -> Dict[str, int]:
        """Get category counts."""
        categories = {}
        for tool in self.tools:
            cat = tool["category"]
            categories[cat] = categories.get(cat, 0) + 1
        return categories


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    indexer = ToolIndexer()
    indexer.index_all_tools()
    indexer.save_index()

    print(f"\nIndexed {len(indexer.tools)} tools")
    print("\nCategories:")
    for cat, count in sorted(indexer.get_categories().items()):
        print(f"  {cat}: {count} tools")
