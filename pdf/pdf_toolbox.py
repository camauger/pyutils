"""PDF toolbox CLI (merge, split, extract, rotate, encrypt, decrypt) using PyPDF2.

Examples:
- Merge:
  python pdf_toolbox.py merge out.pdf in1.pdf in2.pdf

- Split into ranges (1-based; open-ended allowed):
  python pdf_toolbox.py split input.pdf --ranges 1-3,7,10- --out-dir parts/

- Extract pages to a single file:
  python pdf_toolbox.py extract input.pdf --ranges 5-8 -o excerpt.pdf

- Rotate pages 1,2 by 90 degrees to new file:
  python pdf_toolbox.py rotate input.pdf --pages 1,2 --angle 90 -o rotated.pdf

- Encrypt with user password:
  python pdf_toolbox.py encrypt input.pdf --password secret -o secured.pdf

- Decrypt with password:
  python pdf_toolbox.py decrypt secured.pdf --password secret -o plain.pdf
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PyPDF2 import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


def parse_ranges(expr: str, max_pages: Optional[int] = None) -> List[Tuple[int, int]]:
    # returns 0-based inclusive ranges as (start, end)
    ranges: List[Tuple[int, int]] = []
    if not expr:
        return ranges
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            start = int(a) if a else 1
            end = int(b) if b else (max_pages or 10**9)
        else:
            start = int(part)
            end = start
        if start <= 0 or end <= 0 or end < start:
            raise ValueError(f"Invalid range: {part}")
        ranges.append((start - 1, end - 1))
    return ranges


def parse_pages(expr: str) -> List[int]:
    pages: List[int] = []
    for tok in expr.split(","):
        tok = tok.strip()
        if tok:
            n = int(tok)
            if n <= 0:
                raise ValueError("Page numbers must be >= 1")
            pages.append(n - 1)
    return pages


def cmd_merge(out: Path, inputs: List[Path]) -> None:
    writer = PdfWriter()
    for p in inputs:
        reader = PdfReader(str(p))
        for page in reader.pages:
            writer.add_page(page)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        writer.write(f)


def cmd_split(src: Path, ranges_expr: str, out_dir: Path) -> None:
    reader = PdfReader(str(src))
    ranges = parse_ranges(ranges_expr, max_pages=len(reader.pages))
    if not ranges:
        raise ValueError("No ranges provided")
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, (start, end) in enumerate(ranges, 1):
        writer = PdfWriter()
        for i in range(start, min(end, len(reader.pages) - 1) + 1):
            writer.add_page(reader.pages[i])
        target = out_dir / f"{src.stem}_part{idx}.pdf"
        with target.open("wb") as f:
            writer.write(f)
        logger.info(f"Wrote {target}")


def cmd_extract(src: Path, ranges_expr: str, out_file: Path) -> None:
    reader = PdfReader(str(src))
    ranges = parse_ranges(ranges_expr, max_pages=len(reader.pages))
    if not ranges:
        raise ValueError("No ranges provided")
    writer = PdfWriter()
    for start, end in ranges:
        for i in range(start, min(end, len(reader.pages) - 1) + 1):
            writer.add_page(reader.pages[i])
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("wb") as f:
        writer.write(f)


def cmd_rotate(src: Path, pages_expr: str, angle: int, out_file: Path) -> None:
    if angle % 90 != 0:
        raise ValueError("Angle must be a multiple of 90")
    reader = PdfReader(str(src))
    writer = PdfWriter()
    rotate_set = set(parse_pages(pages_expr))
    for idx, page in enumerate(reader.pages):
        pg = page
        if idx in rotate_set:
            pg = page.rotate(angle)  # PyPDF2 handles positive rotation clockwise
        writer.add_page(pg)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("wb") as f:
        writer.write(f)


def cmd_encrypt(src: Path, password: str, out_file: Path) -> None:
    reader = PdfReader(str(src))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(password)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("wb") as f:
        writer.write(f)


def cmd_decrypt(src: Path, password: str, out_file: Path) -> None:
    reader = PdfReader(str(src))
    if reader.is_encrypted:
        ok = reader.decrypt(password)
        if ok == 0:
            raise ValueError("Incorrect password")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("wb") as f:
        writer.write(f)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PDF toolbox (merge, split, extract, rotate, encrypt, decrypt)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_merge = sub.add_parser("merge", help="Merge PDFs into one")
    p_merge.add_argument("output", type=Path)
    p_merge.add_argument("inputs", nargs="+", type=Path)

    p_split = sub.add_parser("split", help="Split PDF into parts by ranges")
    p_split.add_argument("input", type=Path)
    p_split.add_argument("--ranges", required=True, type=str, help="e.g., 1-3,7,10-")
    p_split.add_argument("--out-dir", required=True, type=Path)

    p_extract = sub.add_parser("extract", help="Extract pages into a single PDF")
    p_extract.add_argument("input", type=Path)
    p_extract.add_argument("--ranges", required=True, type=str)
    p_extract.add_argument("-o", "--output", required=True, type=Path)

    p_rotate = sub.add_parser("rotate", help="Rotate selected pages by angle")
    p_rotate.add_argument("input", type=Path)
    p_rotate.add_argument("--pages", required=True, type=str, help="e.g., 1,2,5")
    p_rotate.add_argument("--angle", required=True, type=int)
    p_rotate.add_argument("-o", "--output", required=True, type=Path)

    p_encrypt = sub.add_parser("encrypt", help="Encrypt PDF with password")
    p_encrypt.add_argument("input", type=Path)
    p_encrypt.add_argument("--password", required=True, type=str)
    p_encrypt.add_argument("-o", "--output", required=True, type=Path)

    p_decrypt = sub.add_parser("decrypt", help="Decrypt PDF with password")
    p_decrypt.add_argument("input", type=Path)
    p_decrypt.add_argument("--password", required=True, type=str)
    p_decrypt.add_argument("-o", "--output", required=True, type=Path)

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        if args.command == "merge":
            cmd_merge(args.output, args.inputs)
        elif args.command == "split":
            cmd_split(args.input, args.ranges, args.out_dir)
        elif args.command == "extract":
            cmd_extract(args.input, args.ranges, args.output)
        elif args.command == "rotate":
            cmd_rotate(args.input, args.pages, args.angle, args.output)
        elif args.command == "encrypt":
            cmd_encrypt(args.input, args.password, args.output)
        elif args.command == "decrypt":
            cmd_decrypt(args.input, args.password, args.output)
        else:
            logger.error("Unknown command")
            return 2
    except Exception as ex:  # noqa: BLE001
        logger.error(str(ex))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
