"""Smoke tests for the vod_analyzer package.

These tests confirm that the package is correctly installed and that its
public surface is reachable. They run in well under a second and are kept
minimal on purpose — their only job is to fail loudly if packaging itself
breaks (wrong import name, missing __init__, dynamic version misconfigured,
etc.).
"""

from __future__ import annotations

import vod_analyzer


def test_package_is_importable() -> None:
    """The top-level package can be imported."""
    assert vod_analyzer is not None


def test_package_exposes_version() -> None:
    """The package exposes a non-empty version string."""
    assert hasattr(vod_analyzer, "__version__")
    assert isinstance(vod_analyzer.__version__, str)
    assert vod_analyzer.__version__


def test_subpackages_are_importable() -> None:
    """All declared subpackages can be imported individually."""
    import vod_analyzer.api
    import vod_analyzer.cli
    import vod_analyzer.core  # noqa: F401
