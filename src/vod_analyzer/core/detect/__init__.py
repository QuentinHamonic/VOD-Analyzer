"""Highlight detectors for VOD Analyzer.

Each sub-module implements one independent signal source and returns a list of
:class:`~vod_analyzer.core.detect.audio_energy.Candidate` objects ranked by
score. The fusion layer (Phase 8) will combine them.

Available detectors
-------------------
- :mod:`vod_analyzer.core.detect.audio_energy` — RMS-energy-based detector.
"""
