"""Image compare CLI: SSIM/PSNR metrics, diff heatmaps, and batch comparison.

Features
--------
- Compare two images or two folders (match by filename)
- Metrics: SSIM (Structural Similarity), PSNR
- Output colored difference heatmap and side-by-side composite
- Threshold-based pass/fail, JSON/CSV reporting
- Recursive folder mode with include/exclude globs

Dependencies
------------
- numpy
- Pillow
- scikit-image

Examples
--------
- Single pair with diff and JSON report:
  python -m images.image_compare a.jpg b.jpg --diff out_diff.png --composite out_side.png --json out.json

- Batch by matching names (recursive), CSV report:
  python -m images.image_compare ./setA ./setB --recursive --csv report.csv --diff-dir diffs/

- Enforce SSIM threshold:
  python -m images.image_compare a.jpg b.jpg --ssim-threshold 0.95 --fail-on-below
"""

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple, cast

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity as ssim

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}


@dataclass
class CompareResult:
    path_a: Path
    path_b: Path
    ssim: float
    psnr: float
    passed: Optional[bool]


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare images (SSIM/PSNR) and produce diff/summary",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("a", type=Path, help="First image or folder")
    parser.add_argument("b", type=Path, help="Second image or folder")

    sel = parser.add_argument_group("Selection")
    sel.add_argument("--recursive", action="store_true")
    sel.add_argument(
        "--include", action="append", default=[], help="Glob include (repeatable)"
    )
    sel.add_argument(
        "--exclude", action="append", default=[], help="Glob exclude (repeatable)"
    )

    out = parser.add_argument_group("Output")
    out.add_argument("--diff", type=Path, help="Write diff heatmap for single pair")
    out.add_argument(
        "--composite", type=Path, help="Write side-by-side composite for single pair"
    )
    out.add_argument("--diff-dir", type=Path, help="Folder to write batch diffs")
    out.add_argument("--csv", type=Path, help="CSV report for batch")
    out.add_argument("--json", type=Path, help="JSON report for batch or single")

    thr = parser.add_argument_group("Thresholds")
    thr.add_argument("--ssim-threshold", type=float, help="Pass if SSIM >= threshold")
    thr.add_argument(
        "--psnr-threshold", type=float, help="Pass if PSNR >= threshold (dB)"
    )
    thr.add_argument(
        "--fail-on-below",
        action="store_true",
        help="Exit 1 if any pair fails thresholds",
    )

    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def load_image_gray(path: Path) -> np.ndarray:
    img = Image.open(path).convert("L")
    arr = np.array(img, dtype=np.float32)
    return arr


def load_image_rgb(path: Path) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    arr = np.array(img, dtype=np.float32)
    return arr


def resize_to_match(a: np.ndarray, b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    if a.shape == b.shape:
        return a, b
    # resize b to a's size
    img_b = Image.fromarray(b.astype(np.uint8))
    resample = Image.Resampling.BILINEAR if hasattr(Image, "Resampling") else Image.BILINEAR  # type: ignore[attr-defined]
    img_b = img_b.resize((a.shape[1], a.shape[0]), resample=resample)
    return a, np.array(img_b, dtype=np.float32)


def compute_psnr(a: np.ndarray, b: np.ndarray) -> float:
    mse = np.mean((a - b) ** 2)
    if mse <= 1e-12:
        return float("inf")
    PIXEL_MAX = 255.0
    return 20 * np.log10(PIXEL_MAX / np.sqrt(mse))


def diff_heatmap(a_rgb: np.ndarray, b_rgb: np.ndarray) -> Image.Image:
    a, b = resize_to_match(a_rgb, b_rgb)
    diff = np.abs(a - b).mean(axis=2)  # per-pixel average abs diff
    # normalize to 0..255
    if diff.max() > 0:
        diff = (diff / diff.max()) * 255.0
    diff_img = Image.fromarray(diff.astype(np.uint8), mode="L").convert("RGB")
    # apply simple red colormap
    r = diff_img.split()[0]
    return Image.merge("RGB", (r, Image.new("L", r.size, 0), Image.new("L", r.size, 0)))


def composite_side_by_side(a_rgb: np.ndarray, b_rgb: np.ndarray) -> Image.Image:
    a, b = resize_to_match(a_rgb, b_rgb)
    ha, wa = a.shape[:2]
    hb, wb = b.shape[:2]
    w = wa + wb
    h = max(ha, hb)
    canvas = Image.new("RGB", (w, h))
    canvas.paste(Image.fromarray(a.astype(np.uint8)), (0, 0))
    canvas.paste(Image.fromarray(b.astype(np.uint8)), (wa, 0))
    return canvas


def compare_pair(
    path_a: Path, path_b: Path, diff: Optional[Path], composite: Optional[Path]
) -> CompareResult:
    a_gray = load_image_gray(path_a)
    b_gray = load_image_gray(path_b)
    a_gray, b_gray = resize_to_match(a_gray, b_gray)
    ssim_value = cast(float, ssim(a_gray, b_gray, data_range=255.0))
    psnr_value = compute_psnr(a_gray, b_gray)

    if diff is not None:
        a_rgb = load_image_rgb(path_a)
        b_rgb = load_image_rgb(path_b)
        heat = diff_heatmap(a_rgb, b_rgb)
        diff.parent.mkdir(parents=True, exist_ok=True)
        heat.save(diff)
        logger.info(f"Wrote diff: {diff}")

    if composite is not None:
        a_rgb = load_image_rgb(path_a)
        b_rgb = load_image_rgb(path_b)
        side = composite_side_by_side(a_rgb, b_rgb)
        composite.parent.mkdir(parents=True, exist_ok=True)
        side.save(composite)
        logger.info(f"Wrote composite: {composite}")

    return CompareResult(
        path_a=path_a,
        path_b=path_b,
        ssim=ssim_value,
        psnr=float(psnr_value),
        passed=None,
    )


def iter_image_files(root: Path, recursive: bool) -> Iterator[Path]:
    if root.is_file():
        yield root
        return
    if not recursive:
        for p in root.iterdir():
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
                yield p
        return
    for dirpath, dirnames, filenames in os.walk(root):
        base = Path(dirpath)
        for name in filenames:
            p = base / name
            if p.suffix.lower() in IMAGE_EXTS:
                yield p


def matches_filters(
    path: Path, base: Path, include: List[str], exclude: List[str]
) -> bool:
    rel = str(path.relative_to(base))
    name = path.name
    if include:
        ok = any(
            fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g) for g in include
        )
        if not ok:
            return False
    if exclude:
        if any(
            fnmatch.fnmatchcase(name, g) or fnmatch.fnmatchcase(rel, g) for g in exclude
        ):
            return False
    return True


def batch_compare(
    dir_a: Path,
    dir_b: Path,
    recursive: bool,
    include: List[str],
    exclude: List[str],
    diff_dir: Optional[Path],
) -> List[CompareResult]:
    base_a = dir_a.resolve()
    base_b = dir_b.resolve()
    files_a = [
        p
        for p in iter_image_files(base_a, recursive)
        if matches_filters(p, base_a, include, exclude)
    ]
    files_b_map = {p.name: p for p in iter_image_files(base_b, recursive)}
    results: List[CompareResult] = []
    for pa in files_a:
        pb = files_b_map.get(pa.name)
        if pb is None:
            logger.warning(f"Missing counterpart for {pa.name} in {dir_b}")
            continue
        diff_path = None
        if diff_dir is not None:
            diff_dir.mkdir(parents=True, exist_ok=True)
            diff_path = diff_dir / f"diff_{pa.stem}.png"
        res = compare_pair(pa, pb, diff=diff_path, composite=None)
        results.append(res)
    return results


def apply_thresholds(
    results: List[CompareResult], ssim_thr: Optional[float], psnr_thr: Optional[float]
) -> None:
    for r in results:
        pass_ssim = (ssim_thr is None) or (r.ssim >= ssim_thr)
        pass_psnr = (psnr_thr is None) or (r.psnr >= psnr_thr)
        r.passed = pass_ssim and pass_psnr


def write_reports(
    results: List[CompareResult], json_path: Optional[Path], csv_path: Optional[Path]
) -> None:
    rows = [
        {
            "a": str(r.path_a),
            "b": str(r.path_b),
            "ssim": r.ssim,
            "psnr": r.psnr,
            "passed": r.passed if r.passed is not None else "",
        }
        for r in results
    ]
    if json_path:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        logger.info(f"Wrote JSON: {json_path}")
    if csv_path:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        logger.info(f"Wrote CSV: {csv_path}")


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    # Single pair vs folder mode
    if args.a.is_file() and args.b.is_file():
        result = compare_pair(args.a, args.b, diff=args.diff, composite=args.composite)
        apply_thresholds([result], args.ssim_threshold, args.psnr_threshold)
        if args.json:
            write_reports([result], args.json, None)
        logger.info(f"SSIM={result.ssim:.4f} PSNR={result.psnr:.2f}dB")
        if args.fail_on_below and result.passed is False:
            return 1
        return 0

    if args.a.is_dir() and args.b.is_dir():
        results = batch_compare(
            args.a, args.b, args.recursive, args.include, args.exclude, args.diff_dir
        )
        apply_thresholds(results, args.ssim_threshold, args.psnr_threshold)
        if args.json or args.csv:
            write_reports(results, args.json, args.csv)
        if args.fail_on_below and any(r.passed is False for r in results):
            return 1
        logger.info(f"Compared {len(results)} pair(s)")
        return 0

    logger.error("Provide two files or two directories")
    return 2


if __name__ == "__main__":
    sys.exit(main())
