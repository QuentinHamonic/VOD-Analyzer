"""VOD Analyzer — extract the best moments from stream VODs as ready-to-share clips.

This is the top-level package. Submodules:

- :mod:`vod_analyzer.core` — pure logic (detection, scoring, fusion, rendering).
- :mod:`vod_analyzer.api`  — high-level Python API meant for external reuse.
- :mod:`vod_analyzer.cli`  — command-line interface (Typer-based, added later).

The package follows a strict layered architecture: ``core`` has no dependency
on ``api`` or ``cli``; the inverse is allowed. This keeps ``core`` reusable
and easy to test.
"""

from __future__ import annotations

# Single source of truth for the version. `pyproject.toml` reads this value
# at build time via `tool.hatch.version`. The format is intentionally bare
# (`__version__ = "..."`) to match hatchling's default regex; type inference
# handles the typing automatically.
__version__ = "0.0.1"

__all__ = ["__version__"]
