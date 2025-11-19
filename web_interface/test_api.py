"""Simple test script to validate the web interface API."""

import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tool_indexer import ToolIndexer


def test_indexer():
    """Test that the indexer can scan and extract tools."""
    print("Testing tool indexer...")

    indexer = ToolIndexer()
    tools = indexer.index_all_tools()

    assert len(tools) > 0, "No tools found!"
    print(f"✓ Found {len(tools)} tools")

    # Check that tools have required fields
    for tool in tools[:5]:  # Check first 5 tools
        assert 'name' in tool, "Tool missing 'name' field"
        assert 'category' in tool, "Tool missing 'category' field"
        assert 'file_path' in tool, "Tool missing 'file_path' field"
        assert 'module_path' in tool, "Tool missing 'module_path' field"

    print(f"✓ All tools have required fields")

    # Test categories
    categories = indexer.get_categories()
    assert len(categories) > 0, "No categories found!"
    print(f"✓ Found {len(categories)} categories: {', '.join(sorted(categories.keys()))}")

    # Test save
    output_path = indexer.save_index('test_index.json')
    assert output_path.exists(), "Index file was not created!"
    print(f"✓ Index saved successfully")

    # Clean up test file
    output_path.unlink()

    return True


def test_index_file():
    """Test that the main index file is valid JSON."""
    print("\nTesting index file...")

    index_file = Path(__file__).parent / 'tool_index.json'

    if not index_file.exists():
        print("⚠ Index file doesn't exist yet. Run tool_indexer.py first.")
        return True

    with open(index_file, 'r') as f:
        data = json.load(f)

    assert isinstance(data, list), "Index should be a list of tools"
    assert len(data) > 0, "Index is empty"
    print(f"✓ Index file is valid JSON with {len(data)} tools")

    return True


def main():
    """Run all tests."""
    print("="*60)
    print("PyUtils Web Interface - API Tests")
    print("="*60)

    try:
        test_indexer()
        test_index_file()

        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("="*60)

        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1

    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
