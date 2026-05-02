"""Typer-based CLI for VOD Analyzer.

Entry point registered in ``pyproject.toml`` as ``vod-analyzer``.

Usage examples::

    vod-analyzer ingest my_vod.mp4
    vod-analyzer ingest my_vod.mp4 --sample-rate 44100 --audio-out audio.wav
    vod-analyzer ingest my_vod.mp4 --verbose
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from vod_analyzer.core.ingest import extract_audio, load_vod

app = typer.Typer(
    name="vod-analyzer",
    help="Analyze VODs and extract the best moments as clips.",
    add_completion=False,
)


@app.command()
def ingest(
    path: Annotated[Path, typer.Argument(help="Path to the VOD file.")],
    sample_rate: Annotated[
        int,
        typer.Option("--sample-rate", "-r", help="Audio sample rate for the extracted WAV (Hz)."),
    ] = 16_000,
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
    typer.echo(f"Audio     : {meta.audio_codec} @ {meta.sample_rate} Hz")

    wav = extract_audio(meta, sample_rate=sample_rate, output_path=audio_out)
    typer.echo(f"Audio out : {wav}")
