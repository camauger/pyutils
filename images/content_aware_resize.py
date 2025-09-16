"""Content-aware image resizing (seam carving) with a Typer CLI.

Depends on scikit-image and Pillow.

Examples:
  python -m images.content_aware_resize input.jpg output.jpg --width 800
  python -m images.content_aware_resize input.jpg output.jpg --height 600
  python -m images.content_aware_resize input.jpg output.jpg --width 800 --energy sobel
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import numpy as np
import typer
from PIL import Image
from skimage import color, filters

logger = logging.getLogger(__name__)
app = typer.Typer(help="Content-aware resize (seam carving)")


class CarvingError(RuntimeError):
    """Raised when content-aware resizing fails."""


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )


def _load_image_as_float_rgb(path: Path) -> np.ndarray:
    try:
        with Image.open(path) as img:
            img = img.convert("RGB")
            arr = np.asarray(img).astype(np.float32) / 255.0
            return arr
    except FileNotFoundError as ex:
        raise CarvingError(f"Input not found: {path}") from ex
    except Exception as ex:  # noqa: BLE001
        raise CarvingError(f"Failed to open image '{path}': {ex}") from ex


def _save_image_uint8(arr: np.ndarray, path: Path) -> None:
    arr = np.clip(arr * 255.0, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def _compute_energy(image_rgb: np.ndarray, method: str) -> np.ndarray:
    gray = color.rgb2gray(image_rgb)
    if method in {"auto", "sobel"}:
        e = np.abs(filters.sobel(gray))
        return e.astype(np.float32)
    raise CarvingError(f"Unsupported energy method: {method}")


def _compute_vertical_cumulative_energy(
    energy: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    h, w = energy.shape
    m = np.zeros_like(energy, dtype=np.float32)
    backtrack = np.zeros((h, w), dtype=np.int32)
    m[0] = energy[0]
    for i in range(1, h):
        for j in range(w):
            left = m[i - 1, j - 1] if j - 1 >= 0 else np.inf
            up = m[i - 1, j]
            right = m[i - 1, j + 1] if j + 1 < w else np.inf
            idx = int(np.argmin([left, up, right]) - 1)  # -1, 0, or +1
            backtrack[i, j] = j + idx
            m[i, j] = energy[i, j] + (left if idx == -1 else up if idx == 0 else right)
    return m, backtrack


def _find_vertical_seam(energy: np.ndarray) -> np.ndarray:
    m, backtrack = _compute_vertical_cumulative_energy(energy)
    h, _ = energy.shape
    seam = np.zeros(h, dtype=np.int32)
    seam[-1] = int(np.argmin(m[-1]))
    for i in range(h - 2, -1, -1):
        seam[i] = backtrack[i + 1, seam[i + 1]]
    return seam


def _remove_vertical_seam(image: np.ndarray, seam: np.ndarray) -> np.ndarray:
    h, w, c = image.shape
    out = np.zeros((h, w - 1, c), dtype=image.dtype)
    for i in range(h):
        j = seam[i]
        out[i, :, :] = np.concatenate((image[i, :j, :], image[i, j + 1 :, :]), axis=0)
    return out


def _reduce_width(image: np.ndarray, target_w: int, energy_method: str) -> np.ndarray:
    current = image
    while current.shape[1] > target_w:
        energy = _compute_energy(current, energy_method)
        seam = _find_vertical_seam(energy)
        current = _remove_vertical_seam(current, seam)
    return current


def _reduce_height(image: np.ndarray, target_h: int, energy_method: str) -> np.ndarray:
    # Transpose to reuse vertical reduction logic
    transposed = np.transpose(image, (1, 0, 2))
    reduced = _reduce_width(transposed, target_h, energy_method)
    return np.transpose(reduced, (1, 0, 2))


def content_aware_resize(
    input_path: Path,
    output_path: Path,
    width: Optional[int],
    height: Optional[int],
    energy: str,
) -> None:
    if width is None and height is None:
        raise CarvingError("Provide --width and/or --height")

    image = _load_image_as_float_rgb(input_path)
    h, w = image.shape[:2]
    logger.info(f"Original size: {(w, h)}")

    target_w = w if width is None else max(1, int(width))
    target_h = h if height is None else max(1, int(height))

    current = image

    if target_w != w:
        if target_w <= 0:
            raise CarvingError("Target width must be > 0")
        if target_w > w:
            raise CarvingError("Widening via seam insertion not supported yet")
        remove = w - target_w
        logger.info(f"Removing {remove} vertical seams to reach width {target_w}")
        current = _reduce_width(current, target_w, energy)

    if target_h != h:
        if target_h <= 0:
            raise CarvingError("Target height must be > 0")
        if target_h > h:
            raise CarvingError("Height increase via seam insertion not supported yet")
        remove = h - target_h
        logger.info(f"Removing {remove} horizontal seams to reach height {target_h}")
        current = _reduce_height(current, target_h, energy)

    logger.info(f"Resized size: {(current.shape[1], current.shape[0])}")
    _save_image_uint8(current, output_path)


@app.callback()
def _main(
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
) -> None:
    _configure_logging(log_level)


@app.command()
def carve(
    input: Path = typer.Argument(..., help="Input image path"),
    output: Path = typer.Argument(..., help="Output image path"),
    width: Optional[int] = typer.Option(None, "--width", help="Target width"),
    height: Optional[int] = typer.Option(None, "--height", help="Target height"),
    energy: str = typer.Option(
        "auto",
        "--energy",
        case_sensitive=False,
        help="Energy function: auto|sobel",
    ),
) -> None:
    """Content-aware resize the image to the target width/height.

    Only downsizing is supported for now (seam removal).
    """
    try:
        content_aware_resize(input, output, width, height, energy.lower())
        typer.echo(f"Saved carved image to {output}")
    except CarvingError as ex:
        typer.echo(str(ex), err=True)
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
