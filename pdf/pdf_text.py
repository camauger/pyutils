"""PDF text extractor CLI with logging, page selection, and output options.

Tries `pdfplumber` first; falls back to `PyPDF2` if unavailable.
Install with:
  pip install pdfplumber PyPDF2
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple

try:
    import pdfplumber  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    pdfplumber = None  # type: ignore[assignment]

try:
    import PyPDF2  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    PyPDF2 = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class PDFTextError(RuntimeError):
    """Raised when PDF text extraction fails."""


def parse_page_ranges(expr: Optional[str]) -> Optional[List[int]]:
    if not expr:
        return None
    pages: List[int] = []
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a_str, b_str = part.split("-", 1)
            try:
                a, b = int(a_str), int(b_str)
            except ValueError as ex:
                raise PDFTextError(f"Invalid page range: {part}") from ex
            if a <= 0 or b <= 0 or b < a:
                raise PDFTextError(f"Invalid page range: {part}")
            pages.extend(list(range(a, b + 1)))
        else:
            try:
                n = int(part)
                if n <= 0:
                    raise ValueError
            except ValueError as ex:
                raise PDFTextError(f"Invalid page number: {part}") from ex
            pages.append(n)
    # Make unique and sorted
    return sorted(set(pages))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract text from a PDF (pdfplumber → PyPDF2)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Path to input PDF file")
    parser.add_argument(
        "--pages", type=str, help="Pages to extract: e.g., '1,3-5' (1-based)"
    )
    parser.add_argument(
        "--output", type=Path, help="Write full text to file instead of stdout"
    )
    parser.add_argument(
        "--page-sep", type=str, default="\n\n", help="Separator between pages"
    )
    parser.add_argument("--strip", action="store_true", help="Strip each page's text")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def extract_with_pdfplumber(
    path: Path, pages_1based: Optional[List[int]], strip: bool
) -> List[str]:
    if pdfplumber is None:
        raise PDFTextError("pdfplumber not installed")
    try:
        texts: List[str] = []
        with pdfplumber.open(str(path)) as pdf:  # type: ignore[arg-type]
            total = len(pdf.pages)
            selected = pages_1based or list(range(1, total + 1))
            for pno in selected:
                if not (1 <= pno <= total):
                    logger.warning(f"Skipping out-of-range page {pno} (1..{total})")
                    continue
                page = pdf.pages[pno - 1]
                txt = page.extract_text() or ""
                texts.append(txt.strip() if strip else txt)
        return texts
    except Exception as ex:  # noqa: BLE001
        raise PDFTextError(f"pdfplumber failed: {ex}") from ex


def extract_with_pypdf2(
    path: Path, pages_1based: Optional[List[int]], strip: bool
) -> List[str]:
    if PyPDF2 is None:
        raise PDFTextError("PyPDF2 not installed")
    try:
        texts: List[str] = []
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)  # type: ignore[attr-defined]
            total = len(reader.pages)
            selected = pages_1based or list(range(1, total + 1))
            for pno in selected:
                if not (1 <= pno <= total):
                    logger.warning(f"Skipping out-of-range page {pno} (1..{total})")
                    continue
                page = reader.pages[pno - 1]
                txt = page.extract_text() or ""
                texts.append(txt.strip() if strip else txt)
        return texts
    except Exception as ex:  # noqa: BLE001
        raise PDFTextError(f"PyPDF2 failed: {ex}") from ex


def extract_pdf_text(path: Path, pages_expr: Optional[str], strip: bool) -> List[str]:
    pages_1based = parse_page_ranges(pages_expr)
    # Try pdfplumber first
    try:
        return extract_with_pdfplumber(path, pages_1based, strip)
    except PDFTextError as ex:
        logger.debug(str(ex))
    # Fallback to PyPDF2
    return extract_with_pypdf2(path, pages_1based, strip)


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    if not args.input.exists():
        logger.error(f"Input not found: {args.input}")
        return 2

    try:
        pages = extract_pdf_text(args.input, args.pages, args.strip)
    except PDFTextError as ex:
        logger.error(str(ex))
        return 1

    combined = args.page_sep.join(pages)
    if args.output:
        try:
            args.output.write_text(combined, encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to write output: {ex}")
            return 1
        logger.info(f"Wrote text to {args.output}")
    else:
        print(combined)
    return 0


if __name__ == "__main__":
    sys.exit(main())
