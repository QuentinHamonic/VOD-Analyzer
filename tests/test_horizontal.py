"""Tests for :mod:`vod_analyzer.core.render.horizontal`.

Uses the ``tiny_vod`` session fixture (a synthetic 2-second MP4) defined in
``conftest.py``. Clips are rendered to pytest's temporary directories so that
no files persist after the test run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vod_analyzer.core.detect.audio_energy import Candidate
from vod_analyzer.core.render.horizontal import (
    PRESETS,
    RenderedClip,
    render_all,
    render_clip,
)

# A candidate that fits within the 2-second tiny_vod fixture
CANDIDATE = Candidate(start=0.2, end=1.2, score=0.9, source="audio_energy")
CANDIDATE_B = Candidate(start=0.5, end=1.5, score=0.7, source="audio_energy")


class TestRenderClip:
    def test_returns_rendered_clip_instance(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(tiny_vod, CANDIDATE, tmp_path, preset="h264_fast")
        assert isinstance(result, RenderedClip)

    def test_output_file_exists(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(tiny_vod, CANDIDATE, tmp_path, preset="h264_fast")
        assert result.path.exists()

    def test_output_is_mp4(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(tiny_vod, CANDIDATE, tmp_path, preset="h264_fast")
        assert result.path.suffix == ".mp4"

    def test_output_layout(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(tiny_vod, CANDIDATE, tmp_path, index=3, preset="h264_fast")
        # Must be under <vod_id>/horizontal/
        assert result.path.parent.name == "horizontal"
        assert result.path.parent.parent.name == tiny_vod.stem

    def test_filename_includes_index_and_slug(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(tiny_vod, CANDIDATE, tmp_path, index=2, preset="h264_fast")
        assert result.path.name.startswith("02_")
        assert "s-" in result.path.name

    def test_preset_stored_on_result(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(tiny_vod, CANDIDATE, tmp_path, preset="h264_fast")
        assert result.preset == "h264_fast"

    def test_candidate_stored_on_result(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(tiny_vod, CANDIDATE, tmp_path, preset="h264_fast")
        assert result.candidate == CANDIDATE

    def test_all_presets_produce_output(self, tiny_vod: Path, tmp_path: Path) -> None:
        for i, preset_name in enumerate(PRESETS):
            result = render_clip(tiny_vod, CANDIDATE, tmp_path, index=i, preset=preset_name)
            assert result.path.exists()

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            render_clip(Path("/nonexistent.mp4"), CANDIDATE, tmp_path)

    def test_unknown_preset_raises(self, tiny_vod: Path, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="preset"):
            render_clip(tiny_vod, CANDIDATE, tmp_path, preset="unknown_preset")


class TestRenderAll:
    def test_returns_list_of_rendered_clips(self, tiny_vod: Path, tmp_path: Path) -> None:
        clips = render_all(tiny_vod, [CANDIDATE, CANDIDATE_B], tmp_path, preset="h264_fast")
        assert all(isinstance(c, RenderedClip) for c in clips)

    def test_one_clip_per_candidate(self, tiny_vod: Path, tmp_path: Path) -> None:
        candidates = [CANDIDATE, CANDIDATE_B]
        clips = render_all(tiny_vod, candidates, tmp_path, preset="h264_fast")
        assert len(clips) == len(candidates)

    def test_empty_candidates_returns_empty(self, tiny_vod: Path, tmp_path: Path) -> None:
        assert render_all(tiny_vod, [], tmp_path) == []

    def test_all_clips_exist_on_disk(self, tiny_vod: Path, tmp_path: Path) -> None:
        clips = render_all(tiny_vod, [CANDIDATE, CANDIDATE_B], tmp_path, preset="h264_fast")
        for clip in clips:
            assert clip.path.exists()

    def test_clips_have_unique_filenames(self, tiny_vod: Path, tmp_path: Path) -> None:
        clips = render_all(tiny_vod, [CANDIDATE, CANDIDATE_B], tmp_path, preset="h264_fast")
        names = [c.path.name for c in clips]
        assert len(names) == len(set(names))
