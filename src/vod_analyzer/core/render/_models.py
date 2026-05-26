"""Shared data models for the render layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from vod_analyzer.core.detect.audio_energy import Candidate


@dataclass(frozen=True)
class RenderedClip:
    """A clip written to disk by a renderer.

    Attributes:
        path: Absolute path to the output MP4 file.
        candidate: The source candidate window.
        preset: Name of the encoder preset used.
    """

    path: Path
    candidate: Candidate
    preset: str
