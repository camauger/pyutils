"""Voice to-do capture CLI using SpeechRecognition with logging.

Install: pip install SpeechRecognition pyaudio (or sounddevice) depending on OS.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import speech_recognition as sr  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)


class VoiceTodoError(RuntimeError):
    """Raised when voice capture or recognition fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture a to-do item from voice and append to a file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output", type=Path, default=Path("tasks.txt"), help="To-do file path"
    )
    parser.add_argument(
        "--device-index", type=int, help="Microphone device index (optional)"
    )
    parser.add_argument(
        "--energy-threshold",
        type=int,
        default=300,
        help="Energy threshold for ambient noise",
    )
    parser.add_argument(
        "--timeout", type=float, default=5.0, help="Seconds to wait for phrase start"
    )
    parser.add_argument(
        "--phrase-time-limit", type=float, default=10.0, help="Max seconds to capture"
    )
    parser.add_argument(
        "--language", type=str, default="en-US", help="Recognition language code"
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def capture_and_recognize(
    device_index: Optional[int],
    energy_threshold: int,
    timeout: float,
    phrase_time_limit: float,
    language: str,
) -> str:
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = max(0, energy_threshold)
    mic_kwargs = {"device_index": device_index} if device_index is not None else {}
    try:
        with sr.Microphone(**mic_kwargs) as source:
            logger.info("Say your task...")
            recognizer.adjust_for_ambient_noise(source, duration=int(1))
            audio = recognizer.listen(
                source, timeout=timeout, phrase_time_limit=phrase_time_limit
            )
    except Exception as ex:  # noqa: BLE001
        raise VoiceTodoError(f"Failed to capture audio: {ex}") from ex

    # Try Google Web Speech API (free, may have limits)
    try:
        text: str = recognizer.recognize_google(audio, language=language)  # type: ignore[assignment]
        return text
    except sr.UnknownValueError:  # type: ignore[attr-defined]
        raise VoiceTodoError("Could not understand audio")
    except sr.RequestError as ex:  # type: ignore[attr-defined]
        raise VoiceTodoError(f"API request error: {ex}") from ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        text = capture_and_recognize(
            device_index=args.device_index,
            energy_threshold=args.energy_threshold,
            timeout=args.timeout,
            phrase_time_limit=args.phrase_time_limit,
            language=args.language,
        )
    except VoiceTodoError as ex:
        logger.error(str(ex))
        return 1

    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("a", encoding="utf-8") as f:
            f.write(f"{text}\n")
    except Exception as ex:  # noqa: BLE001
        logger.error(f"Failed to write to-do: {ex}")
        return 1

    logger.info(f"Added: {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
