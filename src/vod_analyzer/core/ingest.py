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
class AudioTrackInfo:
    """Metadata for a single audio stream inside a VOD file.

    Attributes:
        index: Zero-based index among audio streams (``0:a:0``, ``0:a:1``, …).
        codec: Short codec name as reported by ffprobe (e.g. ``"aac"``).
        sample_rate: Sample rate in Hz.
        channels: Number of audio channels (1 = mono, 2 = stereo, …).
        channel_layout: Layout string as reported by ffprobe
            (e.g. ``"stereo"``, ``"5.1"``). Empty string when not reported.
    """

    index: int
    codec: str
    sample_rate: int
    channels: int
    channel_layout: str


@dataclass(frozen=True)
class VodMetadata:
    """Metadata extracted from a VOD file via ``ffprobe``.

    Attributes:
        path: Absolute path to the source file.
        duration: Total duration in seconds.
        width: Frame width in pixels (0 if no video stream).
        height: Frame height in pixels (0 if no video stream).
        fps: Average frame rate (0.0 if no video stream).
        video_codec: Short codec name of the first video stream
            (e.g. ``"h264"``). Empty string when no video stream exists.
        audio_tracks: All audio streams found in the file, in stream order.
            Empty tuple for video-only files.
    """

    path: Path
    duration: float
    width: int
    height: int
    fps: float
    video_codec: str
    audio_tracks: tuple[AudioTrackInfo, ...]

    # ------------------------------------------------------------------
    # Convenience properties (backwards-compatible shortcuts)
    # ------------------------------------------------------------------

    @property
    def audio_codec(self) -> str:
        """Codec of the first audio track, or empty string."""
        return self.audio_tracks[0].codec if self.audio_tracks else ""

    @property
    def sample_rate(self) -> int:
        """Sample rate of the first audio track in Hz, or 0."""
        return self.audio_tracks[0].sample_rate if self.audio_tracks else 0


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
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

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

    audio_tracks = tuple(
        AudioTrackInfo(
            index=i,
            codec=str(s.get("codec_name", "")),
            sample_rate=int(str(s.get("sample_rate", 0))),
            channels=int(str(s.get("channels", 0))),
            channel_layout=str(s.get("channel_layout", "")),
        )
        for i, s in enumerate(audio_streams)
    )

    return VodMetadata(
        path=path,
        duration=duration,
        width=width,
        height=height,
        fps=fps,
        video_codec=video_codec,
        audio_tracks=audio_tracks,
    )


def extract_audio(
    metadata: VodMetadata,
    *,
    audio_track: int = 0,
    sample_rate: int = 16_000,
    output_path: Path | None = None,
) -> Path:
    """Extract one audio track from *metadata.path* to a mono WAV file.

    The output is always mono PCM 16-bit signed little-endian (``pcm_s16le``),
    which is the format expected by all downstream audio analysis modules
    (librosa, faster-whisper, silero-vad, …).

    Args:
        metadata: Metadata object returned by :func:`load_vod`.
        audio_track: Zero-based index of the audio stream to extract
            (default: ``0``). Use :attr:`VodMetadata.audio_tracks` to list
            available tracks before choosing.
        sample_rate: Target sample rate in Hz (default: 16 000).
        output_path: Destination WAV path. When *None*, a temporary file is
            created; the caller is responsible for deleting it.

    Returns:
        Path to the extracted WAV file.

    Raises:
        IndexError: If *audio_track* is out of range for this file.
        subprocess.CalledProcessError: If ``ffmpeg`` exits with a non-zero
            status.
    """
    if metadata.audio_tracks and audio_track >= len(metadata.audio_tracks):
        raise IndexError(
            f"audio_track={audio_track} is out of range "
            f"(file has {len(metadata.audio_tracks)} audio track(s))."
        )

    if output_path is None:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            output_path = Path(tmp.name)

    logger.debug(
        "Extracting audio track %d: %s -> %s (sr=%d Hz)",
        audio_track,
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
            "-map",
            f"0:a:{audio_track}",
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
