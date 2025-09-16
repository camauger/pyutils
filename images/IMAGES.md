# Images Utilities

This directory contains command-line utilities for common image workflows: EXIF metadata management, organization, comparison, resizing, contact sheets, watermarking, background removal, deduplication, simple editing, and handwriting rendering.

Each tool supports `--log-level` and prints clear messages. Most tools can be run as modules with `python -m images.<script>` from the repo root, or directly via `python images/<script>.py`.

## exif_manager.py — EXIF metadata manager
- Description: Inspect, export, strip, and edit EXIF metadata.
- Features:
  - List EXIF fields; export JSON/CSV
  - Strip all EXIF or remove GPS only
  - Set `DateTimeOriginal` from file mtime or a specific date
  - Shift date/time by relative offsets (e.g., `+2h,-30m`)
  - Batch over folders with include/exclude globs, recursion, dry-run
- Dependencies: Pillow, piexif
- Examples:
  - List EXIF to JSON recursively:
    ```bash
    python -m images.exif_manager ./photos --list --json --recursive
    ```
  - Strip all EXIF (dry-run first):
    ```bash
    python -m images.exif_manager ./photos --strip --recursive --dry-run
    ```
  - Remove GPS only:
    ```bash
    python -m images.exif_manager ./photos --remove-gps --include "*.jpg" --recursive --yes
    ```
  - Set date from file mtime:
    ```bash
    python -m images.exif_manager ./photos --set-date from-mtime --include "*.jpg" --yes
    ```
  - Shift date by +2h -30m:
    ```bash
    python -m images.exif_manager ./photos --shift-date "+2h,-30m" --include "*.jpg" --yes
    ```

## image_contact_sheet.py — Contact sheet generator
- Description: Build contact sheet pages from a folder of images.
- Features:
  - Grid layout (columns/rows), thumbnail size, spacing, margins
  - Optional filename labels with custom font/size
  - Include/exclude globs, recursive scanning
  - Output PNG/JPEG pages or a single multi-page PDF
- Dependencies: Pillow
- Examples:
  - Basic PNG page(s):
    ```bash
    python -m images.image_contact_sheet ./photos --cols 6 --rows 5 \
      --thumb 320x240 --spacing 8 --bg "#111111" --labels --out out/contact.png
    ```
  - Multipage PDF with recursion and includes:
    ```bash
    python -m images.image_contact_sheet ./photos --recursive --include "*.jpg" \
      --cols 5 --rows 6 --thumb 256x256 --labels --out out/contacts.pdf
    ```

## image_compare.py — Compare images (SSIM/PSNR) and diffs
- Description: Compare two images or two folders; produce metrics and visuals.
- Features:
  - SSIM, PSNR metrics
  - Difference heatmap and side-by-side composite
  - Threshold-based pass/fail; JSON/CSV reports
  - Recursive folder compare by matching filenames
- Dependencies: numpy, Pillow, scikit-image
- Examples:
  - Single pair with diff and JSON report:
    ```bash
    python -m images.image_compare a.jpg b.jpg \
      --diff out_diff.png --composite out_side.png --json out.json
    ```
  - Batch folders with CSV and diff images:
    ```bash
    python -m images.image_compare ./setA ./setB --recursive \
      --csv report.csv --diff-dir diffs/
    ```
  - Enforce SSIM threshold:
    ```bash
    python -m images.image_compare a.jpg b.jpg --ssim-threshold 0.95 --fail-on-below
    ```

## photo_organizer.py — Sort into date folders with rename & dedupe
- Description: Organize photos into date-based folders; rename, copy/move, dedupe.
- Features:
  - Date from EXIF `DateTimeOriginal` (fallback to file mtime)
  - Folder structures: `yyyy/mm`, `yyyy/mm/dd`, custom tokens
  - Rename templates: `{yyyy},{mm},{dd},{HH},{MM},{SS},{orig},{hash}`
  - Copy or move; dry-run; JSON/CSV report
  - Dedupe by SHA256 or by name; conflict resolution with suffixes
- Dependencies: Pillow, piexif (optional for EXIF dates)
- Examples:
  - Dry-run organize into `yyyy/mm`:
    ```bash
    python -m images.photo_organizer ./in ./photos --structure yyyy/mm --dry-run
    ```
  - Use EXIF then mtime; move and rename:
    ```bash
    python -m images.photo_organizer ./in ./photos --use exif,mtime --move \
      --name-template "{yyyy}-{mm}-{dd}_{HH}{MM}{SS}_{orig}"
    ```
  - Dedupe by SHA256 with JSON report:
    ```bash
    python -m images.photo_organizer ./in ./photos --dedupe hash --json report.json
    ```

## image_deduper.py — Find exact and near-duplicate images
- Description: Detect duplicates using perceptual hashes and/or exact hash.
- Features:
  - Algorithms: aHash, dHash, pHash, wHash (via imagehash)
  - Adjustable Hamming distance threshold for near-duplicates
  - Include/exclude globs, recursion, follow symlinks
  - Exact duplicate detection via SHA256
  - Actions: report CSV/JSON, move to quarantine, or delete (with `--yes`)
  - Dry-run for safety
- Dependencies: Pillow, imagehash
- Examples:
  - Report near-duplicates (threshold=8) to CSV:
    ```bash
    python -m images.image_deduper ./photos --algo phash --threshold 8 --report dupes.csv --recursive
    ```
  - Move near-duplicates to quarantine (dry-run first):
    ```bash
    python -m images.image_deduper ./photos --threshold 6 --move-to ./dupes --dry-run
    ```
  - Delete exact duplicates only:
    ```bash
    python -m images.image_deduper ./photos --exact --delete --yes
    ```

## watermarker.py — Add text or image watermarks
- Description: Watermark images with text or overlay image, with positioning.
- Features:
  - Text watermark: font, size, RGBA color, anchors, margins
  - Image watermark: scale, opacity, anchors, margins
  - Anchors: top-left, top-right, bottom-left, bottom-right, center
- Dependencies: Pillow
- Examples:
  - Text watermark:
    ```bash
    python -m images.watermarker text input.jpg output.jpg \
      --text "© 2025 Your Name" --size 32 --color 255,255,255,160 \
      --anchor bottom-right --margin 24,24
    ```
  - Image watermark:
    ```bash
    python -m images.watermarker image input.jpg output.jpg \
      --mark logo.png --opacity 128 --scale 0.5 --anchor top-left --margin 16,16
    ```

## remove_background.py — Background removal via rembg
- Description: Remove background from images using `rembg`.
- Features:
  - Simple CLI to strip background and save PNG
  - Optional alpha enforcement (RGBA)
- Dependencies: rembg, Pillow
- Examples:
  ```bash
  python -m images.remove_background input.jpg output.png --alpha
  ```

## photo_editor.py — Common photo edits
- Description: Small set of editing commands: crop, resize, flip, rotate, blur, text, grayscale, sharpen, merge.
- Features:
  - Subcommands: `crop`, `resize`, `flip`, `rotate`, `blur`, `text`, `grayscale`, `sharpen`, `merge`
  - Safe file I/O with clear errors
- Dependencies: Pillow
- Examples:
  - Crop:
    ```bash
    python -m images.photo_editor crop in.jpg out.jpg 100 100 800 600
    ```
  - Resize (keep aspect):
    ```bash
    python -m images.photo_editor resize in.jpg out.jpg 1920 1080 --keep-aspect
    ```
  - Text overlay:
    ```bash
    python -m images.photo_editor text in.jpg out.jpg "Hello" 50 50 --color 255,0,0 --size 24
    ```

## image_resizer.py — Focused resizer with aspect options
- Description: Resize an image with aspect ratio preservation or fit-within box.
- Features:
  - `--keep-aspect` with one dimension auto-computed
  - `--fit-within` bounding-box scaling
  - Resample filters: nearest, bilinear, bicubic, lanczos
- Dependencies: Pillow
- Examples:
  - Keep aspect using width:
    ```bash
    python -m images.image_resizer in.jpg out.jpg --width 1600 --keep-aspect
    ```
  - Fit within 1600x1200 box:
    ```bash
    python -m images.image_resizer in.jpg out.jpg --width 1600 --height 1200 --fit-within
    ```

## content_aware_resize.py — Content-aware resizer (seam carving)
- Description: Resize images while preserving salient content by removing low-energy seams.
- Features:
  - Target a specific width and/or height (downsizing only)
  - Energy options: auto/sobel (gradient magnitude)
  - Typer-based CLI with logging
- Dependencies: numpy, Pillow, scikit-image (filters, color)
- Examples:
  - Reduce width to 800 with default energy:
    ```bash
    python -m images.content_aware_resize carve input.jpg output.jpg --width 800
    ```
  - Reduce height to 600 with explicit energy:
    ```bash
    python -m images.content_aware_resize carve input.jpg output.jpg --height 600 --energy sobel
    ```
  - Debug logging:
    ```bash
    python -m images.content_aware_resize --log-level DEBUG carve input.jpg output.jpg --width 1200
    ```

## image_heic_converter.py — Convert HEIC/HEIF to JPEG/PNG/WebP
- Description: Batch-convert iPhone/HEIC photos to common formats with optional resize, quality, EXIF preservation, and auto-orientation.
- Features:
  - Formats: input HEIC/HEIF; output JPEG/PNG/WebP
  - Metadata: preserve or strip EXIF; auto-orient from EXIF
  - Quality/size: set JPEG/WebP quality; optional max dimensions
  - Selection: `--recursive`, `--include/--exclude` globs; preserve structure
  - Safety: dry-run, structured logging
- Dependencies: pillow-heif, Pillow
- Examples:
  - Convert all HEIC to JPEG at quality 90, preserving EXIF, auto-orienting:
    ```bash
    python -m images.image_heic_converter ./in ./out --to jpeg --quality 90 --preserve-exif --auto-orient --recursive
    ```
  - Convert to WebP with max size and strip metadata:
    ```bash
    python -m images.image_heic_converter ./in ./out --to webp --max-width 2048 --max-height 2048 --strip-exif --recursive
    ```
  - Only convert *.HEIC while keeping folder structure:
    ```bash
    python -m images.image_heic_converter ./in ./out --to png --include "*.HEIC" --keep-structure --recursive
    ```

## handwriter.py — Render text as handwriting-style image
- Description: Generate handwriting-style PNG from text using `pywhatkit`.
- Features:
  - Input via `--text`, `--file`, or stdin
  - Configurable RGB ink color; output path
- Dependencies: pywhatkit
- Examples:
  - From CLI text:
    ```bash
    python -m images.handwriter --text "Bonjour le monde" --rgb 0,0,255 --output writing.png
    ```
  - From a file:
    ```bash
    python -m images.handwriter --file note.txt --rgb 50,50,50 --output note.png
    ```

---

Tips:
- Use `--include`/`--exclude` and `--recursive` where supported to target specific files.
- Prefer running within a virtual environment. Activate on Windows Git Bash: `source .venv/Scripts/activate`.
