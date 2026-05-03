"""Horizontal (16:9) clip renderer.

Takes a source VOD and a list of :class:`~vod_analyzer.core.detect.audio_energy.Candidate`
windows and writes one MP4 clip per candidate to an output directory.

Output layout
-------------
::

    output/<vod_id>/horizontal/<index>_<slug>.mp4

Where:
- ``vod_id``  is the source file stem (e.g. ``my_stream``).
- ``index``   is the zero-padded candidate rank (``00``, ``01``, …).
- ``slug``    is ``<start_s>s-<end_s>s`` (e.g. ``12s-18s``).

Encoder presets
---------------
Two presets are provided out of the box:

``h264_fast``
    CRF 28, ``ultrafast`` preset — largest file, fastest encode.
    Good for iterating locally.

``h264_balanced``
    CRF 23, ``medium`` preset — balanced quality/size trade-off.
    Default for final output.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

from vod_analyzer.core.detect.audio_energy import Candidate

logger = logging.getLogger(__name__)

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


@dataclass(frozen=True)
class RenderedClip:
    """A clip written to disk by :func:`render_clip`.

    Attributes:
        path: Absolute path to the output MP4 file.
        candidate: The source candidate window.
        preset: Name of the encoder preset used.
    """

    path: Path
    candidate: Candidate
    preset: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def render_clip(
    vod_path: Path | str,
    candidate: Candidate,
    output_dir: Path | str,
    *,
    index: int = 0,
    preset: str = "h264_balanced",
    pre_padding: float = 0.5,
    post_padding: float = 0.5,
) -> RenderedClip:
    """Render a single horizontal clip from *vod_path*.

    Args:
        vod_path: Path to the source video file.
        candidate: The highlight window to extract.
        output_dir: Directory where the clip will be written.  The
            ``<vod_id>/horizontal/`` subdirectory is created automatically.
        index: Zero-based rank used for the output filename prefix.
        preset: Encoder preset name — one of ``"h264_fast"`` or
            ``"h264_balanced"``.
        pre_padding: Seconds of footage to include before *candidate.start*.
        post_padding: Seconds of footage to include after *candidate.end*.

    Returns:
        A :class:`RenderedClip` describing the written file.

    Raises:
        FileNotFoundError: If *vod_path* does not exist.
        ValueError: If *preset* is not a known preset name.
        subprocess.CalledProcessError: If ffmpeg exits with a non-zero status.
    """
    vod_path = Path(vod_path)
    if not vod_path.exists():
        raise FileNotFoundError(f"VOD not found: {vod_path}")
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset {preset!r}. Choose from: {list(PRESETS)}")

    enc = PRESETS[preset]
    start = max(0.0, candidate.start - pre_padding)
    end = candidate.end + post_padding
    duration = end - start

    # Build output path: output/<vod_id>/horizontal/<index>_<start>s-<end>s.mp4
    vod_id = vod_path.stem
    slug = f"{int(candidate.start)}s-{int(candidate.end)}s"
    clip_name = f"{index:02d}_{slug}.mp4"
    clip_dir = Path(output_dir) / vod_id / "horizontal"
    clip_dir.mkdir(parents=True, exist_ok=True)
    clip_path = clip_dir / clip_name

    logger.debug(
        "Rendering clip %s: %.2f-%.2f s (preset=%s)",
        clip_name,
        start,
        end,
        preset,
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
    preset: str = "h264_balanced",
    pre_padding: float = 0.5,
    post_padding: float = 0.5,
) -> list[RenderedClip]:
    """Render one horizontal clip per candidate, sorted by score.

    Args:
        vod_path: Path to the source video file.
        candidates: List of highlight candidates (order is preserved).
        output_dir: Root output directory.
        preset: Encoder preset name for all clips.
        pre_padding: Seconds of footage before each candidate start.
        post_padding: Seconds of footage after each candidate end.

    Returns:
        List of :class:`RenderedClip` in the same order as *candidates*.
        Empty when *candidates* is empty.
    """
    clips: list[RenderedClip] = []
    for i, candidate in enumerate(candidates):
        clip = render_clip(
            vod_path,
            candidate,
            output_dir,
            index=i,
            preset=preset,
            pre_padding=pre_padding,
            post_padding=post_padding,
        )
        clips.append(clip)
        logger.info("Rendered %s", clip.path.name)
    return clips
