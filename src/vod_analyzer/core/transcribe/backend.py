"""ASRBackend Protocol — the interface every transcription backend must satisfy."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vod_analyzer.core.transcribe._models import TranscriptSegment


@runtime_checkable
class ASRBackend(Protocol):
    """Structural interface for automatic speech recognition backends.

    Any class that implements :meth:`transcribe` with the correct signature
    satisfies this protocol — no inheritance required.
    """

    def transcribe(
        self,
        wav_path: Path,
        *,
        language: str | None = None,
        vad_filter: bool = False,
    ) -> list[TranscriptSegment]:
        """Transcribe *wav_path* and return time-aligned segments.

        Args:
            wav_path: Path to a mono WAV file (16 kHz recommended).
            language: BCP-47 language code (e.g. ``"fr"``, ``"en"``).
                Pass ``None`` to let the backend auto-detect.
            vad_filter: When ``True``, skip silent portions of the audio
                before transcription to reduce hallucinations and speed up
                inference.

        Returns:
            A list of :class:`~vod_analyzer.core.transcribe._models.TranscriptSegment`
            in chronological order.  May be empty for silent or very short
            audio.
        """
        ...
