"""Tests for :mod:`vod_analyzer.core.detect.audio_energy`.

Synthetic WAV files are generated with the standard-library ``wave`` module —
no extra audio dependency needed. Each fixture models a specific scenario:

- ``silent_wav``  — flat zero signal  → no candidates expected.
- ``peak_wav``    — loud burst in the centre of an otherwise quiet clip
                    → exactly one candidate expected.
- ``multi_wav``   — three distinct bursts separated by silence
                    → multiple candidates expected.
"""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pytest

from vod_analyzer.core.detect.audio_energy import Candidate, detect

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_RATE = 16_000  # Hz


def _write_wav(path: Path, samples: list[float]) -> Path:
    """Write a list of float samples (range [-1, 1]) to a 16-bit mono WAV."""
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(SAMPLE_RATE)
        for s in samples:
            clamped = max(-1.0, min(1.0, s))
            wf.writeframes(struct.pack("<h", int(clamped * 32767)))
    return path


def _silence(duration_sec: float) -> list[float]:
    return [0.0] * int(duration_sec * SAMPLE_RATE)


def _sine(duration_sec: float, amplitude: float = 0.9, freq: float = 440.0) -> list[float]:
    n = int(duration_sec * SAMPLE_RATE)
    return [amplitude * math.sin(2 * math.pi * freq * i / SAMPLE_RATE) for i in range(n)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def silent_wav(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """10 s of pure silence."""
    out = tmp_path_factory.mktemp("audio") / "silent.wav"
    return _write_wav(out, _silence(10.0))


@pytest.fixture(scope="module")
def peak_wav(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """10 s clip: 4 s silence, 2 s loud tone, 4 s silence."""
    out = tmp_path_factory.mktemp("audio") / "peak.wav"
    samples = _silence(4.0) + _sine(2.0, amplitude=0.9) + _silence(4.0)
    return _write_wav(out, samples)


@pytest.fixture(scope="module")
def multi_wav(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """20 s clip with three bursts separated by silence."""
    out = tmp_path_factory.mktemp("audio") / "multi.wav"
    samples = (
        _silence(1.0)
        + _sine(2.0, amplitude=0.9)  # burst 1 @ ~1 s
        + _silence(3.0)
        + _sine(2.0, amplitude=0.7)  # burst 2 @ ~6 s
        + _silence(3.0)
        + _sine(2.0, amplitude=0.8)  # burst 3 @ ~11 s
        + _silence(1.0)
    )
    return _write_wav(out, samples)


# ---------------------------------------------------------------------------
# Candidate dataclass
# ---------------------------------------------------------------------------


class TestCandidate:
    def test_valid_candidate(self) -> None:
        c = Candidate(start=0.0, end=2.0, score=0.8, source="audio_energy")
        assert c.start == 0.0
        assert c.end == 2.0

    def test_negative_start_raises(self) -> None:
        with pytest.raises(ValueError, match="start"):
            Candidate(start=-1.0, end=2.0, score=0.5, source="audio_energy")

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="end"):
            Candidate(start=3.0, end=1.0, score=0.5, source="audio_energy")

    def test_score_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="score"):
            Candidate(start=0.0, end=1.0, score=1.5, source="audio_energy")


# ---------------------------------------------------------------------------
# detect() — error paths
# ---------------------------------------------------------------------------


class TestDetectErrors:
    def test_file_not_found_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            detect(Path("/nonexistent/audio.wav"))

    def test_invalid_window_raises(self, silent_wav: Path) -> None:
        with pytest.raises(ValueError, match="window_sec"):
            detect(silent_wav, window_sec=0)

    def test_invalid_hop_raises(self, silent_wav: Path) -> None:
        with pytest.raises(ValueError, match="hop_sec"):
            detect(silent_wav, hop_sec=-1.0)


# ---------------------------------------------------------------------------
# detect() — happy path
# ---------------------------------------------------------------------------


class TestDetectSilence:
    def test_silent_audio_returns_empty(self, silent_wav: Path) -> None:
        assert detect(silent_wav) == []


class TestDetectSinglePeak:
    def test_returns_at_least_one_candidate(self, peak_wav: Path) -> None:
        candidates = detect(peak_wav, threshold=0.5)
        assert len(candidates) >= 1

    def test_candidates_are_candidate_instances(self, peak_wav: Path) -> None:
        for c in detect(peak_wav, threshold=0.5):
            assert isinstance(c, Candidate)

    def test_source_is_audio_energy(self, peak_wav: Path) -> None:
        for c in detect(peak_wav, threshold=0.5):
            assert c.source == "audio_energy"

    def test_candidate_covers_peak_region(self, peak_wav: Path) -> None:
        candidates = detect(peak_wav, threshold=0.5)
        assert any(c.start <= 5.0 and c.end >= 5.0 for c in candidates)

    def test_sorted_by_score_descending(self, peak_wav: Path) -> None:
        candidates = detect(peak_wav, threshold=0.3)
        scores = [c.score for c in candidates]
        assert scores == sorted(scores, reverse=True)

    def test_scores_in_unit_interval(self, peak_wav: Path) -> None:
        for c in detect(peak_wav, threshold=0.3):
            assert 0.0 <= c.score <= 1.0


class TestDetectMultiplePeaks:
    def test_detects_multiple_candidates(self, multi_wav: Path) -> None:
        candidates = detect(multi_wav, threshold=0.4)
        assert len(candidates) >= 2

    def test_max_candidates_respected(self, multi_wav: Path) -> None:
        candidates = detect(multi_wav, threshold=0.1, max_candidates=2)
        assert len(candidates) <= 2

    def test_very_high_threshold_yields_fewer_results(self, multi_wav: Path) -> None:
        """A threshold near 1.0 should return fewer candidates than 0.5."""
        normal = detect(multi_wav, threshold=0.5)
        strict = detect(multi_wav, threshold=0.99)
        assert len(normal) >= len(strict)
