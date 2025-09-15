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

### Notes
- Some features require optional dependencies (transformers, openai, streamlit, pyaudio/sounddevice).
- On Windows, install build tools for some wheels when needed.
