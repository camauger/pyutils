# PyUtils Web Interface

A simple, local web interface to search, browse, and explore all your Python CLI utilities.

## Features

- 🔍 **Full-text search** - Search by tool name, description, or dependencies
- 📁 **Category filtering** - Browse tools by category (images, pdf, video, etc.)
- 📊 **Tool details** - View descriptions, commands, arguments, and usage examples
- 🔄 **Auto-indexing** - Automatically scans your codebase and extracts tool metadata
- 🎨 **Modern UI** - Clean, responsive design that works on all devices
- ⚡ **Fast & local** - Runs entirely on your machine, no external services needed

## Quick Start

### 1. Install Dependencies

```bash
cd web_interface
pip install -r requirements.txt
```

### 2. Run the Server

```bash
python app.py
```

### 3. Open Your Browser

Navigate to: http://localhost:5000

## Usage

### Browsing Tools

- Use the search box to find tools by name, description, or dependency
- Filter by category using the dropdown menu
- Click on any tool card to view detailed information

### Viewing Tool Details

Click on a tool to see:
- Full description
- Available commands and their arguments
- Usage examples from README
- Required dependencies
- File location and module path

### Refreshing the Index

Click the "Refresh Index" button to rescan your codebase and update the tool database. This is useful when you:
- Add new tools
- Modify existing tools
- Update docstrings or dependencies

## Architecture

### Components

1. **tool_indexer.py** - Scans Python files and extracts metadata using AST parsing
2. **app.py** - Flask backend providing REST API endpoints
3. **templates/index.html** - Frontend single-page application

### API Endpoints

- `GET /` - Main web interface
- `GET /api/tools` - List all tools (supports ?search= and ?category= params)
- `GET /api/tool/<category>/<tool_name>` - Get detailed tool information
- `GET /api/categories` - Get all categories with tool counts
- `GET /api/stats` - Get overall statistics
- `GET /api/refresh` - Refresh the tool index

### Data Flow

```
Python Files → AST Parser → JSON Index → Flask API → Web Frontend
```

## Keyboard Shortcuts

- `/` - Focus search box
- `Esc` - Close tool detail modal

## Configuration

The web interface automatically detects the pyutils root directory. To customize:

```python
# In app.py
ROOT_DIR = Path('/custom/path/to/pyutils')
```

## Troubleshooting

### No tools found

1. Check that you're running from the `web_interface` directory
2. Try clicking "Refresh Index" to rebuild the tool database
3. Check the console for error messages

### Import errors

Make sure Flask is installed:
```bash
pip install flask
```

### Port already in use

Change the port in `app.py`:
```python
app.run(debug=True, host='0.0.0.0', port=5001)  # Use different port
```

## Development

### Adding New Features

The codebase is structured to be easily extensible:

- **New metadata fields**: Add extraction logic in `tool_indexer.py`
- **New API endpoints**: Add routes in `app.py`
- **UI enhancements**: Modify `templates/index.html`

### Metadata Extraction

The indexer uses Python's `ast` module to parse source files and extract:
- Module docstrings
- Function definitions and decorators
- Type annotations
- Import statements

## Future Enhancements

Potential features to add:
- [ ] Code syntax highlighting in tool details
- [ ] Direct tool execution from web interface
- [ ] Tool usage analytics
- [ ] Export tool list to various formats (CSV, JSON, Markdown)
- [ ] Tag system for custom organization
- [ ] Favorite/bookmark tools
- [ ] Dark mode toggle

## License

Part of the pyutils project.
