"""PDF summarizer CLI (OpenAI or Hugging Face) with extraction and logging."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any, List, Optional

try:
    import pdfplumber  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    pdfplumber = None  # type: ignore[assignment]

try:
    import PyPDF2  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    PyPDF2 = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class PDFSummarizerError(RuntimeError):
    """Raised when summarization or extraction fails."""


def parse_page_ranges(expr: Optional[str]) -> Optional[List[int]]:
    if not expr:
        return None
    pages: List[int] = []
    for part in expr.split(","):
        s = part.strip()
        if not s:
            continue
        if "-" in s:
            a_str, b_str = s.split("-", 1)
            try:
                a, b = int(a_str), int(b_str)
            except ValueError as ex:
                raise PDFSummarizerError(f"Invalid page range: {s}") from ex
            if a <= 0 or b <= 0 or b < a:
                raise PDFSummarizerError(f"Invalid page range: {s}")
            pages.extend(range(a, b + 1))
        else:
            try:
                n = int(s)
            except ValueError as ex:
                raise PDFSummarizerError(f"Invalid page number: {s}") from ex
            if n <= 0:
                raise PDFSummarizerError(f"Invalid page number: {s}")
            pages.append(n)
    return sorted(set(pages))


def extract_with_pdfplumber(
    path: Path, pages_1based: Optional[List[int]], strip: bool
) -> List[str]:
    if pdfplumber is None:
        raise PDFSummarizerError("pdfplumber not installed")
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
        raise PDFSummarizerError(f"pdfplumber failed: {ex}") from ex


def extract_with_pypdf2(
    path: Path, pages_1based: Optional[List[int]], strip: bool
) -> List[str]:
    if PyPDF2 is None:
        raise PDFSummarizerError("PyPDF2 not installed")
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
        raise PDFSummarizerError(f"PyPDF2 failed: {ex}") from ex


def extract_pdf_text(path: Path, pages_expr: Optional[str], strip: bool) -> str:
    pages_1based = parse_page_ranges(pages_expr)
    try:
        parts = extract_with_pdfplumber(path, pages_1based, strip)
    except PDFSummarizerError as ex:
        logger.debug(str(ex))
        parts = extract_with_pypdf2(path, pages_1based, strip)
    return "\n\n".join(parts)


def chunk_text(text: str, max_chars: int) -> List[str]:
    if max_chars <= 0 or len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        para_break = text.rfind("\n\n", start, end)
        if para_break != -1 and para_break > start + int(0.5 * max_chars):
            end = para_break
        chunks.append(text[start:end])
        start = end
    return chunks


def summarize_with_hf(
    text: str, model_name: str, max_length: int, min_length: int
) -> str:
    try:
        from transformers import pipeline  # type: ignore[import-not-found]
    except Exception as ex:  # noqa: BLE001
        raise PDFSummarizerError(
            "transformers not installed. Run: pip install transformers"
        ) from ex
    try:
        summarizer = pipeline("summarization", model=model_name)  # type: ignore[call-arg]
        result = summarizer(
            text, max_length=max_length, min_length=min_length, do_sample=False
        )
        return str(result[0]["summary_text"])  # type: ignore[index]
    except Exception as ex:  # noqa: BLE001
        raise PDFSummarizerError(f"HF summarization failed: {ex}") from ex


def summarize_with_openai(
    text: str, api_key: str, model: str, temperature: float, max_tokens: int
) -> str:
    try:
        from openai import OpenAI  # type: ignore[import-not-found]

        client: Any = OpenAI(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the user's text as a concise, clear summary.",
                },
                {"role": "user", "content": text},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as modern_ex:  # noqa: BLE001
        logger.debug(f"Modern OpenAI client failed: {modern_ex}")

    try:
        import openai as legacy  # type: ignore[import-not-found]

        legacy.api_key = api_key  # type: ignore[attr-defined]
        resp = legacy.ChatCompletion.create(  # type: ignore[attr-defined]
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Summarize the user's text as a concise, clear summary.",
                },
                {"role": "user", "content": text},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp["choices"][0]["message"]["content"] or "").strip()
    except Exception as legacy_ex:  # noqa: BLE001
        raise PDFSummarizerError(
            f"OpenAI summarization failed: {legacy_ex}"
        ) from legacy_ex


def combine_summaries(chunks: List[str], mode: str, **kwargs: Any) -> str:
    if len(chunks) == 1:
        return chunks[0]
    combined = "\n\n".join(chunks)
    if mode == "openai":
        return summarize_with_openai(
            combined,
            api_key=kwargs["api_key"],
            model=kwargs["openai_model"],
            temperature=kwargs["temperature"],
            max_tokens=kwargs["max_tokens"],
        )
    else:
        return summarize_with_hf(
            combined,
            model_name=kwargs["hf_model"],
            max_length=kwargs["hf_max_length"],
            min_length=kwargs["hf_min_length"],
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Summarize a PDF using OpenAI or Hugging Face.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input", type=Path, help="Path to input PDF")
    parser.add_argument("--pages", type=str, help="Pages to include, e.g., '1,3-5'")
    parser.add_argument("--strip", action="store_true", help="Strip text per page")
    parser.add_argument(
        "--output", type=Path, help="Write summary to file instead of stdout"
    )

    parser.add_argument("--mode", choices=["openai", "hf"], default="openai")
    parser.add_argument(
        "--api-key", type=str, help="OpenAI API key (or OPENAI_API_KEY env)"
    )
    parser.add_argument("--openai-model", type=str, default="gpt-4o-mini")
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--hf-model", type=str, default="facebook/bart-large-cnn")
    parser.add_argument("--hf-max-length", type=int, default=180)
    parser.add_argument("--hf-min-length", type=int, default=60)
    parser.add_argument("--max-chars-per-chunk", type=int, default=5000)
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

    if not args.input.exists():
        logger.error(f"Input not found: {args.input}")
        return 2

    try:
        text = extract_pdf_text(args.input, args.pages, args.strip)
    except PDFSummarizerError as ex:
        logger.error(str(ex))
        return 1

    chunks = chunk_text(text, max_chars=args.max_chars_per_chunk)
    summaries: List[str] = []

    try:
        if args.mode == "openai":
            api_key = args.api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise PDFSummarizerError(
                    "Missing API key. Provide --api-key or set OPENAI_API_KEY env var."
                )
            for ch in chunks:
                summaries.append(
                    summarize_with_openai(
                        ch,
                        api_key=api_key,
                        model=args.openai_model,
                        temperature=args.temperature,
                        max_tokens=args.max_tokens,
                    )
                )
            final = combine_summaries(
                summaries,
                mode="openai",
                api_key=api_key,
                openai_model=args.openai_model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
            )
        else:
            for ch in chunks:
                summaries.append(
                    summarize_with_hf(
                        ch,
                        model_name=args.hf_model,
                        max_length=args.hf_max_length,
                        min_length=args.hf_min_length,
                    )
                )
            final = combine_summaries(
                summaries,
                mode="hf",
                hf_model=args.hf_model,
                hf_max_length=args.hf_max_length,
                hf_min_length=args.hf_min_length,
            )
    except PDFSummarizerError as ex:
        logger.error(str(ex))
        return 1

    if args.output:
        try:
            args.output.write_text(final, encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to write summary: {ex}")
            return 1
        logger.info(f"Wrote summary to {args.output}")
    else:
        print(final)
    return 0


if __name__ == "__main__":
    sys.exit(main())
