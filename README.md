# VOD Analyzer

[![CI](https://github.com/QuentinHamonic/VOD-Analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/QuentinHamonic/VOD-Analyzer/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

VOD Analyzer is a tool designed to analyze stream VODs and identify the best moments to turn them into short-form or long-form videos.

The goal of the project is to help content creators save time by automatically detecting highlights, funny moments, intense reactions, strong discussions, gameplay peaks, and other segments that could be reused as clips for platforms such as YouTube, TikTok, Shorts, Reels, or other video formats.

This project is built as a clean, modular, and extensible portfolio project.

---

## Quickstart

**Requirements:** Python 3.11+, Git

```bash
# Clone the repository
git clone https://github.com/QuentinHamonic/VOD-Analyzer.git
cd vod-analyzer

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Verify everything works
pytest
```

## Usage

```bash
# Ingest a VOD: display metadata and extract audio
vod-analyzer ingest <path-to-vod>

# Detect highlights and render horizontal clips
vod-analyzer clips horizontal my_stream.mp4
vod-analyzer clips horizontal my_stream.mp4 --output-dir ./out --preset h264_fast --threshold 0.4

# Detect highlights and render vertical (9:16) clips
vod-analyzer clips vertical my_stream.mp4
vod-analyzer clips vertical my_stream.mp4 --output-dir ./out --preset h264_fast --threshold 0.4
```

> Clip generation, transcription and highlight ranking are coming in later phases. See [ROADMAP.md](ROADMAP.md) for the full delivery plan.

## Development

```bash
# Run the full lint + type-check + test suite
pre-commit run --all-files
pytest

# Lint only
ruff check .

# Format
ruff format .

# Type check
mypy
```

## Roadmap

The project is split into twelve phases, each with a clear Definition of Done.
See [ROADMAP.md](ROADMAP.md) for the full plan.

| Phase | Description | Status |
|---|---|---|
| 0 | Foundations (tooling, CI, docs) | ✅ Done |
| 1 | VOD ingestion | ✅ Done |
| 2 | Audio highlight detection | ✅ Done |
| 3 | Horizontal clip generation | ✅ Done |
| 4 | Vertical clip generation | ✅ Done |
| 5 | Speech-to-text | ⏳ Planned |
| 6 | Speaker diarization | ⏳ Planned |
| 7 | LLM highlight scoring | ⏳ Planned |
| 8 | Multi-signal fusion | ⏳ Planned |
| 9 | Vision layer | ⏳ Planned |
| 10 | Stable API + mature CLI | ⏳ Planned |
| 11 | Web UI | ⏳ Planned |

## License

[MIT](LICENSE)
