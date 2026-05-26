"""Tests for :mod:`vod_analyzer.core.transcribe`.

Strategy
--------
faster-whisper requires downloading model weights (145 MB+ for "base") which
is unsuitable for CI.  All tests here mock ``WhisperModel`` so that:

- The backend construction, parameter forwarding, and output parsing are
  fully covered without network or GPU.
- The Protocol contract is validated against a lightweight stub.
- ``TranscriptSegment`` and ``Word`` dataclasses are tested directly.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from vod_analyzer.core.transcribe._models import TranscriptSegment, Word
from vod_analyzer.core.transcribe.backend import ASRBackend
from vod_analyzer.core.transcribe.faster_whisper import FasterWhisperBackend

# ---------------------------------------------------------------------------
# Model helpers — fake faster-whisper objects
# ---------------------------------------------------------------------------


def _make_fake_word(start: float, end: float, text: str, prob: float = 0.95) -> MagicMock:
    w = MagicMock()
    w.start = start
    w.end = end
    w.word = text
    w.probability = prob
    return w


def _make_fake_segment(
    start: float, end: float, text: str, words: list[MagicMock] | None = None
) -> MagicMock:
    seg = MagicMock()
    seg.start = start
    seg.end = end
    seg.text = text
    seg.words = words or []
    return seg


def _make_fake_info(language: str = "en", probability: float = 0.99) -> MagicMock:
    info = MagicMock()
    info.language = language
    info.language_probability = probability
    return info


# ---------------------------------------------------------------------------
# TranscriptSegment and Word — unit tests (no mocking needed)
# ---------------------------------------------------------------------------


class TestTranscriptSegment:
    def test_fields_are_stored(self) -> None:
        seg = TranscriptSegment(start=1.0, end=3.5, text="Hello world")
        assert seg.start == 1.0
        assert seg.end == 3.5
        assert seg.text == "Hello world"

    def test_words_defaults_to_empty_tuple(self) -> None:
        seg = TranscriptSegment(start=0.0, end=1.0, text="Hi")
        assert seg.words == ()

    def test_words_stored_correctly(self) -> None:
        w = Word(start=0.1, end=0.4, text="Hi", probability=0.98)
        seg = TranscriptSegment(start=0.0, end=1.0, text="Hi", words=(w,))
        assert len(seg.words) == 1
        assert seg.words[0].text == "Hi"

    def test_is_frozen(self) -> None:
        seg = TranscriptSegment(start=0.0, end=1.0, text="Hi")
        with pytest.raises(dataclasses.FrozenInstanceError):
            seg.text = "changed"  # type: ignore[misc]


class TestWord:
    def test_fields_are_stored(self) -> None:
        w = Word(start=0.1, end=0.4, text=" hello", probability=0.97)
        assert w.start == 0.1
        assert w.end == 0.4
        assert w.text == " hello"
        assert w.probability == 0.97

    def test_is_frozen(self) -> None:
        w = Word(start=0.0, end=0.1, text="x", probability=1.0)
        with pytest.raises(dataclasses.FrozenInstanceError):
            w.text = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ASRBackend Protocol
# ---------------------------------------------------------------------------


class TestASRBackendProtocol:
    def test_stub_satisfies_protocol(self) -> None:
        """A minimal stub with the right signature is a valid ASRBackend."""

        class StubBackend:
            def transcribe(
                self,
                wav_path: Path,
                *,
                language: str | None = None,
                vad_filter: bool = False,
            ) -> list[TranscriptSegment]:
                return []

        assert isinstance(StubBackend(), ASRBackend)

    def test_faster_whisper_backend_satisfies_protocol(self) -> None:
        with patch("vod_analyzer.core.transcribe.faster_whisper.WhisperModel"):
            backend = FasterWhisperBackend()
        assert isinstance(backend, ASRBackend)


# ---------------------------------------------------------------------------
# FasterWhisperBackend — unit tests with mocked WhisperModel
# ---------------------------------------------------------------------------


class TestFasterWhisperBackend:
    @pytest.fixture
    def backend(self) -> FasterWhisperBackend:
        with patch("vod_analyzer.core.transcribe.faster_whisper.WhisperModel"):
            return FasterWhisperBackend(model_size="tiny", device="cpu", compute_type="int8")

    def test_stores_init_params(self, backend: FasterWhisperBackend) -> None:
        assert backend.model_size == "tiny"
        assert backend.device == "cpu"
        assert backend.compute_type == "int8"

    def test_transcribe_returns_segment_list(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")  # dummy content — not actually read

        fake_seg = _make_fake_segment(0.0, 2.0, "  Hello world  ")
        fake_info = _make_fake_info()
        backend._model.transcribe.return_value = (iter([fake_seg]), fake_info)

        result = backend.transcribe(wav)

        assert len(result) == 1
        assert isinstance(result[0], TranscriptSegment)

    def test_transcribe_strips_whitespace(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        fake_seg = _make_fake_segment(0.0, 2.0, "  Hello world  ")
        backend._model.transcribe.return_value = (iter([fake_seg]), _make_fake_info())

        result = backend.transcribe(wav)

        assert result[0].text == "Hello world"

    def test_transcribe_preserves_timestamps(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        fake_seg = _make_fake_segment(1.5, 4.2, "Test")
        backend._model.transcribe.return_value = (iter([fake_seg]), _make_fake_info())

        result = backend.transcribe(wav)

        assert result[0].start == 1.5
        assert result[0].end == 4.2

    def test_transcribe_parses_word_timestamps(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        words = [_make_fake_word(0.1, 0.4, " hello"), _make_fake_word(0.5, 0.9, " world")]
        fake_seg = _make_fake_segment(0.0, 1.0, "hello world", words=words)
        backend._model.transcribe.return_value = (iter([fake_seg]), _make_fake_info())

        result = backend.transcribe(wav)

        assert len(result[0].words) == 2
        assert result[0].words[0].text == " hello"
        assert result[0].words[1].probability == 0.95

    def test_transcribe_empty_audio_returns_empty_list(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        backend._model.transcribe.return_value = (iter([]), _make_fake_info())

        result = backend.transcribe(wav)

        assert result == []

    def test_transcribe_passes_language(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        backend._model.transcribe.return_value = (iter([]), _make_fake_info("fr"))

        backend.transcribe(wav, language="fr")

        call_kwargs = backend._model.transcribe.call_args.kwargs
        assert call_kwargs["language"] == "fr"

    def test_transcribe_passes_vad_filter(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        backend._model.transcribe.return_value = (iter([]), _make_fake_info())

        backend.transcribe(wav, vad_filter=True)

        call_kwargs = backend._model.transcribe.call_args.kwargs
        assert call_kwargs["vad_filter"] is True

    def test_transcribe_requests_word_timestamps(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        backend._model.transcribe.return_value = (iter([]), _make_fake_info())

        backend.transcribe(wav)

        call_kwargs = backend._model.transcribe.call_args.kwargs
        assert call_kwargs["word_timestamps"] is True

    def test_transcribe_raises_when_file_not_found(self, backend: FasterWhisperBackend) -> None:
        with pytest.raises(FileNotFoundError):
            backend.transcribe(Path("/nonexistent/audio.wav"))

    def test_multiple_segments_preserved_in_order(
        self, backend: FasterWhisperBackend, tmp_path: Path
    ) -> None:
        wav = tmp_path / "audio.wav"
        wav.write_bytes(b"RIFF")

        segs = [
            _make_fake_segment(0.0, 2.0, "First"),
            _make_fake_segment(2.5, 4.0, "Second"),
            _make_fake_segment(5.0, 7.5, "Third"),
        ]
        backend._model.transcribe.return_value = (iter(segs), _make_fake_info())

        result = backend.transcribe(wav)

        assert len(result) == 3
        assert [r.text for r in result] == ["First", "Second", "Third"]
