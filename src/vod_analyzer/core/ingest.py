"""VOD ingestion: metadata extraction and audio track export.

This module is the entry point of the analysis pipeline. It wraps ``ffprobe``
(metadata) and ``ffmpeg`` (audio extraction) via :mod:`subprocess` so that the
rest of the codebase never has to parse raw ffprobe JSON or build ffmpeg
command lines by hand.

Design notes
------------
* No global state — every function is pure given its inputs.
* No ``print()`` — structured logging only (callers decide the log level).
* ffprobe / ffmpeg are called as subprocesses so that the project has no hard
  Python dependency on the system ``ffmpeg`` build; users install ffmpeg
  separately, which is the standard approach for media tooling.
"""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VodMetadata:
    """Metadata extracted from a VOD file via ``ffprobe``.

    All fields are populated from the first video and audio stream found.
    For audio-only files, *width*, *height*, *fps*, and *video_codec* are
    set to their zero / empty-string defaults.

    Attributes:
        path: Absolute path to the source file.
        duration: Total duration in seconds.
        width: Frame width in pixels (0 if no video stream).
        height: Frame height in pixels (0 if no video stream).
        fps: Average frame rate (0.0 if no video stream).
        video_codec: Short codec name as reported by ffprobe (e.g. ``"h264"``).
        audio_codec: Short codec name as reported by ffprobe (e.g. ``"aac"``).
        sample_rate: Audio sample rate in Hz (0 if no audio stream).
    """

    path: Path
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_codec: str
    sample_rate: int


def load_vod(path: Path | str) -> VodMetadata:
    """Probe *path* with ``ffprobe`` and return a :class:`VodMetadata`.

    Args:
        path: Absolute or relative path to the video / audio file.

    Returns:
        A frozen :class:`VodMetadata` populated from ffprobe output.

    Raises:
        FileNotFoundError: If *path* does not exist on disk.
        subprocess.CalledProcessError: If ``ffprobe`` exits with a non-zero
            status (e.g. unrecognised format).
        ValueError: If the file contains no recognisable streams.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"VOD not found: {path}")

    logger.debug("Probing %s", path)
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    info: dict[str, Any] = json.loads(result.stdout)
    streams: list[dict[str, Any]] = info.get("streams", [])
    fmt: dict[str, Any] = info.get("format", {})

    if not streams:
        raise ValueError(f"No recognisable streams found in: {path}")

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    duration = float(str(fmt.get("duration", 0)))

    if video is not None:
        raw_fps: str = str(video.get("avg_frame_rate", "0/1"))
        num_s, _, den_s = raw_fps.partition("/")
        den = float(den_s) if den_s else 1.0
        fps = float(num_s) / den if den else 0.0
        width = int(str(video.get("width", 0)))
        height = int(str(video.get("height", 0)))
        video_codec = str(video.get("codec_name", ""))
    else:
        fps, width, height, video_codec = 0.0, 0, 0, ""

    if audio is not None:
        audio_codec = str(audio.get("codec_name", ""))
        sample_rate = int(str(audio.get("sample_rate", 0)))
    else:
        audio_codec, sample_rate = "", 0

    return VodMetadata(
        path=path,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        video_codec=video_codec,
        audio_codec=audio_codec,
        sample_rate=sample_rate,
    )


def extract_audio(
    metadata: VodMetadata,
    *,
    sample_rate: int = 16_000,
    output_path: Path | None = None,
) -> Path:
    """Extract the audio track from *metadata.path* to a mono WAV file.

    The output is always mono PCM 16-bit signed little-endian (``pcm_s16le``),
    which is the format expected by all downstream audio analysis modules
    (librosa, faster-whisper, silero-vad, …).

    Args:
        metadata: Metadata object returned by :func:`load_vod`.
        sample_rate: Target sample rate in Hz (default: 16 000).
        output_path: Destination WAV path. When *None*, a temporary file is
            created; the caller is responsible for deleting it.

    Returns:
        Path to the extracted WAV file.

    Raises:
        subprocess.CalledProcessError: If ``ffmpeg`` exits with a non-zero
            status.
    """
    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        output_path = Path(tmp.name)

    logger.debug(
        "Extracting audio: %s → %s (sr=%d Hz)",
        metadata.path,
        output_path,
        sample_rate,
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(metadata.path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )
    return output_path
