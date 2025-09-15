"""Sentiment analysis with Hugging Face Transformers pipeline.

CLI supports analyzing a single text, reading from a file, or stdin, with
optional batch mode and JSON output. Model and device are configurable.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List, Optional

from transformers import pipeline

logger = logging.getLogger(__name__)


class HFAnalysisError(Exception):
    """Raised when the Transformers pipeline fails or misconfigured."""


@dataclass(frozen=True)
class SentimentPrediction:
    label: str
    score: float


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sentiment analysis via Transformers pipeline.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", type=str, help="Text to analyze")
    source.add_argument("--file", type=Path, help="Path to a UTF-8 text file")

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output predictions as JSON",
    )
    parser.add_argument(
        "--split-lines",
        action="store_true",
        help="Treat input as multiple lines and analyze each line separately",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=8,
        help="Batch size for pipeline calls when analyzing many lines",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="distilbert-base-uncased-finetuned-sst-2-english",
        help="Model checkpoint to use for sentiment-analysis",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cpu", "gpu"],
        default="auto",
        help="Computation device selection",
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def read_text_from_stdin() -> Optional[str]:
    if sys.stdin is None or sys.stdin.isatty():
        return None
    return sys.stdin.read()


def load_text_from_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        raise HFAnalysisError(f"Failed to read file '{path}': {ex}") from ex


def resolve_device_arg(device_pref: str) -> int:
    """Return device index for HF pipeline. -1 for CPU, >=0 for GPU index."""
    if device_pref == "cpu":
        return -1
    if device_pref == "gpu":
        return 0
    # auto
    try:
        import torch  # type: ignore

        return 0 if torch.cuda.is_available() else -1
    except Exception:  # noqa: BLE001
        return -1


def build_classifier(model_name: str, device_pref: str):
    try:
        device = resolve_device_arg(device_pref)
        return pipeline("sentiment-analysis", model=model_name, device=device)
    except Exception as ex:  # noqa: BLE001
        raise HFAnalysisError(f"Failed to initialize pipeline: {ex}") from ex


def batched(iterable: Iterable[str], batch_size: int) -> Iterable[List[str]]:
    batch: List[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


def analyze_texts(
    classifier: Any, texts: List[str], batch_size: int
) -> List[SentimentPrediction]:
    predictions: List[SentimentPrediction] = []
    for batch in batched(texts, max(1, batch_size)):
        outputs = classifier(batch)
        for out in outputs:
            # Expected format: {"label": "POSITIVE"|"NEGATIVE", "score": float}
            label = str(out.get("label", ""))
            score = float(out.get("score", 0.0))
            predictions.append(SentimentPrediction(label=label, score=score))
    return predictions


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    text: Optional[str] = None
    if args.text is not None:
        text = args.text
    elif args.file is not None:
        text = load_text_from_file(args.file)
    else:
        text = read_text_from_stdin()

    if text is None:
        logger.error("No input provided. Use --text, --file, or pipe via stdin.")
        return 2

    texts: List[str] = [
        t for t in (text.splitlines() if args.split_lines else [text]) if t.strip()
    ]

    if not texts:
        logger.error("Input is empty after processing.")
        return 2

    try:
        clf = build_classifier(args.model, args.device)
        preds = analyze_texts(clf, texts, args.batch_size)
    except HFAnalysisError as ex:
        logger.error(str(ex))
        return 1

    if args.json:
        print(json.dumps([pred.__dict__ for pred in preds]))
    else:
        for t, p in zip(texts, preds):
            logger.info(f"{t!r} -> {p.label} ({p.score:.3f})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
