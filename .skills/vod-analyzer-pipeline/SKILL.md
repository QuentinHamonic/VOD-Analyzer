---
name: vod-analyzer-pipeline
description: Use this skill when modifying any step of the detection pipeline (ingest, detect, render) or adding a new signal source. Covers the data contracts between pipeline steps (VodMetadata, Candidate, RenderedClip), the ingest→detect→render flow, how audio tracks are selected, how candidates are produced and ranked, and the rules for adding new detector or renderer modules.
---

# VOD Analyzer pipeline

## Vue d'ensemble

```
VOD file (mp4/mkv/...)
      │
      ▼
 [ingest]  load_vod() → VodMetadata
              extract_audio() → WAV file
      │
      ▼
 [detect]  detect(wav_path) → list[Candidate]
      │
      ▼
 [render]  render_all(vod_path, candidates, output_dir) → list[RenderedClip]
      │
      ▼
 Output clips (horizontal MP4, vertical MP4, ...)
```

## Contrats de données

### VodMetadata (`core/ingest.py`)

```python
@dataclass
class AudioTrackInfo:
    index: int           # zero-based stream index (0:a:N)
    codec: str
    sample_rate: int
    channels: int
    channel_layout: str

@dataclass
class VodMetadata:
    path: Path
    duration: float      # secondes
    width: int
    height: int
    fps: float
    video_codec: str
    audio_tracks: list[AudioTrackInfo]

    @property
    def audio_codec(self) -> str | None: ...   # compat : track 0
    @property
    def sample_rate(self) -> int | None: ...   # compat : track 0
```

### Candidate (`core/detect/audio_energy.py`)

```python
@dataclass(frozen=True)
class Candidate:
    start: float    # secondes depuis le début du VOD
    end: float      # secondes depuis le début du VOD
    score: float    # normalisé [0, 1] — plus haut = plus intéressant
    source: str     # "audio_energy" | "vad" | "llm" | ...
```

Invariants :
- `0 <= start < end <= meta.duration`
- `0 <= score <= 1`
- `source` est un identifiant stable du détecteur (pour le débogage et la fusion)

### RenderedClip (`core/render/horizontal.py`)

```python
@dataclass(frozen=True)
class RenderedClip:
    path: Path           # chemin absolu du fichier produit
    candidate: Candidate
    preset: str          # clé dans PRESETS
```

## Étape ingest

Responsabilités :
- Lire les métadonnées via ffprobe (durée, résolution, fps, pistes audio).
- Extraire la piste audio sélectionnée en WAV mono 16 kHz (configurable).
- Ne pas faire de détection ni de rendu.

Règle : `load_vod()` est read-only (lit juste les métadonnées). `extract_audio()` écrit un WAV et retourne son chemin.

## Étape detect

Responsabilités :
- Prendre un fichier WAV et des paramètres (threshold, window_size...).
- Retourner une `list[Candidate]` triée par `score` décroissant.
- Ne pas lire la vidéo. Ne pas produire de clips.

Ajouter un nouveau détecteur :
1. Créer `core/detect/<nom>.py` avec une fonction `detect(wav_path: Path, **kwargs) -> list[Candidate]`.
2. Utiliser le même type `Candidate` avec un `source` identifiable.
3. Ajouter des tests sur signaux synthétiques.

## Étape render

Responsabilités :
- Prendre la vidéo source + une liste de candidats + un répertoire de sortie.
- Produire des fichiers MP4 via ffmpeg.
- Retourner la liste des `RenderedClip` produits.

Layout de sortie :
```
output/
└── <vod_stem>/
    ├── horizontal/
    │   ├── 00_highlight.mp4
    │   └── 01_highlight.mp4
    └── vertical/        ← phase 4
        ├── 00_highlight.mp4
        └── 01_highlight.mp4
```

Ajouter un nouveau renderer :
1. Créer `core/render/<format>.py` avec `render_clip()` et `render_all()`.
2. Réutiliser les types `Candidate` et `RenderedClip`.
3. Ajouter une commande CLI dans `cli/main.py` : `vod-analyzer clips <format> <vod>`.
4. Ajouter des tests avec un `tiny_vod` fixture.

## Sélection de piste audio

Le paramètre `audio_track` est un index zero-based vers `-map 0:a:N` dans ffmpeg.
- Défaut : `0` (première piste audio).
- Doit être validé `>= 0` au niveau CLI avant d'atteindre core.
- En cas d'index hors plage, ffmpeg retourne une erreur → `FfmpegError`.

## Règle de padding

`pre_padding` et `post_padding` s'ajoutent aux bornes du candidat avant le clamp :

```python
actual_start = max(0.0, candidate.start - pre_padding)
actual_end = min(meta.duration, candidate.end + post_padding)
```

Ne jamais dépasser `0` ou `meta.duration` — ffmpeg échoue sur des timestamps hors bornes.

## Phases à venir

| Phase | Nouveau module | Intégration pipeline |
|-------|---------------|---------------------|
| 4 | `core/render/vertical.py` | Après `detect`, en parallèle de `horizontal` |
| 5 | `core/transcribe/` | Après `ingest`, avant `detect` |
| 6 | `core/diarize/` | Après `transcribe` |
| 7 | `core/llm/` | Après `transcribe`, produit des `Candidate` avec `source="llm"` |
| 8 | `core/rank/` | Fusionne les candidats multi-sources |
| 9 | `core/detect/scene.py` | Nouveau signal, intégré dans `rank/` |
