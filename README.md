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
- qrcode_generator.py: Create QR codes with error correction, colors, sizing.
- remove_background.py: Remove background using rembg; PNG with alpha.
- rename_files.py: Batch rename with filters, transforms, enumeration, collisions.
- summarizer.py: Summarize arbitrary text via TheTextAPI or Hugging Face.
- web_summarizer.py: Fetch a web page and summarize via HF or TheTextAPI.
- voice_todo.py: Capture speech via microphone and append to a tasks file.
- watermarker.py: Add text/image watermarks with position, opacity, scaling.
- wikifacts.py: Fetch Wikipedia summaries (wikipedia lib with pywhatkit fallback).
- image_deduper.py: Find exact/near-duplicate images via perceptual hashes; report/move/delete options.

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

### Notes
- Some features require optional dependencies (transformers, openai, streamlit, pyaudio/sounddevice).
- On Windows, install build tools for some wheels when needed.
