"""QR code generator CLI with error correction, size, colors, and logging.

Requires `qrcode[pil]` (installs Pillow backend). Example:
  pip install qrcode[pil]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import qrcode  # type: ignore[import-not-found]
except Exception:  # noqa: BLE001
    qrcode = None  # type: ignore[assignment]


logger = logging.getLogger(__name__)


class QRCodeError(RuntimeError):
    """Raised when QR code generation fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a QR code image from text or file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--data", type=str, help="Text/data to encode")
    src.add_argument("--file", type=Path, help="Read data to encode from UTF-8 file")

    parser.add_argument(
        "--output", type=Path, default=Path("qrcode.png"), help="Output image path"
    )
    parser.add_argument(
        "--version",
        type=int,
        default=None,
        help="QR version (1-40); default auto based on data",
    )
    parser.add_argument(
        "--error",
        choices=["L", "M", "Q", "H"],
        default="M",
        help="Error correction level",
    )
    parser.add_argument(
        "--box-size", type=int, default=10, help="Pixel size of each box"
    )
    parser.add_argument(
        "--border", type=int, default=4, help="Border boxes around the code"
    )
    parser.add_argument("--fill", type=str, default="black", help="Foreground color")
    parser.add_argument("--back", type=str, default="white", help="Background color")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def read_data(data: Optional[str], file: Optional[Path]) -> str:
    if data is not None:
        return data
    assert file is not None
    try:
        return file.read_text(encoding="utf-8")
    except Exception as ex:  # noqa: BLE001
        raise QRCodeError(f"Failed to read data file '{file}': {ex}") from ex


def error_correction(level: str) -> Any:
    if qrcode is None:
        raise QRCodeError(
            "qrcode library is not installed. Run: pip install qrcode[pil]"
        )
    constants = getattr(qrcode, "constants", None)
    if constants is None:
        raise QRCodeError("qrcode.constants is not available in the installed package")
    mapping = {
        "L": getattr(constants, "ERROR_CORRECT_L"),
        "M": getattr(constants, "ERROR_CORRECT_M"),
        "Q": getattr(constants, "ERROR_CORRECT_Q"),
        "H": getattr(constants, "ERROR_CORRECT_H"),
    }
    return mapping[level]


def generate_qr_code(
    data: str,
    output_path: Path,
    version: Optional[int],
    error_level: str,
    box_size: int,
    border: int,
    fill: str,
    back: str,
) -> None:
    if qrcode is None:
        raise QRCodeError(
            "qrcode library is not installed. Run: pip install qrcode[pil]"
        )
    if not data.strip():
        raise QRCodeError("Data is empty")
    if version is not None and not (1 <= version <= 40):
        raise QRCodeError("--version must be between 1 and 40")

    try:
        qr = qrcode.QRCode(
            version=version,
            error_correction=error_correction(error_level),
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill, back_color=back)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            img.save(f)
    except Exception as ex:  # noqa: BLE001
        raise QRCodeError(f"Failed to generate QR code: {ex}") from ex


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        data = read_data(args.data, args.file)
        generate_qr_code(
            data=data,
            output_path=args.output,
            version=args.version,
            error_level=args.error,
            box_size=args.box_size,
            border=args.border,
            fill=args.fill,
            back=args.back,
        )
    except QRCodeError as ex:
        logger.error(str(ex))
        return 1

    logger.info(f"Saved QR code to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
