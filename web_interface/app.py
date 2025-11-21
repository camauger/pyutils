"""Flask web interface for browsing pyutils tools."""

import json
import logging
import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List

from flask import Flask, jsonify, render_template, request, send_from_directory
from tool_indexer import ToolIndexer

app = Flask(__name__)
logger = logging.getLogger(__name__)

# Configuration
ROOT_DIR = Path(__file__).parent.parent
INDEX_FILE = Path(__file__).parent / "tool_index.json"

# Whitelist of allowed modules for execution
ALLOWED_MODULES = {
    "audio.audio_speaker",
    "audio.voice_todo",
    "data.faker_generator",
    "files.clipboard_history",
    "files.context_manager",
    "files.file_hasher",
    "files.pathfinder",
    "files.rename_files",
    "images.content_aware_resize",
    "images.exif_manager",
    "images.handwriter",
    "images.image_compare",
    "images.image_contact_sheet",
    "images.image_deduper",
    "images.image_heic_converter",
    "images.image_resizer",
    "images.photo_editor",
    "images.photo_organizer",
    "images.remove_background",
    "images.watermarker",
    "office.docx_creator",
    "office.excel_creator",
    "pdf.pdf_summarizer",
    "pdf.pdf_text",
    "pdf.pdf_toolbox",
    "qr.qrcode_generator",
    "text_nlp.blobbing",
    "text_nlp.blobbing_more",
    "text_nlp.collections_helpers",
    "text_nlp.markdown_converter",
    "text_nlp.openai_api",
    "text_nlp.proofreader",
    "text_nlp.summarizer",
    "video.video_toolbox",
    "web.google_search",
    "web.link_preview",
    "web.url_status_checker",
    "web.web_summarizer",
    "web.wikifacts",
}

# Load or create tool index
tools_data = []


def load_tools_index():
    """Load tools index from JSON or create if missing."""
    global tools_data

    if not INDEX_FILE.exists():
        logger.info("Index not found, creating...")
        indexer = ToolIndexer(str(ROOT_DIR))
        indexer.index_all_tools()
        indexer.save_index()

    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        tools_data = json.load(f)

    logger.info(f"Loaded {len(tools_data)} tools")
    return tools_data


@app.route("/")
def index():
    """Main page."""
    return render_template("index.html")


@app.route("/api/tools")
def get_tools():
    """Get all tools or search."""
    category = request.args.get("category", "")
    search = request.args.get("search", "").lower()

    filtered_tools = tools_data

    # Filter by category
    if category and category != "all":
        filtered_tools = [t for t in filtered_tools if t["category"] == category]

    # Search in name, description, and dependencies
    if search:
        filtered_tools = [
            t
            for t in filtered_tools
            if search in t["name"].lower()
            or search in t.get("description", "").lower()
            or any(search in dep.lower() for dep in t.get("dependencies", []))
        ]

    return jsonify(filtered_tools)


@app.route("/api/tool/<category>/<tool_name>")
def get_tool_detail(category, tool_name):
    """Get detailed information about a specific tool."""
    tool = next(
        (t for t in tools_data if t["category"] == category and t["name"] == tool_name),
        None,
    )

    if not tool:
        return jsonify({"error": "Tool not found"}), 404

    # Read the actual source code
    tool_file = ROOT_DIR / tool["file_path"]
    source_code = ""
    if tool_file.exists():
        with open(tool_file, "r", encoding="utf-8") as f:
            source_code = f.read()

    # Try to find examples from README
    examples = extract_examples_for_tool(tool_name)

    return jsonify({**tool, "source_code": source_code, "examples": examples})


def extract_examples_for_tool(tool_name: str) -> List[str]:
    """Extract usage examples for a tool from README."""
    readme_path = ROOT_DIR / "README.md"
    if not readme_path.exists():
        return []

    examples = []
    try:
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Look for code blocks that mention the tool
        in_code_block = False
        current_block = []

        for line in content.split("\n"):
            if line.startswith("```"):
                if in_code_block:
                    block_text = "\n".join(current_block)
                    if tool_name in block_text:
                        examples.append(block_text.strip())
                    current_block = []
                in_code_block = not in_code_block
            elif in_code_block:
                current_block.append(line)

    except Exception as e:
        logger.error(f"Error extracting examples: {e}")

    return examples


@app.route("/api/categories")
def get_categories():
    """Get list of all categories with counts."""
    categories = {}
    for tool in tools_data:
        cat = tool["category"]
        categories[cat] = categories.get(cat, 0) + 1

    return jsonify(categories)


@app.route("/api/stats")
def get_stats():
    """Get overall statistics."""
    stats = {
        "total_tools": len(tools_data),
        "categories": len(set(t["category"] for t in tools_data)),
        "category_breakdown": {},
    }

    for tool in tools_data:
        cat = tool["category"]
        stats["category_breakdown"][cat] = stats["category_breakdown"].get(cat, 0) + 1

    return jsonify(stats)


@app.route("/api/refresh")
def refresh_index():
    """Refresh the tool index."""
    indexer = ToolIndexer(str(ROOT_DIR))
    indexer.index_all_tools()
    indexer.save_index()

    global tools_data
    tools_data = indexer.tools

    return jsonify({"status": "success", "tools_indexed": len(tools_data)})


@app.route("/api/execute", methods=["POST"])
def execute_tool():
    """Execute a tool with given arguments."""
    try:
        data = request.get_json()
        module_path = data.get("module", "")
        args_str = data.get("args", "")

        if not module_path:
            return jsonify({"error": "Module path required", "success": False}), 400

        if module_path not in ALLOWED_MODULES:
            return (
                jsonify({"error": "Invalid or unauthorized module", "success": False}),
                403,
            )

        # Build the command
        cmd = ["python", "-m", module_path]

        # Parse and add arguments safely
        if args_str:
            # Split args by lines or spaces, filter empty strings
            args_lines = [line.strip() for line in args_str.split("\n") if line.strip()]
            for line in args_lines:
                # Use shlex to properly parse arguments
                try:
                    parsed_args = shlex.split(line)
                    cmd.extend(parsed_args)
                except ValueError:
                    # If shlex fails, just split on spaces
                    cmd.extend(line.split())

        logger.info(f"Executing: {' '.join(cmd)}")

        # Execute with timeout
        try:
            result = subprocess.run(
                cmd,
                cwd=ROOT_DIR,
                capture_output=True,
                text=True,
                timeout=30,  # 30 second timeout
            )

            return jsonify(
                {
                    "success": result.returncode == 0,
                    "exit_code": result.returncode,
                    "output": result.stdout,
                    "error": result.stderr,
                }
            )

        except subprocess.TimeoutExpired:
            return jsonify(
                {
                    "success": False,
                    "exit_code": -1,
                    "error": "Command timed out after 30 seconds",
                }
            )

    except Exception as e:
        logger.error(f"Execution error: {e}")
        return jsonify({"success": False, "error": str(e), "exit_code": -1}), 500


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Load tools on startup
    load_tools_index()

    # Run Flask app
    print("\n" + "=" * 60)
    print("🔧 PyUtils Tool Browser")
    print("=" * 60)
    print(f"📊 Loaded {len(tools_data)} tools")
    print(f"🌐 Starting server at http://localhost:5000")
    print("=" * 60 + "\n")

    app.run(debug=True, host="0.0.0.0", port=5000)
