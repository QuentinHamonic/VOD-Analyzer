"""Typer-based CLI for VOD Analyzer.

Entry point registered in ``pyproject.toml`` as ``vod-analyzer``.

Usage examples::

    vod-analyzer ingest my_vod.mp4
    vod-analyzer ingest my_vod.mp4 --sample-rate 44100 --audio-out audio.wav

    vod-analyzer clips horizontal my_vod.mp4
    vod-analyzer clips horizontal my_vod.mp4 --output-dir ./out --preset h264_fast
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Annotated

import typer

from vod_analyzer.core.detect.audio_energy import detect
from vod_analyzer.core.ingest import extract_audio, load_vod
from vod_analyzer.core.render.horizontal import PRESETS, render_all
from vod_analyzer.core.render.vertical import (
    PRESETS as VERTICAL_PRESETS,
)
from vod_analyzer.core.render.vertical import (
    render_all as render_all_vertical,
)

app = typer.Typer(
    name="vod-analyzer",
    help="Analyze VODs and extract the best moments as clips.",
    add_completion=False,
)

clips_app = typer.Typer(help="Render highlight clips in various formats.")
app.add_typer(clips_app, name="clips")


# ---------------------------------------------------------------------------
# vod-analyzer ingest
# ---------------------------------------------------------------------------


@app.command()
def ingest(
    path: Annotated[Path, typer.Argument(help="Path to the VOD file.")],
    sample_rate: Annotated[
        int,
        typer.Option("--sample-rate", "-r", help="Audio sample rate for the extracted WAV (Hz)."),
    ] = 16_000,
    audio_track: Annotated[
        int,
        typer.Option("--audio-track", "-a", help="Zero-based audio stream index to extract."),
    ] = 0,
    audio_out: Annotated[
        Path | None,
        typer.Option("--audio-out", "-o", help="Destination WAV path. Defaults to a temp file."),
    ] = None,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging."),
    ] = False,
) -> None:
    """Ingest a VOD: display metadata and extract the audio track."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    meta = load_vod(path)

    typer.echo(f"Path      : {meta.path}")
    typer.echo(f"Duration  : {meta.duration:.2f} s")
    typer.echo(f"Resolution: {meta.width}x{meta.height} @ {meta.fps:.2f} fps")
    typer.echo(f"Video     : {meta.video_codec}")

    if meta.audio_tracks:
        typer.echo(f"Audio tracks ({len(meta.audio_tracks)}):")
        for track in meta.audio_tracks:
            marker = " <-- selected" if track.index == audio_track else ""
            typer.echo(
                f"  [{track.index}] {track.codec} "
                f"{track.sample_rate} Hz "
                f"{track.channels}ch ({track.channel_layout}){marker}"
            )
    else:
        typer.echo("Audio     : none")

    wav = extract_audio(
        meta,
        audio_track=audio_track,
        sample_rate=sample_rate,
        output_path=audio_out,
    )
    typer.echo(f"Audio out : {wav}")


# ---------------------------------------------------------------------------
# vod-analyzer clips horizontal
# ---------------------------------------------------------------------------


@clips_app.command("horizontal")
def clips_horizontal(
    path: Annotated[Path, typer.Argument(help="Path to the VOD file.")],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Root directory for rendered clips."),
    ] = Path("output"),
    preset: Annotated[
        str,
        typer.Option("--preset", "-p", help=f"Encoder preset. Choices: {list(PRESETS)}."),
    ] = "h264_balanced",
    audio_track: Annotated[
        int,
        typer.Option("--audio-track", "-a", help="Zero-based audio stream index to analyse."),
    ] = 0,
    threshold: Annotated[
        float,
        typer.Option("--threshold", "-t", help="RMS energy threshold (0-1)."),
    ] = 0.5,
    max_candidates: Annotated[
        int,
        typer.Option("--max-candidates", "-n", help="Maximum number of clips to render."),
    ] = 10,
    pre_padding: Annotated[
        float,
        typer.Option("--pre-padding", help="Seconds of footage before each highlight."),
    ] = 0.5,
    post_padding: Annotated[
        float,
        typer.Option("--post-padding", help="Seconds of footage after each highlight."),
    ] = 0.5,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging."),
    ] = False,
) -> None:
    """Detect highlights and render horizontal MP4 clips."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    if not path.exists():
        typer.echo(f"Error: file not found: {path}", err=True)
        raise typer.Exit(code=1)

    if preset not in PRESETS:
        typer.echo(f"Error: unknown preset {preset!r}. Choose from: {list(PRESETS)}", err=True)
        raise typer.Exit(code=1)

    typer.echo(f"Ingesting  : {path}")
    meta = load_vod(path)
    typer.echo(f"Duration   : {meta.duration:.2f} s")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)

    typer.echo(f"Extracting audio track {audio_track}...")
    extract_audio(meta, audio_track=audio_track, output_path=wav_path)

    typer.echo(f"Detecting highlights (threshold={threshold})...")
    candidates = detect(wav_path, threshold=threshold, max_candidates=max_candidates)

    if not candidates:
        typer.echo("No highlights found. Try lowering --threshold.")
        wav_path.unlink(missing_ok=True)
        return

    typer.echo(f"Found {len(candidates)} candidate(s). Rendering clips...")
    clips = render_all(
        path,
        candidates,
        output_dir,
        preset=preset,
        pre_padding=pre_padding,
        post_padding=post_padding,
    )

    wav_path.unlink(missing_ok=True)

    clip_dir = output_dir / meta.path.stem / "horizontal"
    typer.echo(f"\nDone - {len(clips)} clip(s) written to {clip_dir}/")
    for clip in clips:
        typer.echo(f"  {clip.path.name}  (score={clip.candidate.score:.2f})")


# ---------------------------------------------------------------------------
# vod-analyzer clips vertical
# ---------------------------------------------------------------------------


@clips_app.command("vertical")
def clips_vertical(
    path: Annotated[Path, typer.Argument(help="Path to the VOD file.")],
    output_dir: Annotated[
        Path,
        typer.Option("--output-dir", "-o", help="Root directory for rendered clips."),
    ] = Path("output"),
    preset: Annotated[
        str,
        typer.Option("--preset", "-p", help=f"Encoder preset. Choices: {list(VERTICAL_PRESETS)}."),
    ] = "h264_balanced",
    audio_track: Annotated[
        int,
        typer.Option("--audio-track", "-a", help="Zero-based audio stream index to analyse."),
    ] = 0,
    threshold: Annotated[
        float,
        typer.Option("--threshold", "-t", help="RMS energy threshold (0-1)."),
    ] = 0.5,
    max_candidates: Annotated[
        int,
        typer.Option("--max-candidates", "-n", help="Maximum number of clips to render."),
    ] = 10,
    pre_padding: Annotated[
        float,
        typer.Option("--pre-padding", help="Seconds of footage before each highlight."),
    ] = 0.5,
    post_padding: Annotated[
        float,
        typer.Option("--post-padding", help="Seconds of footage after each highlight."),
    ] = 0.5,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable debug logging."),
    ] = False,
) -> None:
    """Detect highlights and render vertical (9:16) MP4 clips."""
    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    if not path.exists():
        typer.echo(f"Error: file not found: {path}", err=True)
        raise typer.Exit(code=1)

    if preset not in VERTICAL_PRESETS:
        typer.echo(
            f"Error: unknown preset {preset!r}. Choose from: {list(VERTICAL_PRESETS)}",
            err=True,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Ingesting  : {path}")
    meta = load_vod(path)
    typer.echo(f"Duration   : {meta.duration:.2f} s")
    typer.echo(f"Resolution : {meta.width}x{meta.height}")

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_path = Path(tmp.name)

    typer.echo(f"Extracting audio track {audio_track}...")
    extract_audio(meta, audio_track=audio_track, output_path=wav_path)

    typer.echo(f"Detecting highlights (threshold={threshold})...")
    candidates = detect(wav_path, threshold=threshold, max_candidates=max_candidates)

    if not candidates:
        typer.echo("No highlights found. Try lowering --threshold.")
        wav_path.unlink(missing_ok=True)
        return

    typer.echo(f"Found {len(candidates)} candidate(s). Rendering vertical clips...")
    clips = render_all_vertical(
        path,
        candidates,
        output_dir,
        width=meta.width,
        height=meta.height,
        preset=preset,
        pre_padding=pre_padding,
        post_padding=post_padding,
    )

    wav_path.unlink(missing_ok=True)

    clip_dir = output_dir / meta.path.stem / "vertical"
    typer.echo(f"\nDone - {len(clips)} clip(s) written to {clip_dir}/")
    for clip in clips:
        typer.echo(f"  {clip.path.name}  (score={clip.candidate.score:.2f})")
