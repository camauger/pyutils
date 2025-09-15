"""Audio speaker utility using pywhatkit TTS.

Provides a simple CLI to speak text from a string, a file, or stdin.

Examples:
  - Speak a short text:
    python audio_speaker.py --text "Hello there!"

  - Speak content from a file:
    python audio_speaker.py --file notes.txt

  - Pipe text via stdin:
    echo "Hello" | python audio_speaker.py
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

import pywhatkit as kit

logger = logging.getLogger(__name__)


class SpeechSynthesisError(Exception):
    """Raised when speech synthesis fails."""


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments for the audio speaker utility."""
    parser = argparse.ArgumentParser(
        description="Speak text using pywhatkit's text-to-speech.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", type=str, help="Text to speak")
    source.add_argument("--file", type=Path, help="Path to a UTF-8 text file")

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )

    return parser.parse_args()


def read_text_from_stdin() -> Optional[str]:
    """Read text from stdin if data is piped. Return None if stdin is a TTY."""
    if sys.stdin is None or sys.stdin.isatty():
        return None
    data = sys.stdin.read()
    return data


def load_text_from_file(path: Path) -> str:
    """Load UTF-8 text from a file, raising on errors."""
    try:
        return path.read_text(encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        raise SpeechSynthesisError(f"Failed to read file '{path}': {ex}") from ex


def speak_text(text: str) -> None:
    """Speak the given text using available TTS backends.

    Priority:
    1) pywhatkit.text_to_speech if available
    2) pyttsx3 (offline) if installed
    """
    if not text or not text.strip():
        logger.warning("Empty text provided; nothing to speak.")
        return
    try:
        tts_func = getattr(kit, "text_to_speech", None)
        if callable(tts_func):
            tts_func(text)
            logger.info("Speech synthesis completed (pywhatkit).")
            return
    except Exception as ex:  # noqa: BLE001
        # pywhatkit backend failed; try next
        logger.debug(f"pywhatkit TTS failed: {ex}")

    # Fallback to pyttsx3 if available
    try:
        import pyttsx3  # type: ignore

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        logger.info("Speech synthesis completed (pyttsx3).")
        return
    except Exception as ex:  # noqa: BLE001
        raise SpeechSynthesisError(
            "No working TTS backend. Install pywhatkit with TTS support or 'pyttsx3'."
        ) from ex


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

    try:
        speak_text(text)
    except SpeechSynthesisError as ex:
        logger.error(str(ex))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
