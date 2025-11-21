"""Tool metadata extraction and indexing for pyutils web interface."""

import ast
import json
import logging
from pathlib import Path
from typing import Optional

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
        self.root_dir = Path(root_dir) if root_dir else Path(__file__).parent.parent
        self.tools: list[dict] = []

    def extract_docstring(self, file_path: Path) -> Optional[str]:
        """Extract module docstring from Python file."""
        try:
            with file_path.open(encoding="utf-8") as f:
                tree = ast.parse(f.read())
                return ast.get_docstring(tree)
        except Exception as e:
            logger.debug(f"Could not extract docstring from {file_path}: {e}")
            return None

    def extract_typer_commands(self, file_path: Path) -> list[dict]:
        """Extract Typer command information from Python file."""
        commands: list[dict] = []
        try:
            with file_path.open(encoding="utf-8") as f:
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
                            cmd_info: dict = {
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
                                args_list = cmd_info["args"]
                                if isinstance(args_list, list):
                                    args_list.append({"name": arg_name, "type": arg_type})

                            commands.append(cmd_info)

        except Exception as e:
            logger.debug(f"Could not parse {file_path}: {e}")

        return commands

    def _generate_smart_descriptions(
        self,
        file_path: Path,
        tool_name: str,
        category: str,
        docstring: Optional[str],
        content: str,
    ) -> tuple[str, str]:
        """Generate smart short and long descriptions from code analysis.

        Returns:
            Tuple of (short_description, long_description)
        """
        short_desc = ""
        long_desc = ""

        # Try to extract from docstring first
        if docstring:
            lines = [line.strip() for line in docstring.split("\n") if line.strip()]

            # First non-empty line is usually the short description
            if lines:
                first_line = lines[0].rstrip(".")
                # Clean up common docstring patterns
                if not first_line.endswith(("CLI", "tool", "utility")):
                    short_desc = first_line
                else:
                    # Try to make it more action-oriented
                    short_desc = first_line

            # First paragraph (up to blank line) is long description
            paragraph_lines = []
            for line in lines[:10]:  # Look at first 10 lines
                if line and not line.startswith(("Features:", "Usage:", "Examples:", "-", "*")):
                    paragraph_lines.append(line)
                elif paragraph_lines:
                    break

            if paragraph_lines:
                long_desc = " ".join(paragraph_lines)

        # Analyze code patterns for better descriptions
        patterns = {
            "convert": "Convert",
            "resize": "Resize",
            "filter": "Filter",
            "merge": "Merge",
            "extract": "Extract",
            "generate": "Generate",
            "analyze": "Analyze",
            "process": "Process",
            "transform": "Transform",
            "compare": "Compare",
            "detect": "Detect",
            "validate": "Validate",
            "optimize": "Optimize",
        }

        # Detect operations from function names
        operations = []
        for pattern, action in patterns.items():
            if pattern in tool_name.lower() or pattern in content.lower()[:500]:
                operations.append(action.lower())

        # Generate fallback based on tool name and category
        if not short_desc:
            # Generate from tool name
            name_parts = tool_name.replace("_", " ").split()

            # Action-oriented templates based on category
            if category == "images":
                if "convert" in tool_name:
                    short_desc = "Convert images between formats"
                elif "resize" in tool_name:
                    short_desc = "Resize and scale images"
                elif "duplicate" in tool_name or "dedup" in tool_name:
                    short_desc = "Find and remove duplicate images"
                else:
                    short_desc = "Process and manipulate images"
            elif category == "files":
                if "duplicate" in tool_name:
                    short_desc = "Find and manage duplicate files"
                elif "rename" in tool_name:
                    short_desc = "Batch rename files with patterns"
                elif "hash" in tool_name:
                    short_desc = "Generate and verify file checksums"
                else:
                    short_desc = "Manage and organize files"
            elif category == "data":
                if "csv" in tool_name:
                    short_desc = "Process and transform CSV files"
                elif "json" in tool_name:
                    short_desc = "Query and manipulate JSON data"
                else:
                    short_desc = "Process and analyze data"
            elif category == "web":
                if "api" in tool_name:
                    short_desc = "Test and interact with REST APIs"
                elif "link" in tool_name:
                    short_desc = "Generate and process web links"
                else:
                    short_desc = "Web scraping and processing"
            elif category == "pdf":
                short_desc = "Extract and process PDF documents"
            elif category == "text_nlp":
                short_desc = "Analyze and process text data"
            else:
                # Generic fallback
                action = operations[0] if operations else "Process"
                short_desc = f"{action.capitalize()} {' '.join(name_parts)}"

        # Enhance long description if missing or too short
        if not long_desc or len(long_desc) < 50:
            # Look for features in docstring
            features = []
            if docstring:
                feature_section = False
                for line in docstring.split("\n"):
                    line = line.strip()
                    if "Features:" in line or "Capabilities:" in line:
                        feature_section = True
                        continue
                    if feature_section and line.startswith(("-", "*", "•")):
                        feature = line.lstrip("-*•").strip()
                        if feature and len(feature) < 100:
                            features.append(feature)
                        if len(features) >= 3:
                            break

            # Build enhanced long description
            if features:
                long_desc = f"{short_desc}. {' '.join(features[:3])}"
            elif not long_desc:
                # Analyze imports for context
                context_parts = []
                if "PIL" in content or "Image" in content:
                    context_parts.append("image processing")
                if "pandas" in content or "DataFrame" in content:
                    context_parts.append("data analysis")
                if "requests" in content:
                    context_parts.append("HTTP requests")
                if "argparse" in content or "typer" in content:
                    context_parts.append("command-line interface")

                if context_parts:
                    long_desc = f"{short_desc}. Includes {', '.join(context_parts)} capabilities."
                else:
                    long_desc = f"{short_desc}. {tool_name.replace('_', ' ').capitalize()} utility for {category} operations."

        # Ensure proper capitalization and punctuation
        if short_desc and not short_desc[0].isupper():
            short_desc = short_desc[0].upper() + short_desc[1:]
        if long_desc and not long_desc[0].isupper():
            long_desc = long_desc[0].upper() + long_desc[1:]

        # Ensure short description is reasonably short (≤100 chars)
        if len(short_desc) > 100:
            short_desc = short_desc[:97] + "..."

        return short_desc, long_desc

    def extract_tool_info(self, file_path: Path, category: str) -> Optional[dict]:
        """Extract comprehensive metadata from a tool file."""
        tool_name = file_path.stem

        # Skip __init__ files
        if tool_name == "__init__":
            return None

        docstring = self.extract_docstring(file_path)
        commands = self.extract_typer_commands(file_path)

        # Read file to extract additional info
        content = ""
        try:
            with file_path.open(encoding="utf-8") as f:
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

        # Generate smart descriptions
        short_desc, long_desc = self._generate_smart_descriptions(
            file_path, tool_name, category, docstring, content
        )

        return {
            "name": tool_name,
            "category": category,
            "file_path": str(file_path.relative_to(self.root_dir)),
            "description": docstring
            or f"{tool_name.replace('_', ' ').title()}",  # Keep for compatibility
            "short_description": short_desc,
            "long_description": long_desc,
            "commands": commands,
            "dependencies": imports,
            "module_path": f"{category}.{tool_name}",
        }

    def index_all_tools(self) -> list[dict]:
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

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(self.tools, f, indent=2)

        logger.info(f"Index saved to: {output_path}")
        return output_path

    def get_categories(self) -> dict[str, int]:
        """Get category counts."""
        categories: dict[str, int] = {}
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
