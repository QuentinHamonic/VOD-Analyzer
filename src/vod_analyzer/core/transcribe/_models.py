"""Data models for the transcription layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Word:
    """A single word with timing and confidence.

    Attributes:
        start: Word start time in seconds relative to the audio file.
        end: Word end time in seconds.
        text: The word string, including surrounding whitespace as returned
            by the ASR backend.
        probability: Confidence score in [0, 1].
    """

    start: float
    end: float
    text: str
    probability: float


@dataclass(frozen=True)
class TranscriptSegment:
    """A transcribed segment (sentence or clause) with timestamps.

    Attributes:
        start: Segment start time in seconds relative to the audio file.
        end: Segment end time in seconds.
        text: Transcribed text, stripped of leading/trailing whitespace.
        words: Word-level timestamps when the backend supports them.
            Empty tuple when not available.
    """

    start: float
    end: float
    text: str
    words: tuple[Word, ...] = field(default_factory=tuple)
