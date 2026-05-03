"""Tests for :mod:`vod_analyzer.core.ingest`.

Coverage targets:
- :func:`load_vod` — happy path, edge cases, error paths.
- :func:`extract_audio` — output file, custom sample rate, custom path,
  audio track selection.

The ``tiny_vod`` fixture (defined in ``conftest.py``) provides a synthetic
2-second MP4 generated once per session via ffmpeg.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from vod_analyzer.core.ingest import AudioTrackInfo, VodMetadata, extract_audio, load_vod


class TestLoadVod:
    """Unit tests for :func:`load_vod`."""

    def test_returns_metadata_instance(self, tiny_vod: Path) -> None:
        assert isinstance(load_vod(tiny_vod), VodMetadata)

    def test_duration_approximately_two_seconds(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        assert 1.8 <= meta.duration <= 2.2

    def test_resolution(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        assert meta.width == 320
        assert meta.height == 240

    def test_fps(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        assert abs(meta.fps - 25.0) < 0.1

    def test_video_codec(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        assert meta.video_codec == "h264"

    def test_audio_tracks_is_tuple(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        assert isinstance(meta.audio_tracks, tuple)

    def test_has_one_audio_track(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        assert len(meta.audio_tracks) == 1

    def test_audio_track_info(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        track = meta.audio_tracks[0]
        assert isinstance(track, AudioTrackInfo)
        assert track.index == 0
        assert track.codec == "aac"

    def test_audio_codec_property(self, tiny_vod: Path) -> None:
        """audio_codec convenience property returns first track codec."""
        meta = load_vod(tiny_vod)
        assert meta.audio_codec == meta.audio_tracks[0].codec

    def test_sample_rate_property(self, tiny_vod: Path) -> None:
        """sample_rate convenience property returns first track sample rate."""
        meta = load_vod(tiny_vod)
        assert meta.sample_rate == meta.audio_tracks[0].sample_rate

    def test_path_stored_on_metadata(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        assert meta.path == tiny_vod

    def test_accepts_string_path(self, tiny_vod: Path) -> None:
        meta = load_vod(str(tiny_vod))
        assert isinstance(meta, VodMetadata)

    def test_file_not_found_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_vod(Path("/nonexistent/does_not_exist.mp4"))


class TestExtractAudio:
    """Unit tests for :func:`extract_audio`."""

    def test_returns_wav_path(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        wav = extract_audio(meta)
        try:
            assert wav.suffix == ".wav"
            assert wav.exists()
        finally:
            wav.unlink(missing_ok=True)

    def test_custom_output_path(self, tiny_vod: Path, tmp_path: Path) -> None:
        meta = load_vod(tiny_vod)
        out = tmp_path / "audio.wav"
        wav = extract_audio(meta, output_path=out)
        assert wav == out
        assert out.exists()

    def test_default_sample_rate_is_16k(self, tiny_vod: Path, tmp_path: Path) -> None:
        meta = load_vod(tiny_vod)
        out = tmp_path / "audio_16k.wav"
        extract_audio(meta, output_path=out)
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(out)],
            capture_output=True,
            text=True,
            check=True,
        )
        info: dict[str, list[dict[str, str]]] = json.loads(result.stdout)
        assert info["streams"][0]["sample_rate"] == "16000"

    def test_custom_sample_rate(self, tiny_vod: Path, tmp_path: Path) -> None:
        meta = load_vod(tiny_vod)
        out = tmp_path / "audio_8k.wav"
        extract_audio(meta, sample_rate=8_000, output_path=out)
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(out)],
            capture_output=True,
            text=True,
            check=True,
        )
        info2: dict[str, list[dict[str, str]]] = json.loads(result.stdout)
        assert info2["streams"][0]["sample_rate"] == "8000"

    def test_output_is_mono(self, tiny_vod: Path, tmp_path: Path) -> None:
        meta = load_vod(tiny_vod)
        out = tmp_path / "audio_mono.wav"
        extract_audio(meta, output_path=out)
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(out)],
            capture_output=True,
            text=True,
            check=True,
        )
        info3: dict[str, list[dict[str, int]]] = json.loads(result.stdout)
        assert info3["streams"][0]["channels"] == 1

    def test_explicit_track_zero(self, tiny_vod: Path, tmp_path: Path) -> None:
        meta = load_vod(tiny_vod)
        out = tmp_path / "track0.wav"
        extract_audio(meta, audio_track=0, output_path=out)
        assert out.exists()

    def test_out_of_range_track_raises(self, tiny_vod: Path) -> None:
        meta = load_vod(tiny_vod)
        with pytest.raises(IndexError):
            extract_audio(meta, audio_track=99)
