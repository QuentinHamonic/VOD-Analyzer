---
name: vod-analyzer-ffmpeg
description: Use this skill whenever writing or modifying code that calls ffmpeg or ffprobe via subprocess. Covers: how to build safe argument lists, the two standard call patterns (check=True for fatal, Popen for streaming), how to parse ffprobe JSON output, the PRESETS dict structure, error mapping to FfmpegError/FfprobeError, and the rules for temporary file handling.
---

# VOD Analyzer — ffmpeg

## Pattern d'appel standard

Toujours des arguments en liste, jamais `shell=True` avec des variables. Voir `injection-prevention` skill.

```python
import subprocess
import logging

logger = logging.getLogger(__name__)

# ✅ Pattern standard — appel bloquant simple
result = subprocess.run(
    ["ffmpeg", "-y", "-i", str(vod_path), ...args..., str(output_path)],
    capture_output=True,
    check=True,   # lève CalledProcessError si returncode != 0
)

# Capturer et relancer proprement
try:
    subprocess.run(cmd, capture_output=True, check=True)
except subprocess.CalledProcessError as e:
    logger.error("ffmpeg failed", extra={"returncode": e.returncode})
    raise FfmpegError(e.returncode, e.stderr.decode(errors="replace")) from e
```

## Pattern ffprobe JSON

```python
import json
import subprocess

def _run_ffprobe(path: Path) -> dict:  # type: ignore[type-arg]
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        raise FfprobeError(f"ffprobe failed on {path}") from e
    except FileNotFoundError as e:
        raise FfprobeError("ffprobe not found — is ffmpeg installed?") from e

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise FfprobeError("ffprobe output is not valid JSON") from e
```

## Extraction audio

```python
cmd = [
    "ffmpeg",
    "-y",                         # overwrite output
    "-i", str(vod_path),
    "-vn",                        # no video
    "-acodec", "pcm_s16le",       # WAV 16-bit signed
    "-ar", str(sample_rate),      # sample rate
    "-ac", "1",                   # mono
    "-map", f"0:a:{audio_track}", # select audio stream N (int, validated)
    str(output_path),
]
```

## PRESETS — structure et extension

```python
# core/render/horizontal.py
PRESETS: dict[str, list[str]] = {
    "h264_fast": [
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
    ],
    "h264_balanced": [
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "192k",
    ],
}
```

Ajouter un preset : ajouter une entrée dans `PRESETS`. Le CLI valide automatiquement contre `list(PRESETS)`.

Pour le renderer vertical, créer `VERTICAL_PRESETS` dans `core/render/vertical.py` sur le même modèle.

## Clipping avec timestamp

```python
cmd = [
    "ffmpeg", "-y",
    "-ss", str(start),            # seek avant -i (input seeking, rapide)
    "-i", str(vod_path),
    "-t", str(duration),          # durée du clip
    *preset_args,                  # codec args depuis PRESETS[preset]
    "-movflags", "+faststart",    # streaming-friendly
    str(output_path),
]
```

Utiliser `-ss` avant `-i` (input seeking) : beaucoup plus rapide que output seeking pour les longues vidéos.

## Rendu vertical — filtre crop (phase 4)

Pour le center-crop 9:16 :

```python
# Calcul : out_width = floor(height * 9/16), centré sur la largeur
out_w = int(meta.height * 9 / 16)
x_offset = (meta.width - out_w) // 2

vf_filter = f"crop={out_w}:{meta.height}:{x_offset}:0"

cmd = [
    "ffmpeg", "-y",
    "-ss", str(start),
    "-i", str(vod_path),
    "-t", str(duration),
    "-vf", vf_filter,
    *preset_args,
    str(output_path),
]
```

## Fichiers temporaires

- Utiliser `tempfile.NamedTemporaryFile` ou `tmp_path` (en test).
- Toujours nettoyer après usage, même en cas d'erreur.

```python
import tempfile
from pathlib import Path

with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
    wav_path = Path(tmp.name)

try:
    extract_audio(meta, output_path=wav_path)
    candidates = detect(wav_path)
finally:
    wav_path.unlink(missing_ok=True)
```

## Erreurs courantes

| Symptôme | Cause probable | Fix |
|----------|---------------|-----|
| `FileNotFoundError: ffmpeg` | ffmpeg non installé ou pas dans PATH | Vérifier installation |
| `returncode=1, stderr: "No such file or directory"` | Chemin VOD incorrect | Valider `path.exists()` avant l'appel |
| `returncode=1, stderr: "Invalid data found"` | Fichier corrompu ou format non supporté | `FfprobeError` avec message clair |
| `returncode=1, stderr: "Stream specifier ... matches no streams"` | `audio_track` hors plage | Valider contre `len(meta.audio_tracks)` |
| Clip de durée 0 | `start >= end` après clamp | Vérifier la logique de padding et clamp |
