# CLAUDE.md - Developer Documentation for AI Assistants

## Project Overview

**pyutils** is a collection of small, focused Python CLI utilities for common tasks. Each tool is designed with a typed command-line interface using Typer, comprehensive logging, and robust error handling.

## Repository Structure

```
pyutils/
├── audio/              # Text-to-speech and voice input tools
├── bulk/               # Bulk file operations
├── common/             # Shared utilities and helpers
├── data/               # Data generation tools (faker)
├── files/              # File management (hashing, clipboard, pathfinding, renaming)
├── images/             # Image processing (editing, resizing, watermarks, EXIF, deduplication)
├── office/             # Office document tools (DOCX, Excel)
├── pdf/                # PDF processing (extraction, summarization)
├── qr/                 # QR code generation
├── screenshots/        # Screenshot text extraction
├── text_nlp/           # NLP tasks (sentiment, summarization, markdown conversion)
├── video/              # Video processing (trimming, GIF creation, frame extraction)
└── web/                # Web scraping and summarization tools
```

## Key Design Patterns

### 1. CLI Interface Pattern
Most tools follow this pattern:
- **Typer** for typed CLI arguments and options
- `--log-level` option (CRITICAL, ERROR, WARNING, INFO, DEBUG)
- Support for input via flags, files, or stdin
- JSON output option for machine-readable results

### 2. Error Handling
- Graceful fallbacks (e.g., pdfplumber → PyPDF2, pdfkit → WeasyPrint)
- Comprehensive logging with configurable levels
- User-friendly error messages

### 3. Module Organization
- Each category has its own directory
- `__init__.py` files for package initialization
- Standalone scripts can be run directly or as modules

## Common Development Tasks

### Adding a New Utility

1. Choose appropriate directory based on functionality
2. Follow the CLI pattern:
   ```python
   import typer
   import logging

   app = typer.Typer()

   @app.command()
   def main(
       input_file: str = typer.Argument(...),
       log_level: str = typer.Option("INFO", help="Logging level")
   ):
       logging.basicConfig(level=getattr(logging, log_level.upper()))
       # Implementation
   ```
3. Add comprehensive help text and type hints
4. Document in README.md
5. Add to requirements.txt if new dependencies needed

### Testing Tools

Most tools support dry-run modes or test inputs:
- File operations: `--dry-run` flag
- Input testing: Use stdin or test files
- Logging: Set `--log-level DEBUG` for verbose output

### Running Tools

Two execution patterns:
```bash
# Direct execution
python tool_name.py [args]

# Module execution (for tools in subdirectories)
python -m category.tool_name [args]
```

## Dependencies

### Core Dependencies
- **typer**: CLI framework
- **Pillow**: Image processing
- **requests**: HTTP requests

### Optional Dependencies by Category

**Images:**
- rembg (background removal)
- piexif (EXIF manipulation)
- imagehash (deduplication)

**NLP/AI:**
- transformers (sentiment analysis)
- openai (API integration)
- textblob (basic NLP)

**Documents:**
- python-docx (Word documents)
- openpyxl (Excel files)
- pdfplumber/PyPDF2 (PDF processing)

**Media:**
- moviepy/ffmpeg-python (video processing)
- pyttsx3/gtts (text-to-speech)
- SpeechRecognition (voice input)

**Web:**
- beautifulsoup4 (web scraping)
- wikipedia (Wikipedia API)

### Installation Strategy
Install only what you need:
```bash
# Core tools
pip install -r requirements.txt

# Specific categories - install as needed
pip install transformers openai  # For NLP features
pip install moviepy              # For video processing
```

## File Conventions

### Input/Output Patterns
- **File paths**: Always absolute or relative to current directory
- **Stdin support**: Most text-processing tools accept `-` or stdin
- **Output formats**: Original format + optional JSON (`--json` flag)

### Naming Conventions
- Scripts: `snake_case.py`
- Functions: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

## Common Code Patterns

### 1. Stdin/File Input Pattern
```python
if input_file == "-":
    text = sys.stdin.read()
else:
    with open(input_file) as f:
        text = f.read()
```

### 2. Dry Run Pattern
```python
if dry_run:
    logger.info(f"Would perform: {operation}")
    return
# Actual operation
```

### 3. Fallback Pattern
```python
try:
    from preferred_lib import preferred_method
    result = preferred_method()
except ImportError:
    logger.warning("Preferred lib not available, using fallback")
    from fallback_lib import fallback_method
    result = fallback_method()
```

### 4. JSON Output Pattern
```python
if json_output:
    print(json.dumps(result, indent=2))
else:
    # Human-readable format
    print(f"Result: {result}")
```

## Environment Variables

Common environment variables used:
- `OPENAI_API_KEY`: OpenAI API integration
- `MAIL_USERNAME`, `MAIL_PASSWORD`: Email sending
- `TEXTAPI_KEY`: Text summarization API

## Integration Points

### Image Processing Pipeline
1. **Input**: photo_organizer.py (organize by date)
2. **Processing**: image_resizer.py, photo_editor.py, watermarker.py
3. **Quality Control**: image_compare.py
4. **Deduplication**: image_deduper.py
5. **Output**: image_contact_sheet.py (create contact sheets)

### Document Workflow
1. **PDF**: pdf_text.py → pdf_summarizer.py
2. **Markdown**: markdown_converter.py (MD → HTML/PDF)
3. **Office**: docx_creator.py, excel_creator.py

### Media Processing
1. **Video**: video_toolbox.py (trim, extract frames, create GIFs)
2. **Audio**: audio_speaker.py (TTS), voice_todo.py (STT)

## Troubleshooting

### Common Issues

**Import Errors:**
- Check requirements.txt for missing dependencies
- Some tools require optional packages
- System dependencies: ffmpeg (video), wkhtmltopdf (PDF conversion)

**Permission Errors:**
- File operations: Check read/write permissions
- Use `--dry-run` to preview changes

**Media Processing:**
- Video/Audio: Ensure ffmpeg is in PATH
- Images: Large images may require more memory

### Debug Mode
Enable verbose logging for all tools:
```bash
python tool_name.py [args] --log-level DEBUG
```

## Best Practices for AI Assistants

1. **Check Dependencies**: Before suggesting code changes, verify required packages in requirements.txt
2. **Maintain Patterns**: Follow existing CLI and error handling patterns
3. **Test Changes**: Suggest using dry-run modes or test inputs
4. **Document Updates**: Update README.md when adding features
5. **Consider Fallbacks**: Implement graceful degradation when possible
6. **Use Type Hints**: All new code should include proper type annotations
7. **Log Appropriately**: Use logging instead of print() for non-output messages

## Quick Reference

### Most Used Tools
- **File Operations**: rename_files.py, file_hasher.py
- **Images**: image_resizer.py, photo_editor.py, watermarker.py
- **Documents**: pdf_text.py, markdown_converter.py
- **Utilities**: password_generator.py, qrcode_generator.py

### Command Templates

**Image batch processing:**
```bash
python -m images.photo_organizer ./input ./output --structure yyyy/mm --move
python -m images.image_resizer batch ./input ./output --width 1920 --keep-aspect
```

**Document conversion:**
```bash
python text_nlp/markdown_converter.py --input doc.md --output doc.pdf --format pdf
python pdf_text.py input.pdf --output output.txt
```

**File management:**
```bash
python files/rename_files.py ./dir --prefix "photo_" --enumerate --dry-run
python files/file_hasher.py ./dir --manifest checksums.txt --recursive
```

## Version Information

- **Python**: 3.9+
- **Primary Framework**: Typer for CLI
- **Primary Image Library**: Pillow (PIL)
- **Primary Video Library**: moviepy (with ffmpeg backend)

## Contributing Guidelines

When adding or modifying tools:
1. Maintain backward compatibility when possible
2. Add comprehensive help text
3. Support both CLI arguments and stdin where appropriate
4. Include JSON output option for automation
5. Use logging for diagnostic messages
6. Add examples to README.md
7. Consider Windows compatibility (path handling, line endings)

## External Tool Dependencies

Some utilities require system binaries:
- **ffmpeg**: Video processing (video_toolbox.py)
- **wkhtmltopdf**: PDF generation from HTML (optional for markdown_converter.py)

Check installation:
```bash
ffmpeg -version
wkhtmltopdf --version
```
