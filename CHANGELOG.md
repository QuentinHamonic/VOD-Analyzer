# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.5] — 2026-05-27

### Added

- `core.transcribe` package: `ASRBackend` Protocol, `TranscriptSegment` and
  `Word` frozen dataclasses, and `FasterWhisperBackend` wrapping
  `faster-whisper`.
- Configurable model size (`--model`), language (`--language`), device
  (`--device`), quantisation (`--compute-type`), and VAD pre-filter
  (`--vad/--no-vad`).
- CLI command `vod-analyzer transcribe <vod>` with optional `--output-json`
  for machine-readable output.
- `faster-whisper>=1.0` added as a runtime dependency.
- 19 unit tests (all mocked — no model download required in CI).

## [0.0.4-post1] — 2026-05-27

### Added

- Multi-track audio support: `AudioTrackInfo` dataclass and `audio_tracks`
  field on `VodMetadata` expose all audio streams with codec, sample rate,
  channels and layout. Convenience properties `audio_codec` and `sample_rate`
  preserve backward compatibility.
- `extract_audio()` gains an `audio_track` parameter (default: ``0``) mapped
  to ffmpeg's ``-map 0:a:N`` to target any audio stream.
- `--audio-track` option on both `vod-analyzer ingest` and
  `vod-analyzer clips horizontal`. The `ingest` command now lists all
  available audio tracks and marks the selected one.

## [0.0.4] — 2026-05-03

### Added

- `core.render.horizontal` module: `render_clip()` and `render_all()` — ffmpeg-based
  horizontal clip extraction with `h264_fast` and `h264_balanced` presets and
  configurable pre/post padding.
- `RenderedClip` dataclass carrying path, source candidate and preset used.
- CLI command `vod-analyzer clips horizontal <vod>` chaining ingestion, audio
  energy detection and clip rendering end-to-end.
- 15 unit tests covering output layout, presets, error paths and multi-clip rendering.

## [0.0.3] — 2026-05-03

### Added

- `core.detect.audio_energy` module: `Candidate` dataclass and `detect()`
  function — RMS-energy-based highlight detection with configurable window,
  hop, threshold, and merging logic.
- `librosa>=0.10` added as a runtime dependency.
- 17 unit tests on synthetic WAV signals (silence, single peak, multi-peak).

## [0.0.2] — 2026-05-03

### Added

- `core.ingest` module: `VodMetadata` dataclass, `load_vod(path)` (ffprobe
  metadata extraction) and `extract_audio()` (mono 16-bit WAV via ffmpeg).
- CLI command `vod-analyzer ingest <path>` (Typer) displaying metadata and
  extracting audio, with `--sample-rate`, `--audio-out`, and `--verbose` flags.
- `typer>=0.12` added as a runtime dependency; `vod-analyzer` script entry point
  registered in `pyproject.toml`.
- Synthetic ffmpeg fixture (`tests/conftest.py`) and 14 unit tests covering
  metadata parsing and audio extraction (`tests/test_ingest.py`).

## [0.0.1] — 2026-05-02

### Added

- Project skeleton: `src/vod_analyzer/{core,api,cli}` layout with `py.typed` marker.
- `pyproject.toml` (PEP 621) with metadata, dependency groups, and tool configuration.
- `ruff` (lint + format), `mypy` (strict), and `pytest` fully configured.
- `pre-commit` hooks: trailing whitespace, end-of-file fixer, YAML/TOML checks,
  large-file guard, merge-conflict detection, mixed-line-ending fix, ruff, mypy.
- Smoke test suite (`tests/test_smoke.py`) verifying the package is importable.
- `ROADMAP.md` describing the twelve-phase development plan.
- MIT `LICENSE`.
- `.gitattributes` with LF enforcement and binary patterns for media and model files.
