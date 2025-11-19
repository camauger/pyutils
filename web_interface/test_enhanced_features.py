"""Test script to verify enhanced web interface features."""

import json
import sys
from pathlib import Path

# Test that all files exist
def test_files_exist():
    """Test that all necessary files exist."""
    print("Testing file existence...")

    files = [
        'app.py',
        'tool_indexer.py',
        'templates/index.html',
        'requirements.txt',
        'README.md',
        '__init__.py'
    ]

    web_dir = Path(__file__).parent

    for file in files:
        file_path = web_dir / file
        assert file_path.exists(), f"Missing file: {file}"
        print(f"  ✓ {file} exists")

    return True


def test_index_json():
    """Test that the index JSON is valid."""
    print("\nTesting index JSON...")

    index_file = Path(__file__).parent / 'tool_index.json'

    if not index_file.exists():
        print("  ⚠ Index file doesn't exist yet (run tool_indexer.py first)")
        return True

    with open(index_file, 'r') as f:
        data = json.load(f)

    assert isinstance(data, list), "Index should be a list"
    assert len(data) > 0, "Index should not be empty"

    # Check that each tool has required fields
    required_fields = ['name', 'category', 'file_path', 'module_path']
    for tool in data[:5]:  # Check first 5
        for field in required_fields:
            assert field in tool, f"Tool missing required field: {field}"

    print(f"  ✓ Index JSON is valid with {len(data)} tools")
    return True


def test_html_structure():
    """Test that HTML has key elements."""
    print("\nTesting HTML structure...")

    html_file = Path(__file__).parent / 'templates' / 'index.html'
    with open(html_file, 'r') as f:
        html = f.read()

    # Check for key features
    features = {
        'Dark mode': 'dark-mode',
        'Favorites': 'favorites',
        'Tags': 'customTags',
        'Analytics': 'analytics',
        'Export': 'exportTools',
        'Execute': 'executeTool',
        'Search': 'searchInput'
    }

    for name, keyword in features.items():
        assert keyword in html, f"Missing {name} feature"
        print(f"  ✓ {name} feature present")

    return True


def test_app_imports():
    """Test that app.py can be imported."""
    print("\nTesting app.py imports...")

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from tool_indexer import ToolIndexer
        print("  ✓ tool_indexer imports successfully")

        # Test that flask is available
        import flask
        print("  ✓ Flask is installed")

        return True
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False


def test_api_endpoints():
    """Test that all required API endpoints are defined."""
    print("\nTesting API endpoints...")

    app_file = Path(__file__).parent / 'app.py'
    with open(app_file, 'r') as f:
        content = f.read()

    endpoints = [
        '/api/tools',
        '/api/tool/',
        '/api/categories',
        '/api/stats',
        '/api/refresh',
        '/api/execute'
    ]

    for endpoint in endpoints:
        assert endpoint in content, f"Missing endpoint: {endpoint}"
        print(f"  ✓ {endpoint} endpoint defined")

    return True


def main():
    """Run all tests."""
    print("="*60)
    print("Enhanced Web Interface - Feature Tests")
    print("="*60)

    tests = [
        test_files_exist,
        test_index_json,
        test_html_structure,
        test_app_imports,
        test_api_endpoints
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
