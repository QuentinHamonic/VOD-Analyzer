"""Shared pytest fixtures for the VOD Analyzer test suite.

Fixtures defined here are automatically available to every test module without
explicit imports (pytest collects conftest.py files up the directory tree).

Session-scoped fixtures (``scope="session"``) are created once per test run
and shared across all tests that request them — ideal for expensive operations
like generating synthetic video files with ffmpeg.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def tiny_vod(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Generate a synthetic 2-second 320x240 test video with audio.

    The video is created with ffmpeg's built-in ``testsrc`` source (a
    coloured test pattern) and a 440 Hz sine wave audio track, encoded as
    H.264 + AAC in an MP4 container.

    Generating it once per session (``scope="session"``) keeps the test
    suite fast: subsequent tests that need the file just reuse the same path.

    Returns:
        Path to the generated ``tiny.mp4`` file inside a temporary directory.
    """
    out: Path = tmp_path_factory.mktemp("fixtures") / "tiny.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            # Video: 2 s test pattern, 320x240, 25 fps
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=2:size=320x240:rate=25",
            # Audio: 2 s 440 Hz sine wave
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            str(out),
        ],
        check=True,
        capture_output=True,
    )
    return out
