"""Shared image processing utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Tuple

from PIL import Image

logger = logging.getLogger(__name__)

SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}


def is_image_file(path: Path) -> bool:
    """Check if file is a supported image format.

    Args:
        path: Path to check

    Returns:
        True if file has supported image extension
    """
    return path.suffix.lower() in SUPPORTED_FORMATS


def load_image(path: Path) -> Image.Image:
    """Load image with error handling.

    Args:
        path: Path to image file

    Returns:
        PIL Image object

    Raises:
        ValueError: If file is not a valid image
    """
    try:
        img = Image.open(path)
        img.load()  # Force load to catch truncated images
        return img
    except Exception as e:
        raise ValueError(f"Failed to load image {path}: {e}") from e


def calculate_dimensions(
    original: Tuple[int, int],
    target_width: int | None = None,
    target_height: int | None = None,
    keep_aspect: bool = True,
) -> Tuple[int, int]:
    """Calculate target dimensions maintaining aspect ratio.

    Args:
        original: (width, height) of original image
        target_width: Desired width (None to calculate from height)
        target_height: Desired height (None to calculate from width)
        keep_aspect: Maintain aspect ratio

    Returns:
        (width, height) tuple
    """
    orig_w, orig_h = original

    if not keep_aspect:
        return (target_width or orig_w, target_height or orig_h)

    if target_width and target_height:
        # Both specified: fit within bounds
        scale = min(target_width / orig_w, target_height / orig_h)
        return (int(orig_w * scale), int(orig_h * scale))

    if target_width:
        scale = target_width / orig_w
        return (target_width, int(orig_h * scale))

    if target_height:
        scale = target_height / orig_h
        return (int(orig_w * scale), target_height)

    return original

