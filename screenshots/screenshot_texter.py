from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Protocol, cast

from PIL import Image


class _PytesseractModule(Protocol):
    def image_to_string(self, image: Image.Image, *args: Any, **kwargs: Any) -> str: ...


def _load_pytesseract() -> _PytesseractModule:
    """Import pytesseract lazily so the module stays optional."""
    try:
        module = importlib.import_module("pytesseract")
        return cast(_PytesseractModule, module)
    except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
        raise ImportError(
            "pytesseract is required for OCR support. Install it via 'pip install pytesseract'."
        ) from exc


def extract_text(image_path: str | Path) -> str:
    """Return OCR text from a screenshot."""
    path = Path(image_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Screenshot not found: {path}")
    with Image.open(path) as img:
        pytesseract = _load_pytesseract()
        text = pytesseract.image_to_string(img)
        return str(text)


def main(image_path: str = "code_screenshot.png") -> None:
    text = extract_text(image_path)
    print(text)


if __name__ == "__main__":
    main()
