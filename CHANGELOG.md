# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
