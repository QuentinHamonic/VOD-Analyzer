"""RMS-energy-based highlight detector.

This is the first and simplest detector in the pipeline. It works directly on
the mono WAV produced by :func:`vod_analyzer.core.ingest.extract_audio` and
requires no network access, no GPU, and no heavy model weights.

Algorithm
---------
1. Load the WAV with ``librosa``.
2. Compute the root-mean-square (RMS) energy over sliding windows.
3. Normalise the RMS curve to [0, 1].
4. Select windows whose normalised score exceeds *threshold*.
5. Merge overlapping windows and return the top-*max_candidates* results
   sorted by score descending.

The detector is intentionally naive — it serves as the baseline that later
detectors (speech, LLM scoring, vision) will complement and outperform.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Candidate:
    """A highlight candidate window produced by a detector.

    Attributes:
        start: Start time in seconds.
        end: End time in seconds.
        score: Normalised highlight score in [0, 1]. Higher is better.
        source: Identifier of the detector that produced this candidate
            (e.g. ``"audio_energy"``).
    """

    start: float
    end: float
    score: float
    source: str

    def __post_init__(self) -> None:
        if self.start < 0:
            raise ValueError(f"start must be >= 0, got {self.start}")
        if self.end <= self.start:
            raise ValueError(f"end ({self.end}) must be > start ({self.start})")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0, 1], got {self.score}")


def detect(
    audio_path: Path | str,
    *,
    window_sec: float = 2.0,
    hop_sec: float = 0.5,
    threshold: float = 0.5,
    min_duration: float = 1.0,
    max_candidates: int = 10,
) -> list[Candidate]:
    """Detect highlight candidates using RMS energy.

    Args:
        audio_path: Path to the mono WAV file produced by
            :func:`~vod_analyzer.core.ingest.extract_audio`.
        window_sec: Duration of each analysis window in seconds.
        hop_sec: Step between consecutive windows in seconds.
        threshold: Minimum normalised RMS score (0-1) for a window to be
            considered a candidate. Lower values yield more candidates.
        min_duration: Minimum duration in seconds for a merged candidate
            window. Shorter merged windows are discarded.
        max_candidates: Maximum number of candidates to return.

    Returns:
        List of :class:`Candidate` objects sorted by score descending,
        at most *max_candidates* long. Returns an empty list when no
        window exceeds *threshold*.

    Raises:
        FileNotFoundError: If *audio_path* does not exist.
        ValueError: If *window_sec* or *hop_sec* are non-positive.
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")
    if window_sec <= 0:
        raise ValueError(f"window_sec must be > 0, got {window_sec}")
    if hop_sec <= 0:
        raise ValueError(f"hop_sec must be > 0, got {hop_sec}")

    logger.debug("Loading audio: %s", audio_path)
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)

    # Convert durations to samples
    frame_length = int(window_sec * sr)
    hop_length = int(hop_sec * sr)

    # Compute RMS energy for each frame
    rms: np.ndarray = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]

    if rms.max() == 0:
        logger.debug("Audio is silent — no candidates")
        return []

    # Normalise to [0, 1]
    rms_norm: np.ndarray = rms / rms.max()

    # Map frame indices to timestamps
    times: np.ndarray = librosa.frames_to_time(
        np.arange(len(rms_norm)), sr=sr, hop_length=hop_length
    )

    # Collect windows above threshold
    raw: list[Candidate] = []
    for t, score in zip(times, rms_norm, strict=False):
        if score >= threshold:
            end = float(min(t + window_sec, len(y) / sr))
            raw.append(
                Candidate(
                    start=float(t),
                    end=end,
                    score=float(score),
                    source="audio_energy",
                )
            )

    if not raw:
        return []

    # Merge overlapping windows, keeping the highest score
    merged = _merge(raw, min_duration=min_duration)

    # Sort by score descending and cap results
    return sorted(merged, key=lambda c: c.score, reverse=True)[:max_candidates]


def _merge(candidates: list[Candidate], *, min_duration: float) -> list[Candidate]:
    """Merge overlapping or adjacent candidate windows.

    Consecutive windows that overlap are collapsed into a single window
    spanning the full range, with the maximum score of the group.
    Windows shorter than *min_duration* after merging are discarded.
    """
    if not candidates:
        return []

    sorted_cands = sorted(candidates, key=lambda c: c.start)
    merged: list[Candidate] = []
    cur_start = sorted_cands[0].start
    cur_end = sorted_cands[0].end
    cur_score = sorted_cands[0].score

    for cand in sorted_cands[1:]:
        if cand.start <= cur_end:
            # Overlapping — extend and take max score
            cur_end = max(cur_end, cand.end)
            cur_score = max(cur_score, cand.score)
        else:
            if cur_end - cur_start >= min_duration:
                merged.append(
                    Candidate(
                        start=cur_start,
                        end=cur_end,
                        score=cur_score,
                        source="audio_energy",
                    )
                )
            cur_start = cand.start
            cur_end = cand.end
            cur_score = cand.score

    if cur_end - cur_start >= min_duration:
        merged.append(
            Candidate(
                start=cur_start,
                end=cur_end,
                score=cur_score,
                source="audio_energy",
            )
        )

    return merged
