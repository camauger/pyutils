"""Benchmark regex vs FlashText keyword replacements with a simple CLI.

Accepts input from a file or stdin, and keywords via JSON mapping or file.
Outputs optional replaced texts and prints timing metrics.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from time import perf_counter
from typing import Any, Dict, Optional, Tuple

try:
    from flashtext import KeywordProcessor  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    KeywordProcessor = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark regex vs FlashText replacements",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", type=Path, help="Path to input text file")
    parser.add_argument(
        "--keywords-json", type=str, help="JSON mapping of replacements"
    )
    parser.add_argument(
        "--keywords-file", type=Path, help="Path to JSON file with mapping"
    )
    parser.add_argument(
        "--case-sensitive", action="store_true", help="Enable case-sensitive matching"
    )
    parser.add_argument("--out-regex", type=Path, help="Write regex output to file")
    parser.add_argument(
        "--out-flashtext", type=Path, help="Write FlashText output to file"
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def read_text(input_path: Optional[Path]) -> Optional[str]:
    if input_path is not None:
        try:
            return input_path.read_text(encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to read input file '{input_path}': {ex}")
            return None
    if sys.stdin is not None and not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def load_keywords(json_str: Optional[str], json_path: Optional[Path]) -> Dict[str, str]:
    data: Dict[str, Any]
    if json_str:
        data = json.loads(json_str)
    elif json_path:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    else:
        # default example keywords
        data = {
            "Python": "PYTHON",
            "Java": "JAVA_REPLACED",
            "JavaScript": "JS_REPLACED",
        }
    # Ensure all values are strings
    return {str(k): str(v) for k, v in dict(data).items()}


def regex_replace(text: str, mapping: Dict[str, str], case_sensitive: bool) -> str:
    flags = 0 if case_sensitive else re.IGNORECASE
    out = text
    for key, value in mapping.items():
        pattern = re.compile(rf"\b{re.escape(key)}\b", flags)
        out = pattern.sub(value, out)
    return out


def flashtext_replace(
    text: str, mapping: Dict[str, str], case_sensitive: bool
) -> Tuple[Optional[str], bool]:
    if KeywordProcessor is None:
        return None, False
    try:
        kp = KeywordProcessor(case_sensitive=case_sensitive)  # type: ignore[operator]
        for key, value in mapping.items():
            kp.add_keyword(key, value)
        return kp.replace_keywords(text), True
    except Exception as ex:  # noqa: BLE001
        logger.debug(f"FlashText failed: {ex}")
        return None, False


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    text = read_text(args.input)
    if text is None:
        logger.error("No input provided. Use --input or pipe via stdin.")
        return 2

    try:
        mapping = load_keywords(args.keywords_json, args.keywords_file)
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Failed to load keywords: {ex}")
        return 2

    t0 = perf_counter()
    regex_out = regex_replace(text, mapping, args.case_sensitive)
    t1 = perf_counter()
    regex_time = t1 - t0

    t2 = perf_counter()
    flash_out, ok = flashtext_replace(text, mapping, args.case_sensitive)
    t3 = perf_counter()
    flash_time = (t3 - t2) if ok else 0.0

    logger.info(f"Regex time: {regex_time:.6f}s")
    if ok and flash_out is not None:
        logger.info(f"FlashText time: {flash_time:.6f}s")
    else:
        logger.warning("FlashText unavailable or failed; only regex result produced.")

    if args.out_regex:
        try:
            args.out_regex.write_text(regex_out, encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to write regex output: {ex}")

    if args.out_flashtext and ok and flash_out is not None:
        try:
            args.out_flashtext.write_text(flash_out, encoding="utf-8")
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to write FlashText output: {ex}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
