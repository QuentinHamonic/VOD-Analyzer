"""Vertical (9:16) clip renderer — Stage A: center-crop.

Takes a source VOD, video dimensions, and a list of
:class:`~vod_analyzer.core.detect.audio_energy.Candidate` windows and writes
one 9:16 MP4 clip per candidate to an output directory.

The crop keeps the horizontal centre of the frame, which works well for
typical 16:9 gaming and stream content where the action is centred.

Output layout
-------------
::

    output/<vod_id>/vertical/<index>_<slug>.mp4

Where:
- ``vod_id``  is the source file stem (e.g. ``my_stream``).
- ``index``   is the zero-padded candidate rank (``00``, ``01``, …).
- ``slug``    is ``<start_s>s-<end_s>s`` (e.g. ``12s-18s``).

Stage B (smart face/action tracking) is out of scope for this phase.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from vod_analyzer.core.detect.audio_energy import Candidate
from vod_analyzer.core.render._models import RenderedClip

logger = logging.getLogger(__name__)

__all__ = ["PRESETS", "render_all", "render_clip"]

# ---------------------------------------------------------------------------
# Encoder presets
# ---------------------------------------------------------------------------

PRESETS: dict[str, dict[str, str]] = {
    "h264_fast": {
        "vcodec": "libx264",
        "crf": "28",
        "preset": "ultrafast",
        "acodec": "aac",
        "audio_bitrate": "128k",
    },
    "h264_balanced": {
        "vcodec": "libx264",
        "crf": "23",
        "preset": "medium",
        "acodec": "aac",
        "audio_bitrate": "192k",
    },
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _center_crop_filter(width: int, height: int) -> str:
    """Return a ``crop`` vf filter string that produces a 9:16 frame.

    For a 16:9 source the output strip is centred horizontally.  For sources
    that are already portrait (width < height * 9/16) the strip equals the
    full width and is centred vertically instead.

    Args:
        width: Source frame width in pixels.
        height: Source frame height in pixels.

    Returns:
        A filter string suitable for ``ffmpeg -vf``, e.g.
        ``"crop=135:240:92:0"``.
    """
    out_w = int(height * 9 / 16)
    if out_w <= width:
        # Landscape / square source: horizontal centre-crop
        x = (width - out_w) // 2
        return f"crop={out_w}:{height}:{x}:0"
    # Portrait source: keep full width, crop height to maintain 9:16
    out_h = int(width * 16 / 9)
    y = (height - out_h) // 2
    return f"crop={width}:{out_h}:0:{y}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_clip(
    vod_path: Path | str,
    candidate: Candidate,
    output_dir: Path | str,
    *,
    width: int,
    height: int,
    index: int = 0,
    preset: str = "h264_balanced",
    pre_padding: float = 0.5,
    post_padding: float = 0.5,
) -> RenderedClip:
    """Render a single vertical (9:16) clip from *vod_path*.

    Args:
        vod_path: Path to the source video file.
        candidate: The highlight window to extract.
        output_dir: Directory where the clip will be written.  The
            ``<vod_id>/vertical/`` subdirectory is created automatically.
        width: Source frame width in pixels (used to compute the crop filter).
        height: Source frame height in pixels.
        index: Zero-based rank used for the output filename prefix.
        preset: Encoder preset name — one of ``"h264_fast"`` or
            ``"h264_balanced"``.
        pre_padding: Seconds of footage to include before *candidate.start*.
        post_padding: Seconds of footage to include after *candidate.end*.

    Returns:
        A :class:`~vod_analyzer.core.render._models.RenderedClip` describing
        the written file.

    Raises:
        FileNotFoundError: If *vod_path* does not exist.
        ValueError: If *preset* is not a known preset name, or if *width* or
            *height* are not positive.
        subprocess.CalledProcessError: If ffmpeg exits with a non-zero status.
    """
    vod_path = Path(vod_path)
    if not vod_path.exists():
        raise FileNotFoundError(f"VOD not found: {vod_path}")
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}. Choose from: {list(PRESETS)}")
    if width <= 0 or height <= 0:
        raise ValueError(f"width and height must be positive, got {width}x{height}")

    enc = PRESETS[preset]
    start = max(0.0, candidate.start - pre_padding)
    end = candidate.end + post_padding
    duration = end - start

    vod_id = vod_path.stem
    slug = f"{int(candidate.start)}s-{int(candidate.end)}s"
    clip_name = f"{index:02d}_{slug}.mp4"
    clip_dir = Path(output_dir) / vod_id / "vertical"
    clip_dir.mkdir(parents=True, exist_ok=True)
    clip_path = clip_dir / clip_name

    vf = _center_crop_filter(width, height)

    logger.debug(
        "Rendering vertical clip %s: %.2f-%.2f s (preset=%s, vf=%s)",
        clip_name,
        start,
        end,
        preset,
        vf,
    )

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(vod_path),
            "-t",
            f"{duration:.3f}",
            "-vf",
            vf,
            "-vcodec",
            enc["vcodec"],
            "-crf",
            enc["crf"],
            "-preset",
            enc["preset"],
            "-acodec",
            enc["acodec"],
            "-b:a",
            enc["audio_bitrate"],
            str(clip_path),
        ],
        capture_output=True,
        check=True,
    )

    return RenderedClip(path=clip_path, candidate=candidate, preset=preset)


def render_all(
    vod_path: Path | str,
    candidates: list[Candidate],
    output_dir: Path | str,
    *,
    width: int,
    height: int,
    preset: str = "h264_balanced",
    pre_padding: float = 0.5,
    post_padding: float = 0.5,
) -> list[RenderedClip]:
    """Render one vertical (9:16) clip per candidate.

    Args:
        vod_path: Path to the source video file.
        candidates: List of highlight candidates (order is preserved).
        output_dir: Root output directory.
        width: Source frame width in pixels.
        height: Source frame height in pixels.
        preset: Encoder preset name for all clips.
        pre_padding: Seconds of footage before each candidate start.
        post_padding: Seconds of footage after each candidate end.

    Returns:
        List of :class:`~vod_analyzer.core.render._models.RenderedClip` in
        the same order as *candidates*.  Empty when *candidates* is empty.
    """
    clips: list[RenderedClip] = []
    for i, candidate in enumerate(candidates):
        clip = render_clip(
            vod_path,
            candidate,
            output_dir,
            width=width,
            height=height,
            index=i,
            preset=preset,
            pre_padding=pre_padding,
            post_padding=post_padding,
        )
        clips.append(clip)
        logger.info("Rendered %s", clip.path.name)
    return clips
