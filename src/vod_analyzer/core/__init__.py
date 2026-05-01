"""Core logic of VOD Analyzer.

This package contains the pure, dependency-light building blocks of the
analysis pipeline: VOD ingestion, audio / vision / language detectors, scoring,
fusion, and clip rendering.

Modules in :mod:`vod_analyzer.core` MUST NOT import from
:mod:`vod_analyzer.api` or :mod:`vod_analyzer.cli`. This separation is what
allows the project to be reused as a library without dragging in CLI or web
dependencies.
"""
