"""FasterWhisperBackend — ASRBackend implementation using faster-whisper.

faster-whisper is a reimplementation of OpenAI Whisper using CTranslate2,
which is significantly faster and more memory-efficient than the original.

Model files are downloaded automatically on first use to the HuggingFace
cache (``~/.cache/huggingface/hub/``).  They are NOT bundled with the
package.

Typical model sizes (approximate, fp16):
    tiny    ~75 MB   — fastest, lowest accuracy
    base    ~145 MB  — good balance for short content
    small   ~460 MB  — better accuracy, still fast on CPU
    medium  ~1.5 GB  — high accuracy, slow on CPU
    large-v3 ~3 GB   — best accuracy, GPU recommended
"""

from __future__ import annotations

import logging
from pathlib import Path

from vod_analyzer.core.transcribe._models import TranscriptSegment, Word

try:
    from faster_whisper import WhisperModel
except ImportError:  # allows import without faster-whisper installed (e.g. partial CI)
    WhisperModel = None

logger = logging.getLogger(__name__)


class FasterWhisperBackend:
    """ASRBackend powered by faster-whisper.

    Args:
        model_size: Whisper model variant.  One of ``"tiny"``, ``"base"``,
            ``"small"``, ``"medium"``, ``"large-v2"``, ``"large-v3"``.
            Defaults to ``"base"``.
        device: ``"cpu"`` or ``"cuda"``.  Defaults to ``"cpu"``.
        compute_type: Quantisation type.  ``"int8"`` is the recommended
            default for CPU (fast, low RAM).  Use ``"float16"`` on GPU.
    """

    def __init__(
        self,
        model_size: str = "base",
        device: str = "cpu",
        compute_type: str = "int8",
    ) -> None:
        if WhisperModel is None:
            raise ImportError(
                "faster-whisper is required for FasterWhisperBackend. "
                "Install it with: pip install faster-whisper"
            )

        logger.debug("Loading Whisper model %r on %s (%s)", model_size, device, compute_type)
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type

    def transcribe(
        self,
        wav_path: Path,
        *,
        language: str | None = None,
        vad_filter: bool = False,
    ) -> list[TranscriptSegment]:
        """Transcribe *wav_path* using faster-whisper.

        Args:
            wav_path: Path to the audio file.  WAV mono 16 kHz works best.
            language: BCP-47 code (``"fr"``, ``"en"``, …) or ``None`` for
                auto-detection.
            vad_filter: When ``True``, use the built-in silero-VAD filter
                to skip silent segments before transcription — reduces
                hallucinations and speeds up inference on sparse audio.

        Returns:
            List of :class:`~vod_analyzer.core.transcribe._models.TranscriptSegment`
            in chronological order.

        Raises:
            FileNotFoundError: If *wav_path* does not exist.
        """
        if not wav_path.exists():
            raise FileNotFoundError(f"Audio file not found: {wav_path}")

        logger.debug("Transcribing %s (lang=%s, vad=%s)", wav_path.name, language, vad_filter)

        segments_gen, info = self._model.transcribe(
            str(wav_path),
            language=language,
            word_timestamps=True,
            vad_filter=vad_filter,
        )

        logger.debug(
            "Detected language: %s (probability=%.2f)",
            info.language,
            info.language_probability,
        )

        result: list[TranscriptSegment] = []
        for seg in segments_gen:
            words: tuple[Word, ...] = tuple(
                Word(
                    start=w.start,
                    end=w.end,
                    text=w.word,
                    probability=w.probability,
                )
                for w in (seg.words or [])
            )
            result.append(
                TranscriptSegment(
                    start=seg.start,
                    end=seg.end,
                    text=seg.text.strip(),
                    words=words,
                )
            )

        logger.info("Transcribed %d segment(s) from %s", len(result), wav_path.name)
        return result
