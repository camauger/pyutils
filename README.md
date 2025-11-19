## pyutils

A collection of small Python CLI utilities. Each script offers a typed command-line interface, logging, and safer error handling.

### Setup

- Python 3.9+
- Create a virtual environment and install dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
source .venv/bin/activate
pip install -r requirements.txt
```

Some tools are optional (transformers, openai, streamlit). Install only what you need.
For Markdown conversion install `markdown` and either `pdfkit` (requires wkhtmltopdf) or `weasyprint`.

Install only what you need. Video helpers also expect an `ffmpeg` binary on your PATH.

### Web Interface

Browse and search all your tools with the built-in web interface:

```bash
cd web_interface
pip install -r requirements.txt
python app.py
# Navigate to http://localhost:5000
```

Features:
- 🔍 Full-text search across all tools
- 📁 Filter by category (images, pdf, video, etc.)
- 📊 View detailed tool information, commands, and usage examples
- 🔄 Auto-indexing of your entire codebase

See `web_interface/README.md` for more details.

### Common options

- Most CLIs support `--log-level`: CRITICAL, ERROR, WARNING, INFO, DEBUG.
- Many support input via flags, files, or stdin.

### Scripts overview

- audio_speaker.py: Text-to-speech from text/file/stdin with logging and fallback.
- blobbing.py: Sentiment analysis via TextBlob; JSON output option.
- blobbing_more.py: Transformers-based sentiment analysis; batch by lines.
- cli_builder.py: Minimal Typer-based example CLI.
- collections_helpers.py: Tokenize and count words; JSON or tabular output.
- context_manager.py: Managed text file writer with append and stdin support.
- docx_creator.py: Read paragraphs/tables, append text, and save DOCX files.
- excel_creator.py: Inspect and modify Excel sheets (get/set cells, append rows/cols).
- faker_generator.py: Generate fake data records (name, email, address, etc.).
- flashtext_test.py: Benchmark regex vs FlashText keyword replacement.
- google_search.py: Open a Google search via pywhatkit or webbrowser fallback.
- handwriter.py: Render text to handwriting-style PNG with color control.
- image_resizer.py: Resize images with aspect options and resampling selection.
- mail_sender.py: Send emails via SMTP with SSL/STARTTLS and env/CLI credentials.
- openai_api.py: Chat/completion via OpenAI (modern client + legacy fallback).
- password_generator.py: Secure passwords with configurable char sets and policies.
- pathfinder.py: Path utilities (info, ls, read, join) with JSON outputs.
- pdf_text.py: Extract text from PDFs (pdfplumber → PyPDF2 fallback).
- pdf_summarizer.py: Extract + summarize PDFs using OpenAI or Hugging Face.
- photo_editor.py: Common image ops (crop, resize, flip, rotate, blur, text, grayscale, sharpen, merge).
- proofreader.py: Grammar/spell correction via gingerit; optional Streamlit UI.
- text_nlp/markdown_converter.py: Convert Markdown to HTML or PDF with optional CSS injection (markdown lib with pdfkit → WeasyPrint fallback).
- qrcode_generator.py: Create QR codes with error correction, colors, sizing.
- remove_background.py: Remove background using rembg; PNG with alpha.
- rename_files.py: Batch rename with filters, transforms, enumeration, collisions.
- summarizer.py: Summarize arbitrary text via TheTextAPI or Hugging Face.
- web_summarizer.py: Fetch a web page and summarize via HF or TheTextAPI.
- voice_todo.py: Capture speech via microphone and append to a tasks file.
- watermarker.py: Add text/image watermarks with position, opacity, scaling.
- wikifacts.py: Fetch Wikipedia summaries (wikipedia lib with pywhatkit fallback).
- image_deduper.py: Find exact/near-duplicate images via perceptual hashes; report/move/delete options.
- exif_manager.py: Inspect/export/strip/edit EXIF (GPS, dates) with batch support.
- photo_organizer.py: Organize photos into date folders using EXIF/mtime with rename, dedupe, and reports.
- image_compare.py: Compute SSIM/PSNR, produce diff heatmaps and composites; batch compare folders.
- image_contact_sheet.py: Generate image contact sheets with grid, labels, pagination. PNG/JPEG/PDF.
- video_toolbox.py: Trim clips, turn segments into GIFs, and extract frames via moviepy or ffmpeg-python.
- content_aware_resize.py: Content-aware image resizing (seam carving) via Sobel energy.
- web/url_status_checker.py: Concurrent URL status checker with table/JSON output.

### Examples

- Rename files (dry run):
```bash
python rename_files.py ./photos --include "*.jpg" --prefix vacation_ --dry-run
```

- Speak text:
```bash
python audio_speaker.py --text "Hello there" --log-level INFO
```

- Sentiment analysis (stdin):
```bash
echo "I love this library" | python blobbing.py --json
```

- Transformers sentiment (batch by lines):
```bash
echo -e "good\nbad" | python blobbing_more.py --split-lines --json
```

- Build simple CLI with Typer:
```bash
python cli_builder.py greet Alice --shout --repeat 2
```

- Word count for a file:
```bash
python collections_helpers.py --file README.md --json
```

- Managed file write:
```bash
echo "Hello" | python context_manager.py ./example.txt --append
```

- DOCX read/append:
```bash
python docx_creator.py --input input.docx --print-paragraphs --append-text "Footer" --output out.docx
```

- Excel inspect/modify:
```bash
python excel_creator.py ./sheet.xlsx --sheet Sheet1 --show
```

- Faker records:
```bash
python faker_generator.py --fields name email --num 3 --json
```

- Regex vs FlashText benchmark:
```bash
python flashtext_test.py --input sample.txt --keywords-json '{"Python":"PY"}'
```

- Google search:
```bash
python google_search.py "what is machine learning"
```

- Handwriting image:
```bash
python handwriter.py --text "Hello" --rgb 0,0,255 --output handwriting.png
```

- Image resize:
```bash
python image_resizer.py input.jpg output.jpg --width 800 --keep-aspect
```

- Content-aware resize (seam carving):
```bash
python -m images.content_aware_resize carve input.jpg output.jpg --width 800
```

- Send mail (SSL):
```bash
MAIL_USERNAME=user MAIL_PASSWORD=pass \
python mail_sender.py --server smtp.example.com --port 465 --ssl \
  --from you@example.com --to them@example.com --subject "Hi" --text "Hello"
```

- OpenAI chat/completion:
```bash
OPENAI_API_KEY=sk-... python openai_api.py --prompt "Summarize this doc" --mode chat
```

- Passwords:
```bash
python password_generator.py --length 20 --avoid-ambiguous --json
```

- QR code:
```bash
python qrcode_generator.py --data https://example.com --output qr.png
```

- Trim a clip segment:
```bash
python -m video.video_toolbox trim input.mp4 output.mp4 --start 00:00:05 --duration 3
```

- Convert part of a clip to a GIF:
```bash
python -m video.video_toolbox to-gif input.mp4 clip.gif --start 2 --end 6 --fps 12
```

- Extract a frame each second:
```bash
python -m video.video_toolbox extract-frames input.mp4 ./frames --fps 1

- Check URL statuses (JSON output):
```bash
python -m web.url_status_checker https://example.com https://httpbin.org/status/404 --json

- Path utilities:
```bash
python pathfinder.py ls . --recursive --glob "*.py" --json
```

- Clipboard monitor:
```bash
python clipboard_history.py --timestamp --duration 30
```

- PDF to text:
```bash
python pdf_text.py input.pdf --pages 1-3 --output out.txt
```

- PDF summarizer (HF):
```bash
python pdf_summarizer.py input.pdf --mode hf --hf-model facebook/bart-large-cnn
```

- Photo edits:
```bash
python photo_editor.py resize input.jpg out.jpg 1200 800 --keep-aspect
```

- Proofreader CLI:
```bash
python proofreader.py --text "This are bad sentence" --json
```

- Markdown to PDF (with optional CSS):
```bash
python text_nlp/markdown_converter.py --input notes.md --output notes.pdf --format pdf --css styles.css
```

- Remove background:
```bash
python remove_background.py input.png output.png --alpha
```

- Summarize text via API/HF:
```bash
python summarizer.py --text "Long text here" --backend api --api-key $TEXTAPI_KEY
```

- Web summarizer:
```bash
python web_summarizer.py https://en.wikipedia.org/wiki/Python_(programming_language) --backend hf
```

- Voice to-do:
```bash
python voice_todo.py --output tasks.txt --language en-US
```

- Watermark:
```bash
python watermarker.py text input.jpg out.jpg --text "Demo" --anchor bottom-right --margin 24,24
```

- Wiki facts:
```bash
python wikifacts.py "Python (programming language)" --lines 2
```

- File hasher (manifest + verify):
```bash
python file_hasher.py ./data --algo sha256 --manifest checksums.txt --recursive --parallel
python file_hasher.py ./data --verify checksums.txt
```

- Image deduper:
```bash
# Report near-duplicates
python image_deduper.py ./photos --algo phash --threshold 8 --report dupes.csv --recursive

# Move duplicates to ./dupes (dry-run first)
python image_deduper.py ./photos --threshold 6 --move-to ./dupes --dry-run

# Delete exact duplicates only
python image_deduper.py ./photos --exact --delete --yes
```

- Photo organizer:
```bash
# Dry-run into yyyy/mm
python -m images.photo_organizer ./in ./photos --structure yyyy/mm --dry-run

# Move and rename using EXIF first, fallback to mtime
python -m images.photo_organizer ./in ./photos --use exif,mtime --move \
  --name-template "{yyyy}-{mm}-{dd}_{HH}{MM}{SS}_{orig}"

# Dedupe by hash and write JSON report
python -m images.photo_organizer ./in ./photos --dedupe hash --json report.json
```

- Image compare:
```bash
# Single pair with diff/composite and JSON
python -m images.image_compare a.jpg b.jpg --diff out_diff.png --composite out_side.png --json out.json

# Batch by filename with CSV and diff images
python -m images.image_compare ./setA ./setB --recursive --csv report.csv --diff-dir diffs/

# Enforce SSIM threshold (exit 1 if below)
python -m images.image_compare a.jpg b.jpg --ssim-threshold 0.95 --fail-on-below
```

- Image contact sheet:
```bash
# Basic PNG output with labels
python -m images.image_contact_sheet ./photos --cols 6 --rows 5 --thumb 320x240 --spacing 8 --bg "#111111" --labels --out out/contact.png

# Recursive selection, include only JPGs, write multi-page PDF
python -m images.image_contact_sheet ./photos --recursive --include "*.jpg" --cols 5 --rows 6 --thumb 256x256 --labels --out out/contacts.pdf
```

- EXIF manager:
```bash
# List EXIF to JSON
python exif_manager.py ./photos --list --json --recursive

# Strip all EXIF (dry run)
python exif_manager.py ./photos --strip --recursive --dry-run

# Remove only GPS
python exif_manager.py ./photos --remove-gps --include "*.jpg" --recursive --yes

# Set DateTimeOriginal from mtime
python exif_manager.py ./photos --set-date from-mtime --include "*.jpg" --yes

# Shift DateTimeOriginal by +2h -30m
python exif_manager.py ./photos --shift-date "+2h,-30m" --include "*.jpg" --yes
```

### Notes
- Some features require optional dependencies (transformers, openai, streamlit, pyaudio/sounddevice).
- On Windows, install build tools for some wheels when needed.
