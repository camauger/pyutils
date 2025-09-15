"""Proofreader CLI using gingerit with optional Streamlit UI.

Install: pip install gingerit streamlit
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from gingerit.gingerit import GingerIt  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    GingerIt = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class ProofreaderError(RuntimeError):
    """Raised when proofreading fails or dependencies are missing."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Proofread text using gingerit.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = parser.add_mutually_exclusive_group()
    src.add_argument("--text", type=str, help="Text to proofread")
    src.add_argument("--file", type=Path, help="Path to a UTF-8 text file")

    parser.add_argument("--json", action="store_true", help="Print JSON result")
    parser.add_argument("--ui", action="store_true", help="Launch Streamlit UI")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def read_input(text: Optional[str], file: Optional[Path]) -> Optional[str]:
    if text is not None:
        return text
    if file is not None:
        try:
            return file.read_text(encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            raise ProofreaderError(f"Failed to read file '{file}': {ex}") from ex
    if sys.stdin is not None and not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def correct_text(text: str) -> Dict[str, Any]:
    if GingerIt is None:
        raise ProofreaderError("gingerit not installed. Run: pip install gingerit")
    try:
        parser = GingerIt()
        result: Dict[str, Any] = parser.parse(text)
        return result
    except Exception as ex:  # noqa: BLE001
        raise ProofreaderError(f"Proofreading failed: {ex}") from ex


def run_ui() -> int:
    try:
        import streamlit as st  # type: ignore[import-not-found]
    except Exception as ex:  # noqa: BLE001
        logger.error("Streamlit is not installed. Run: pip install streamlit")
        return 2

    st.set_page_config(page_title="Proofreader")
    st.title("Proofreading in Python")
    text = st.text_area("Enter your text:")
    if st.button("Correct Sentence"):
        if not text.strip():
            st.warning("Please enter text for proofreading")
        else:
            try:
                result = correct_text(text)
                st.markdown("### Corrected Text")
                st.write(result.get("result", ""))
                st.markdown("### Corrections (raw)")
                st.json(result)
            except ProofreaderError as ex:
                st.error(str(ex))
    return 0


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    if args.ui:
        return run_ui()

    try:
        text = read_input(args.text, args.file)
    except ProofreaderError as ex:
        logger.error(str(ex))
        return 2

    if not text:
        logger.error("No input provided. Use --text, --file, or pipe via stdin.")
        return 2

    try:
        result = correct_text(text)
    except ProofreaderError as ex:
        logger.error(str(ex))
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(result.get("result", ""))

    return 0


if __name__ == "__main__":
    sys.exit(main())
