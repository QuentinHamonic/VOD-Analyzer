# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- GitHub Actions CI workflow (lint, type-check, tests on Python 3.11 and 3.12).
- `CHANGELOG.md` in Keep-a-Changelog format.
- Expanded `README.md` with quickstart, usage, and roadmap link.

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
