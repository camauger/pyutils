"""Markdown converter CLI using markdown + pdfkit/weasyprint fallbacks.

Install: pip install markdown pdfkit weasyprint
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class MarkdownConversionError(RuntimeError):
    """Raised when markdown conversion or file IO fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert Markdown to HTML or PDF with optional CSS support.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to the Markdown input file. Reads stdin when omitted.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Destination file path for the rendered document.",
    )
    parser.add_argument(
        "--format",
        choices=["html", "pdf"],
        default="html",
        help="Output format for the rendered document.",
    )
    parser.add_argument(
        "--css",
        type=Path,
        help="Optional path to a CSS file to embed in the output.",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity.",
    )
    return parser.parse_args()


def read_markdown(input_path: Optional[Path]) -> str:
    if input_path is not None:
        try:
            logger.debug("Reading Markdown from %s", input_path)
            return input_path.read_text(encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            raise MarkdownConversionError(
                f"Failed to read Markdown file '{input_path}': {ex}"
            ) from ex
    if sys.stdin is not None and not sys.stdin.isatty():
        logger.debug("Reading Markdown from stdin")
        return sys.stdin.read()
    raise MarkdownConversionError("No input provided. Use --input or pipe Markdown via stdin.")


def load_css(css_path: Optional[Path]) -> Optional[str]:
    if css_path is None:
        return None
    try:
        logger.debug("Loading CSS from %s", css_path)
        return css_path.read_text(encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        raise MarkdownConversionError(f"Failed to read CSS file '{css_path}': {ex}") from ex


def render_html(markdown_text: str, css_text: Optional[str]) -> str:
    try:
        import markdown  # type: ignore[import-not-found]
    except Exception as ex:  # noqa: BLE001
        raise MarkdownConversionError(
            "markdown library not installed. Run: pip install markdown"
        ) from ex
    try:
        logger.debug("Rendering Markdown to HTML")
        body = markdown.markdown(markdown_text, extensions=["extra"])
    except Exception as ex:  # noqa: BLE001
        raise MarkdownConversionError(f"Failed to render HTML from Markdown: {ex}") from ex
    css_block = f"<style>\n{css_text}\n</style>\n" if css_text else ""
    html = (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        "<meta charset=\"utf-8\" />\n"
        f"{css_block}"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>\n"
    )
    return html


def write_html(output_path: Path, html: str) -> None:
    try:
        if output_path.parent and not output_path.parent.exists():
            output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.debug("Writing HTML output to %s", output_path)
        output_path.write_text(html, encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        raise MarkdownConversionError(f"Failed to write HTML file '{output_path}': {ex}") from ex


def write_pdf(output_path: Path, html: str) -> None:
    if output_path.parent and not output_path.parent.exists():
        output_path.parent.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []

    try:
        import pdfkit  # type: ignore[import-not-found]
    except Exception as ex:  # noqa: BLE001
        errors.append(f"pdfkit unavailable: {ex}")
    else:
        try:
            logger.debug("Generating PDF via pdfkit")
            pdfkit.from_string(html, str(output_path))
            return
        except Exception as ex:  # noqa: BLE001
            errors.append(f"pdfkit failed: {ex}")

    try:
        from weasyprint import HTML  # type: ignore[import-not-found]
    except Exception as ex:  # noqa: BLE001
        errors.append(f"weasyprint unavailable: {ex}")
    else:
        try:
            logger.debug("Generating PDF via WeasyPrint")
            HTML(string=html).write_pdf(str(output_path))
            return
        except Exception as ex:  # noqa: BLE001
            errors.append(f"weasyprint failed: {ex}")

    detail = "; ".join(errors)
    raise MarkdownConversionError(
        "PDF generation failed. Install pdfkit (requires wkhtmltopdf) or weasyprint. "
        f"Details: {detail}"
    )


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        markdown_text = read_markdown(args.input)
        css_text = load_css(args.css)
    except MarkdownConversionError as ex:
        logger.error(str(ex))
        return 2

    try:
        html = render_html(markdown_text, css_text)
        if args.format == "html":
            write_html(args.output, html)
        else:
            write_pdf(args.output, html)
    except MarkdownConversionError as ex:
        logger.error(str(ex))
        return 1

    logger.info("Wrote %s to %s", args.format.upper(), args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
