"""Link preview generator: extract OpenGraph/Twitter meta and basics.

Usage:
  python -m web.link_preview https://example.com --json out.json --download-image --out-card preview.png
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup, Tag
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class LinkPreview:
    url: str
    title: Optional[str] = None
    description: Optional[str] = None
    site_name: Optional[str] = None
    canonical_url: Optional[str] = None
    favicon: Optional[str] = None
    image: Optional[str] = None
    twitter_card: Optional[str] = None
    og: Dict[str, str] = field(default_factory=dict)  # raw og:* map
    twitter: Dict[str, str] = field(default_factory=dict)  # raw twitter:* map


class LinkPreviewError(RuntimeError):
    """Raised when fetching or parsing fails."""


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract link preview metadata (OpenGraph/Twitter)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("url", type=str, help="URL to fetch")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--json", type=Path, help="Write JSON metadata to file")
    parser.add_argument(
        "--download-image", action="store_true", help="Download og:image"
    )
    parser.add_argument("--image-out", type=Path, help="Path to save downloaded image")
    parser.add_argument("--out-card", type=Path, help="Optional small preview card PNG")
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    return parser.parse_args()


def fetch_html(url: str, timeout: int) -> Tuple[str, str]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; LinkPreviewBot/1.0; +https://example.com)"
        }
        resp = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
        resp.raise_for_status()
        final_url = resp.url
        return resp.text, final_url
    except requests.RequestException as ex:
        raise LinkPreviewError(f"Failed to fetch URL: {ex}") from ex


def absolutize(base_url: str, href: Optional[str]) -> Optional[str]:
    if not href:
        return None
    return urljoin(base_url, href)


def get_attr_str(tag: Tag, attr: str) -> Optional[str]:
    val = tag.get(attr)
    return val if isinstance(val, str) else None


def extract_meta(url: str, html: str) -> LinkPreview:
    soup = BeautifulSoup(html, "html.parser")
    # Canonical
    canonical = soup.select_one("link[rel=canonical]")
    canonical_href = (
        get_attr_str(canonical, "href") if isinstance(canonical, Tag) else None
    )
    canonical_url = absolutize(url, canonical_href)

    # Favicon
    icon = soup.select_one("link[rel~='icon'], link[rel~='shortcut icon']")
    icon_href = get_attr_str(icon, "href") if isinstance(icon, Tag) else None
    favicon_url = absolutize(url, icon_href)

    # Title / description basics
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None
    desc_tag = soup.find("meta", attrs={"name": "description"})
    description = (
        get_attr_str(desc_tag, "content") if isinstance(desc_tag, Tag) else None
    )

    # OpenGraph and Twitter
    og: Dict[str, str] = {}
    tw: Dict[str, str] = {}
    for tag in soup.find_all("meta"):
        if not isinstance(tag, Tag):
            continue
        prop = get_attr_str(tag, "property") or get_attr_str(tag, "name")
        content = get_attr_str(tag, "content")
        if not prop or not content:
            continue
        if prop.startswith("og:"):
            og[prop] = content
        if prop.startswith("twitter:"):
            tw[prop] = content

    # Prefer OG/Twitter values when available
    site_name = og.get("og:site_name")
    title = og.get("og:title") or tw.get("twitter:title") or title
    description = (
        og.get("og:description") or tw.get("twitter:description") or description
    )
    image_rel = (
        og.get("og:image") or tw.get("twitter:image") or tw.get("twitter:image:src")
    )
    image = absolutize(url, image_rel) if image_rel else None
    twitter_card = tw.get("twitter:card")

    return LinkPreview(
        url=url,
        title=title,
        description=description,
        site_name=site_name,
        canonical_url=canonical_url,
        favicon=favicon_url,
        image=image,
        twitter_card=twitter_card,
        og=og,
        twitter=tw,
    )


def download_image(image_url: str, out_path: Path, timeout: int) -> None:
    try:
        resp = requests.get(image_url, timeout=timeout, stream=True)
        resp.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        logger.info(f"Downloaded image to {out_path}")
    except requests.RequestException as ex:
        raise LinkPreviewError(f"Failed to download image: {ex}") from ex


def render_card(meta: LinkPreview, out_path: Path, timeout: int) -> None:
    # Very minimal: 800x420 card with background from image (if available) and a text strip
    width, height = 800, 420
    bg = Image.new("RGB", (width, height), (30, 30, 30))
    if meta.image:
        try:
            resp = requests.get(meta.image, timeout=timeout, stream=True)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img.thumbnail((width, height))
            x = (width - img.width) // 2
            y = (height - img.height) // 2
            bg.paste(img, (x, y))
        except Exception as ex:  # noqa: BLE001
            logger.debug(f"Card image load failed: {ex}")

    # Simple dark overlay at bottom and text
    try:
        from PIL import ImageDraw, ImageFont

        overlay_h = 120
        draw = ImageDraw.Draw(bg)
        draw.rectangle(((0, height - overlay_h), (width, height)), fill=(0, 0, 0, 200))
        title = (meta.title or urlparse(meta.url).netloc)[:120]
        desc = (meta.description or "")[:180]
        font = ImageFont.load_default()
        draw.text((20, height - overlay_h + 16), title, fill=(255, 255, 255), font=font)
        draw.text((20, height - overlay_h + 44), desc, fill=(220, 220, 220), font=font)
    except Exception as ex:  # noqa: BLE001
        logger.debug(f"Text drawing failed: {ex}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    bg.save(out_path)
    logger.info(f"Wrote preview card to {out_path}")


def main() -> int:
    args = parse_arguments()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        html, final_url = fetch_html(args.url, args.timeout)
        meta = extract_meta(final_url, html)
    except LinkPreviewError as ex:
        logger.error(str(ex))
        return 1

    if args.json:
        try:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(
                json.dumps(asdict(meta), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            logger.info(f"Wrote JSON to {args.json}")
        except Exception as ex:  # noqa: BLE001
            logger.error(f"Failed to write JSON: {ex}")
            return 1
    else:
        print(json.dumps(asdict(meta), ensure_ascii=False, indent=2))

    if args.download_image and meta.image:
        if not args.image_out:
            logger.error("--image-out is required when using --download-image")
            return 2
        try:
            download_image(meta.image, args.image_out, args.timeout)
        except LinkPreviewError as ex:
            logger.error(str(ex))
            return 1

    if args.out_card:
        try:
            render_card(meta, args.out_card, args.timeout)
        except LinkPreviewError as ex:
            logger.error(str(ex))
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
