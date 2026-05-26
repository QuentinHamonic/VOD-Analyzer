---
name: vod-analyzer-architecture
description: Use this skill when adding a new feature, creating a new module, or deciding where to place code. Covers the three-layer architecture (core / api / cli), strict dependency direction (cli and api depend on core, never the reverse), where to place new detectors, renderers, and backends, and the rules against global state and hidden side effects.
---

# VOD Analyzer architecture

## Trois couches strictes

```
┌────────────────────────────────────────┐
│  cli/       Typer CLI — interface      │  ← couche 3
├────────────────────────────────────────┤
│  api/       Python API — adapter mince │  ← couche 2
├────────────────────────────────────────┤
│  core/      Logique pure, sans I/O UI  │  ← couche 1
└────────────────────────────────────────┘
```

## Règle de dépendance — absolue

- **`core/`** ne dépend de rien dans `cli/` ou `api/`. Jamais.
- **`api/`** dépend de `core/`. Pas de `cli/`.
- **`cli/`** dépend de `core/` et peut dépendre de `api/`.

Si on a envie d'importer quelque chose de `cli/` dans `core/`, c'est un signal que l'architecture est mauvaise — repenser.

## Layout actuel

```
src/vod_analyzer/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── ingest.py              # VodMetadata, load_vod(), extract_audio()
│   ├── detect/
│   │   ├── __init__.py
│   │   └── audio_energy.py   # Candidate, detect()
│   └── render/
│       ├── __init__.py
│       └── horizontal.py     # RenderedClip, render_clip(), render_all(), PRESETS
├── api/
│   └── __init__.py            # à remplir en phase 10
└── cli/
    ├── __init__.py
    └── main.py                # commandes Typer : ingest, clips horizontal
```

## Où placer le nouveau code — guide

| Nouveau code | Où |
|---|---|
| Nouveau renderer (vertical, square, ...) | `core/render/<nom>.py` |
| Nouveau détecteur (scene, VAD, LLM scoring) | `core/detect/<nom>.py` |
| Nouveau backend ASR/LLM/diarization | `core/<domaine>/<backend>.py` |
| Nouveau sous-command CLI | `cli/main.py` (ajouter une commande au `clips_app` ou un nouveau `Typer`) |
| Point d'entrée Python pour notebooks | `api/__init__.py` |
| Dataclasses de données partagées | `core/ingest.py` ou nouveau `core/models.py` si beaucoup |

## Principes core/

1. **Pas de `print()`** — uniquement `logging.getLogger(__name__)`.
2. **Pas de lecture de variables d'environnement** — la config est passée en argument.
3. **Pas d'état global mutable** — pas de variables de module modifiées à l'exécution.
4. **Pas de side effects cachés** — une fonction qui écrit un fichier le déclare dans sa signature (retourne le chemin).

```python
# ✅ CORRECT — effet de bord déclaré
def extract_audio(meta: VodMetadata, output_path: Path, ...) -> Path:
    ...
    return output_path

# ❌ MAUVAIS — side effect caché
def extract_audio(meta: VodMetadata) -> None:
    # écrit un fichier quelque part sans le dire
    ...
```

## Dataclasses immuables pour les données de pipeline

Utiliser des `@dataclass(frozen=True)` pour les objets qui traversent les couches.

```python
@dataclass(frozen=True)
class Candidate:
    start: float
    end: float
    score: float
    source: str

@dataclass(frozen=True)
class RenderedClip:
    path: Path
    candidate: Candidate
    preset: str
```

Bénéfice : pas d'effet de bord accidentel, facile à tester.

## Interfaces pour les backends futurs

Pour les backends interchangeables (ASR, LLM, diarization en phases 5-7), définir un `Protocol` dans `core/` :

```python
from typing import Protocol

class ASRBackend(Protocol):
    def transcribe(self, wav_path: Path) -> list[TranscriptSegment]: ...
```

L'implémentation concrète (`FasterWhisperBackend`) vit dans `core/transcribe/faster_whisper.py`.

## CLI — responsabilités

Le CLI est **uniquement** responsable de :
1. Parser et valider les arguments (voir `input-validation` skill).
2. Orchestrer les appels `core/`.
3. Afficher les résultats à l'utilisateur (`typer.echo`).
4. Gérer les erreurs avec un message lisible + `typer.Exit(code=1)`.

Le CLI ne contient **aucune logique métier**. Si on a une logique non triviale dans `cli/main.py`, l'extraire dans `core/`.
