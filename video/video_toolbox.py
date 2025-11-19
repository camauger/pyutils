"""Video processing toolbox CLI.

This script bundles a few common video helpers behind a single typed CLI.
It supports multiple backends (``moviepy`` and ``ffmpeg-python``) and keeps
imports optional so the toolbox works even if you only install one of them.

Examples
--------
Trim 5 seconds from a clip::

    python -m video.video_toolbox trim input.mp4 output.mp4 --start 00:00:10 --duration 5

Convert part of a clip to a GIF::

    python -m video.video_toolbox to-gif demo.mov demo.gif --start 2 --end 8 --fps 12

Extract one frame per second::

    python -m video.video_toolbox extract-frames clip.mp4 ./frames --fps 1
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    import moviepy.editor as moviepy_editor  # type: ignore
except Exception:  # pragma: no cover - import guard
    moviepy_editor = None

try:  # pragma: no cover - optional dependency
    import ffmpeg  # type: ignore
except Exception:  # pragma: no cover - import guard
    ffmpeg = None


class MissingDependencyError(RuntimeError):
    """Raised when an optional dependency is required but missing."""


class VideoProcessingError(RuntimeError):
    """Raised when processing fails due to invalid input or runtime errors."""


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        description="Video toolbox with trimming, GIF conversion, and frame extraction.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="INFO",
        help="Logging verbosity",
    )
    parser.add_argument(
        "--backend",
        choices=["auto", "moviepy", "ffmpeg"],
        default="auto",
        help="Processing backend to use. 'auto' prefers moviepy when available.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    trim_parser = subparsers.add_parser(
        "trim",
        help="Trim a video clip to a shorter segment.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    trim_parser.add_argument("input", type=Path, help="Input video path")
    trim_parser.add_argument("output", type=Path, help="Output video path")
    add_time_range_arguments(trim_parser)
    trim_parser.add_argument("--fps", type=float, help="Force output frame rate")
    trim_parser.set_defaults(handler=handle_trim)

    gif_parser = subparsers.add_parser(
        "to-gif",
        help="Convert a video (or segment) to a GIF.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    gif_parser.add_argument("input", type=Path, help="Input video path")
    gif_parser.add_argument("output", type=Path, help="Output GIF path")
    add_time_range_arguments(gif_parser)
    gif_parser.add_argument("--fps", type=float, help="Frame rate for GIF frames")
    gif_parser.set_defaults(handler=handle_to_gif)

    frames_parser = subparsers.add_parser(
        "extract-frames",
        help="Extract frames from a clip into individual image files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    frames_parser.add_argument("input", type=Path, help="Input video path")
    frames_parser.add_argument("output", type=Path, help="Directory for extracted frames")
    add_time_range_arguments(frames_parser)
    frames_parser.add_argument("--fps", type=float, help="Frames per second to sample")
    frames_parser.add_argument(
        "--prefix",
        default="frame",
        help="Filename prefix for extracted frames",
    )
    frames_parser.add_argument(
        "--image-format",
        default="png",
        help="Image format/extension for frames (png, jpg, ...)",
    )
    frames_parser.set_defaults(handler=handle_extract_frames)

    return parser


def add_time_range_arguments(parser: argparse.ArgumentParser) -> None:
    """Add shared time range arguments to a parser."""
    parser.add_argument("--start", type=str, help="Start time (seconds or HH:MM:SS)")
    parser.add_argument("--end", type=str, help="End time (seconds or HH:MM:SS)")
    parser.add_argument(
        "--duration",
        type=str,
        help="Clip duration (seconds or HH:MM:SS). Mutually exclusive with --end.",
    )


TimeRange = Tuple[Optional[float], Optional[float]]


def parse_timecode(value: Optional[str]) -> Optional[float]:
    """Convert a time code into seconds."""
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if ":" in text:
        parts = text.split(":")
        if len(parts) > 3:
            raise VideoProcessingError(f"Invalid timecode '{value}'.")
        seconds = 0.0
        for part in parts:
            try:
                number = float(part)
            except ValueError as exc:  # pragma: no cover - defensive
                raise VideoProcessingError(f"Invalid time value '{value}'.") from exc
            seconds = seconds * 60 + number
        return seconds
    try:
        return float(text)
    except ValueError as exc:  # pragma: no cover - defensive
        raise VideoProcessingError(f"Invalid time value '{value}'.") from exc


def resolve_time_range(start: Optional[str], end: Optional[str], duration: Optional[str]) -> TimeRange:
    """Parse and validate time range CLI arguments."""
    start_s = parse_timecode(start)
    end_s = parse_timecode(end)
    duration_s = parse_timecode(duration)

    if duration_s is not None and end_s is not None:
        raise VideoProcessingError("--duration and --end cannot be used together.")
    if start_s is not None and start_s < 0:
        raise VideoProcessingError("Start time must be non-negative.")
    if end_s is not None and end_s < 0:
        raise VideoProcessingError("End time must be non-negative.")
    if duration_s is not None and duration_s <= 0:
        raise VideoProcessingError("Duration must be greater than zero.")

    if duration_s is not None:
        start_s = 0.0 if start_s is None else start_s
        end_s = start_s + duration_s
    elif end_s is not None and start_s is None:
        start_s = 0.0

    if start_s is not None and end_s is not None and end_s <= start_s:
        raise VideoProcessingError("End time must be greater than start time.")

    return start_s, end_s


def ensure_input_file(path: Path) -> None:
    """Validate that an input file exists and is not a directory."""
    if not path.exists():
        raise VideoProcessingError(f"Input file '{path}' does not exist.")
    if path.is_dir():
        raise VideoProcessingError(f"Input path '{path}' is a directory, not a file.")


def ensure_parent_dir(path: Path) -> None:
    """Ensure the parent directory for the output path exists."""
    parent = path.parent
    if parent and not parent.exists():
        parent.mkdir(parents=True, exist_ok=True)


def ensure_output_dir(path: Path) -> None:
    """Ensure an output directory exists."""
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    elif not path.is_dir():
        raise VideoProcessingError(f"Output path '{path}' must be a directory.")


def pick_backend(preference: str) -> str:
    """Select a processing backend based on availability and user preference."""
    preference = preference or "auto"
    if preference == "moviepy":
        if moviepy_editor is None:
            raise MissingDependencyError(
                "moviepy is not installed. Install 'moviepy' to use this backend."
            )
        return "moviepy"
    if preference == "ffmpeg":
        if ffmpeg is None:
            raise MissingDependencyError(
                "ffmpeg-python is not installed. Install 'ffmpeg-python' to use this backend."
            )
        return "ffmpeg"

    if moviepy_editor is not None:
        return "moviepy"
    if ffmpeg is not None:
        return "ffmpeg"
    raise MissingDependencyError("Install 'moviepy' or 'ffmpeg-python' to use video features.")


def format_seconds(value: Optional[float]) -> str:
    """Human friendly formatting for seconds."""
    if value is None:
        return "full clip"
    minutes, seconds = divmod(value, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}"
    if minutes:
        return f"{int(minutes):02d}:{seconds:05.2f}"
    return f"{seconds:.2f}s"


def handle_trim(args: argparse.Namespace) -> None:
    """Handle the trim subcommand."""
    input_path: Path = args.input
    output_path: Path = args.output
    ensure_input_file(input_path)
    ensure_parent_dir(output_path)

    start, end = resolve_time_range(args.start, args.end, args.duration)
    fps = args.fps
    if fps is not None and fps <= 0:
        raise VideoProcessingError("FPS must be greater than zero.")

    backend = pick_backend(args.backend)
    logger.info(
        "Trimming %s -> %s using %s backend (start=%s, end=%s, fps=%s)",
        input_path,
        output_path,
        backend,
        format_seconds(start),
        format_seconds(end),
        fps or "source",
    )

    if backend == "moviepy":
        trim_with_moviepy(input_path, output_path, start, end, fps)
    else:
        trim_with_ffmpeg(input_path, output_path, start, end, fps)

    logger.info("Saved trimmed clip to %s", output_path)


def handle_to_gif(args: argparse.Namespace) -> None:
    """Handle the to-gif subcommand."""
    input_path: Path = args.input
    output_path: Path = args.output
    ensure_input_file(input_path)
    ensure_parent_dir(output_path)

    start, end = resolve_time_range(args.start, args.end, args.duration)
    fps = args.fps
    if fps is not None and fps <= 0:
        raise VideoProcessingError("FPS must be greater than zero.")

    backend = pick_backend(args.backend)
    logger.info(
        "Converting %s -> %s using %s backend (start=%s, end=%s, fps=%s)",
        input_path,
        output_path,
        backend,
        format_seconds(start),
        format_seconds(end),
        fps or "source",
    )

    if backend == "moviepy":
        gif_with_moviepy(input_path, output_path, start, end, fps)
    else:
        gif_with_ffmpeg(input_path, output_path, start, end, fps)

    logger.info("Saved GIF to %s", output_path)


def handle_extract_frames(args: argparse.Namespace) -> None:
    """Handle the extract-frames subcommand."""
    input_path: Path = args.input
    output_dir: Path = args.output
    ensure_input_file(input_path)
    ensure_output_dir(output_dir)

    start, end = resolve_time_range(args.start, args.end, args.duration)
    fps = args.fps
    if fps is not None and fps <= 0:
        raise VideoProcessingError("FPS must be greater than zero.")

    backend = pick_backend(args.backend)
    logger.info(
        "Extracting frames from %s into %s using %s backend (start=%s, end=%s, fps=%s)",
        input_path,
        output_dir,
        backend,
        format_seconds(start),
        format_seconds(end),
        fps or "source",
    )

    if backend == "moviepy":
        count = frames_with_moviepy(
            input_path,
            output_dir,
            start,
            end,
            fps,
            prefix=args.prefix,
            image_format=args.image_format,
        )
    else:
        count = frames_with_ffmpeg(
            input_path,
            output_dir,
            start,
            end,
            fps,
            prefix=args.prefix,
            image_format=args.image_format,
        )

    logger.info("Extracted %s frame(s) into %s", count, output_dir)


def trim_with_moviepy(
    input_path: Path,
    output_path: Path,
    start: Optional[float],
    end: Optional[float],
    fps: Optional[float],
) -> None:
    if moviepy_editor is None:  # pragma: no cover - defensive
        raise MissingDependencyError("moviepy backend is unavailable.")

    clip = moviepy_editor.VideoFileClip(str(input_path))
    clips_to_close = [clip]
    try:
        working_clip = clip
        if start is not None or end is not None:
            working_clip = clip.subclip(start or 0.0, end)
            clips_to_close.append(working_clip)
        if fps:
            working_clip = working_clip.set_fps(fps)
            clips_to_close.append(working_clip)
        write_kwargs = {"logger": None}
        working_clip.write_videofile(str(output_path), **write_kwargs)
    finally:
        close_clips(clips_to_close)


def trim_with_ffmpeg(
    input_path: Path,
    output_path: Path,
    start: Optional[float],
    end: Optional[float],
    fps: Optional[float],
) -> None:
    if ffmpeg is None:  # pragma: no cover - defensive
        raise MissingDependencyError("ffmpeg backend is unavailable.")

    input_kwargs = {}
    if start is not None:
        input_kwargs["ss"] = start
    duration: Optional[float] = None
    if end is not None:
        if start is not None:
            duration = end - start
        else:
            input_kwargs["to"] = end
    if duration is not None:
        input_kwargs["t"] = duration

    stream = ffmpeg.input(str(input_path), **input_kwargs)
    if fps:
        stream = stream.filter("fps", fps=fps)
    stream = ffmpeg.output(stream, str(output_path))
    run_ffmpeg(stream)


def gif_with_moviepy(
    input_path: Path,
    output_path: Path,
    start: Optional[float],
    end: Optional[float],
    fps: Optional[float],
) -> None:
    if moviepy_editor is None:  # pragma: no cover - defensive
        raise MissingDependencyError("moviepy backend is unavailable.")

    clip = moviepy_editor.VideoFileClip(str(input_path))
    clips_to_close = [clip]
    try:
        working_clip = clip
        if start is not None or end is not None:
            working_clip = clip.subclip(start or 0.0, end)
            clips_to_close.append(working_clip)
        if fps:
            working_clip = working_clip.set_fps(fps)
            clips_to_close.append(working_clip)
        write_kwargs = {"logger": None}
        working_clip.write_gif(str(output_path), **write_kwargs)
    finally:
        close_clips(clips_to_close)


def gif_with_ffmpeg(
    input_path: Path,
    output_path: Path,
    start: Optional[float],
    end: Optional[float],
    fps: Optional[float],
) -> None:
    if ffmpeg is None:  # pragma: no cover - defensive
        raise MissingDependencyError("ffmpeg backend is unavailable.")

    input_kwargs = {}
    if start is not None:
        input_kwargs["ss"] = start
    if end is not None:
        if start is not None:
            input_kwargs["t"] = end - start
        else:
            input_kwargs["to"] = end

    stream = ffmpeg.input(str(input_path), **input_kwargs)
    if fps:
        stream = stream.filter("fps", fps=fps)
    stream = ffmpeg.output(stream, str(output_path), loop=0)
    run_ffmpeg(stream)


def frames_with_moviepy(
    input_path: Path,
    output_dir: Path,
    start: Optional[float],
    end: Optional[float],
    fps: Optional[float],
    *,
    prefix: str,
    image_format: str,
) -> int:
    if moviepy_editor is None:  # pragma: no cover - defensive
        raise MissingDependencyError("moviepy backend is unavailable.")

    clip = moviepy_editor.VideoFileClip(str(input_path))
    clips_to_close = [clip]
    try:
        working_clip = clip
        if start is not None or end is not None:
            working_clip = clip.subclip(start or 0.0, end)
            clips_to_close.append(working_clip)
        fps_value = fps or getattr(working_clip, "fps", None) or getattr(clip, "fps", None) or 24.0
        if fps_value <= 0:
            raise VideoProcessingError("Detected frame rate is invalid.")
        duration = float(working_clip.duration or 0.0)
        if duration <= 0:
            raise VideoProcessingError("Selected segment has zero duration.")
        interval = 1.0 / fps_value
        frame_time = 0.0
        count = 0
        while frame_time < duration:
            count += 1
            filename = output_dir / f"{prefix}{count:05d}.{image_format}"
            working_clip.save_frame(str(filename), t=frame_time)
            frame_time += interval
        if count == 0:
            filename = output_dir / f"{prefix}00001.{image_format}"
            working_clip.save_frame(str(filename), t=0.0)
            count = 1
        return count
    finally:
        close_clips(clips_to_close)


def frames_with_ffmpeg(
    input_path: Path,
    output_dir: Path,
    start: Optional[float],
    end: Optional[float],
    fps: Optional[float],
    *,
    prefix: str,
    image_format: str,
) -> int:
    if ffmpeg is None:  # pragma: no cover - defensive
        raise MissingDependencyError("ffmpeg backend is unavailable.")

    input_kwargs = {}
    if start is not None:
        input_kwargs["ss"] = start
    if end is not None:
        if start is not None:
            input_kwargs["t"] = end - start
        else:
            input_kwargs["to"] = end

    pattern = output_dir / f"{prefix}%05d.{image_format}"
    stream = ffmpeg.input(str(input_path), **input_kwargs)
    if fps:
        stream = stream.filter("fps", fps=fps)
    stream = ffmpeg.output(stream, str(pattern), vsync="vfr")
    run_ffmpeg(stream)

    # Estimate the number of frames by counting files matching the prefix
    matching = list(sorted(output_dir.glob(f"{prefix}[0-9]{{5}}.{image_format}")))
    return len(matching)


def close_clips(clips: Iterable[object]) -> None:
    """Close moviepy clip objects, ignoring errors."""
    seen_ids = set()
    for clip in clips:
        if clip is None:
            continue
        clip_id = id(clip)
        if clip_id in seen_ids:
            continue
        seen_ids.add(clip_id)
        close = getattr(clip, "close", None)
        if callable(close):
            try:
                close()
            except Exception:  # pragma: no cover - best effort cleanup
                logger.debug("Failed to close clip cleanly", exc_info=True)


def run_ffmpeg(stream: object) -> None:
    """Execute an ffmpeg-python stream and surface errors clearly."""
    if ffmpeg is None:  # pragma: no cover - defensive
        raise MissingDependencyError("ffmpeg backend is unavailable.")
    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as exc:  # type: ignore[attr-defined]
        stderr = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
        raise VideoProcessingError(f"ffmpeg processing failed: {stderr.strip()}") from exc


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    try:
        handler: Callable[[argparse.Namespace], None] = args.handler
    except AttributeError:  # pragma: no cover - argparse fallback
        parser.print_help()
        return 2

    try:
        handler(args)
    except MissingDependencyError as exc:
        logger.error(str(exc))
        return 2
    except VideoProcessingError as exc:
        logger.error(str(exc))
        return 1
    except Exception:  # pragma: no cover - unexpected
        logger.exception("Unexpected error during video processing")
        return 1

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())
