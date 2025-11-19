# PyUtils Web Interface

A simple, local web interface to search, browse, and explore all your Python CLI utilities.

## Features

### Core Functionality
- 🔍 **Full-text search** - Search by tool name, description, dependencies, or custom tags
- 📁 **Category filtering** - Browse tools by category (images, pdf, video, etc.)
- 📊 **Tool details** - View descriptions, commands, arguments, and usage examples
- 🔄 **Auto-indexing** - Automatically scans your codebase and extracts tool metadata
- 🎨 **Modern UI** - Clean, responsive design that works on all devices
- ⚡ **Fast & local** - Runs entirely on your machine, no external services needed

### Advanced Features (NEW!)
- 🌓 **Dark mode** - Toggle between light and dark themes (persists across sessions)
- ⭐ **Favorites system** - Mark your frequently used tools as favorites
- 🏷️ **Custom tags** - Add and search by custom tags for better organization
- 📈 **Usage analytics** - Track tool views, executions, and identify most-used tools
- 🕐 **Recently used** - Quick filter to see your recently viewed tools
- ▶️ **Direct execution** - Run tools directly from the browser with custom arguments
- 💾 **Export functionality** - Export your tool list to JSON, CSV, or Markdown

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
- Quick actions (copy command, execute tool, view analytics)

### Using Favorites

- Click the star icon (☆) on any tool card to add it to favorites
- The star will turn gold (⭐) when favorited
- Use the "⭐ Favorites" dropdown filter to see only your favorite tools
- Favorite status is saved in browser localStorage

### Adding Custom Tags

1. Open a tool's detail view
2. Scroll to the "Custom Tags" section
3. Enter a tag name and click "Add Tag"
4. Tags appear as yellow chips on tool cards
5. Search for tools by tag name in the search box
6. Click tag chips in the filter bar for quick filtering

### Viewing Analytics

Click the analytics button (📊) in the header to see:
- Total views and executions across all tools
- Number of favorites and tagged tools
- Most viewed tools (top 5)
- Most executed tools (top 5)
- Individual tool analytics (views, executions, last viewed date)

### Executing Tools

1. Open a tool's detail view
2. Click "Execute Tool" button
3. Enter command-line arguments in the text area (one argument per line or space-separated)
4. Click "Run" to execute
5. View output in the terminal-style panel below
6. Execution counts are tracked in analytics

### Exporting Data

Click the export button (💾) in the header and choose a format:
- **JSON**: Full structured data with all metadata
- **CSV**: Spreadsheet format (Name, Category, Description, Dependencies, Tags)
- **Markdown**: Beautiful formatted documentation

### Dark Mode

- Click the dark mode toggle (🌓) in the header
- Theme preference is saved in browser localStorage
- All colors automatically adjust for optimal readability

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
- `POST /api/execute` - Execute a tool with given arguments (body: {module, args})

### Data Flow

```
Python Files → AST Parser → JSON Index → Flask API → Web Frontend
```

## Keyboard Shortcuts

- `/` - Focus search box
- `Esc` - Close any open modal (tool details, analytics, export)

## Data Persistence

All user preferences and data are stored in browser localStorage:

- **Dark mode preference** - Remembers your theme choice
- **Favorites** - List of starred tools
- **Custom tags** - All tags you've added to tools
- **Analytics** - View counts, execution counts, and timestamps

Data persists across browser sessions but is specific to each browser. To backup or transfer your data:
1. Export your tools list (includes custom tags)
2. Analytics can be cleared from the analytics panel if needed

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

Completed features (v2.0):
- [x] Direct tool execution from web interface
- [x] Tool usage analytics
- [x] Export tool list to various formats (CSV, JSON, Markdown)
- [x] Tag system for custom organization
- [x] Favorite/bookmark tools
- [x] Dark mode toggle

Potential features for future versions:
- [ ] Code syntax highlighting in tool details
- [ ] Tool dependency graph visualization
- [ ] Scheduled tool execution
- [ ] Tool output history
- [ ] Multi-user support with authentication
- [ ] Cloud sync for favorites and tags
- [ ] Tool comparison view
- [ ] Integration with version control (git blame, history)

## License

Part of the pyutils project.
