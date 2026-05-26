"""Tests for :mod:`vod_analyzer.core.render.vertical`.

Uses the ``tiny_vod`` session fixture (a synthetic 2-second 320x240 MP4)
defined in ``conftest.py``.  Clips are written to pytest's temporary
directories so that no files persist after the test run.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vod_analyzer.core.detect.audio_energy import Candidate
from vod_analyzer.core.render._models import RenderedClip
from vod_analyzer.core.render.vertical import (
    PRESETS,
    _center_crop_filter,
    render_all,
    render_clip,
)

# tiny_vod fixture is 320x240 — constants used across tests
VOD_WIDTH = 320
VOD_HEIGHT = 240

CANDIDATE = Candidate(start=0.2, end=1.2, score=0.9, source="audio_energy")
CANDIDATE_B = Candidate(start=0.5, end=1.5, score=0.7, source="audio_energy")


# ---------------------------------------------------------------------------
# _center_crop_filter unit tests (no I/O)
# ---------------------------------------------------------------------------


class TestCenterCropFilter:
    def test_landscape_produces_narrower_width(self) -> None:
        # 320x240 → out_w = 240*9/16 = 135 < 320
        f = _center_crop_filter(320, 240)
        assert f.startswith("crop=135:240:")

    def test_landscape_x_is_centred(self) -> None:
        # x = (320 - 135) // 2 = 92
        f = _center_crop_filter(320, 240)
        assert f == "crop=135:240:92:0"

    def test_square_source(self) -> None:
        # 240x240 → out_w = 240*9/16 = 135, x = (240-135)//2 = 52
        f = _center_crop_filter(240, 240)
        assert f == "crop=135:240:52:0"

    def test_portrait_source_crops_height(self) -> None:
        # 270x480 → out_w = 480*9/16 = 270 == width → no horizontal crop
        # but 270 == width so out_w <= width branch: x = (270-270)//2 = 0
        f = _center_crop_filter(270, 480)
        assert f == "crop=270:480:0:0"

    def test_very_wide_source_1920x1080(self) -> None:
        # out_w = 1080*9/16 = 607, x = (1920-607)//2 = 656
        f = _center_crop_filter(1920, 1080)
        assert f == "crop=607:1080:656:0"

    def test_output_is_string(self) -> None:
        assert isinstance(_center_crop_filter(1280, 720), str)


# ---------------------------------------------------------------------------
# render_clip integration tests
# ---------------------------------------------------------------------------


class TestRenderClip:
    def test_returns_rendered_clip_instance(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(
            tiny_vod, CANDIDATE, tmp_path, width=VOD_WIDTH, height=VOD_HEIGHT, preset="h264_fast"
        )
        assert isinstance(result, RenderedClip)

    def test_output_file_exists(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(
            tiny_vod, CANDIDATE, tmp_path, width=VOD_WIDTH, height=VOD_HEIGHT, preset="h264_fast"
        )
        assert result.path.exists()

    def test_output_is_mp4(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(
            tiny_vod, CANDIDATE, tmp_path, width=VOD_WIDTH, height=VOD_HEIGHT, preset="h264_fast"
        )
        assert result.path.suffix == ".mp4"

    def test_output_layout(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(
            tiny_vod,
            CANDIDATE,
            tmp_path,
            width=VOD_WIDTH,
            height=VOD_HEIGHT,
            index=3,
            preset="h264_fast",
        )
        assert result.path.parent.name == "vertical"
        assert result.path.parent.parent.name == tiny_vod.stem

    def test_filename_includes_index_and_slug(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(
            tiny_vod,
            CANDIDATE,
            tmp_path,
            width=VOD_WIDTH,
            height=VOD_HEIGHT,
            index=2,
            preset="h264_fast",
        )
        assert result.path.name.startswith("02_")
        assert "s-" in result.path.name

    def test_preset_stored_on_result(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(
            tiny_vod, CANDIDATE, tmp_path, width=VOD_WIDTH, height=VOD_HEIGHT, preset="h264_fast"
        )
        assert result.preset == "h264_fast"

    def test_candidate_stored_on_result(self, tiny_vod: Path, tmp_path: Path) -> None:
        result = render_clip(
            tiny_vod, CANDIDATE, tmp_path, width=VOD_WIDTH, height=VOD_HEIGHT, preset="h264_fast"
        )
        assert result.candidate == CANDIDATE

    def test_all_presets_produce_output(self, tiny_vod: Path, tmp_path: Path) -> None:
        for i, preset_name in enumerate(PRESETS):
            result = render_clip(
                tiny_vod,
                CANDIDATE,
                tmp_path,
                width=VOD_WIDTH,
                height=VOD_HEIGHT,
                index=i,
                preset=preset_name,
            )
            assert result.path.exists()

    def test_file_not_found_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            render_clip(
                Path("/nonexistent.mp4"),
                CANDIDATE,
                tmp_path,
                width=VOD_WIDTH,
                height=VOD_HEIGHT,
            )

    def test_unknown_preset_raises(self, tiny_vod: Path, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="preset"):
            render_clip(
                tiny_vod,
                CANDIDATE,
                tmp_path,
                width=VOD_WIDTH,
                height=VOD_HEIGHT,
                preset="unknown",
            )

    def test_zero_width_raises(self, tiny_vod: Path, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="positive"):
            render_clip(tiny_vod, CANDIDATE, tmp_path, width=0, height=VOD_HEIGHT)

    def test_zero_height_raises(self, tiny_vod: Path, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="positive"):
            render_clip(tiny_vod, CANDIDATE, tmp_path, width=VOD_WIDTH, height=0)


# ---------------------------------------------------------------------------
# render_all integration tests
# ---------------------------------------------------------------------------


class TestRenderAll:
    def test_returns_list_of_rendered_clips(self, tiny_vod: Path, tmp_path: Path) -> None:
        clips = render_all(
            tiny_vod,
            [CANDIDATE, CANDIDATE_B],
            tmp_path,
            width=VOD_WIDTH,
            height=VOD_HEIGHT,
            preset="h264_fast",
        )
        assert all(isinstance(c, RenderedClip) for c in clips)

    def test_one_clip_per_candidate(self, tiny_vod: Path, tmp_path: Path) -> None:
        candidates = [CANDIDATE, CANDIDATE_B]
        clips = render_all(
            tiny_vod,
            candidates,
            tmp_path,
            width=VOD_WIDTH,
            height=VOD_HEIGHT,
            preset="h264_fast",
        )
        assert len(clips) == len(candidates)

    def test_empty_candidates_returns_empty(self, tiny_vod: Path, tmp_path: Path) -> None:
        assert render_all(tiny_vod, [], tmp_path, width=VOD_WIDTH, height=VOD_HEIGHT) == []

    def test_all_clips_exist_on_disk(self, tiny_vod: Path, tmp_path: Path) -> None:
        clips = render_all(
            tiny_vod,
            [CANDIDATE, CANDIDATE_B],
            tmp_path,
            width=VOD_WIDTH,
            height=VOD_HEIGHT,
            preset="h264_fast",
        )
        for clip in clips:
            assert clip.path.exists()

    def test_clips_have_unique_filenames(self, tiny_vod: Path, tmp_path: Path) -> None:
        clips = render_all(
            tiny_vod,
            [CANDIDATE, CANDIDATE_B],
            tmp_path,
            width=VOD_WIDTH,
            height=VOD_HEIGHT,
            preset="h264_fast",
        )
        names = [c.path.name for c in clips]
        assert len(names) == len(set(names))

    def test_clips_go_to_vertical_subdir(self, tiny_vod: Path, tmp_path: Path) -> None:
        clips = render_all(
            tiny_vod,
            [CANDIDATE],
            tmp_path,
            width=VOD_WIDTH,
            height=VOD_HEIGHT,
            preset="h264_fast",
        )
        assert clips[0].path.parent.name == "vertical"
