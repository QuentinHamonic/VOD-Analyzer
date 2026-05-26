---
name: python-quality
description: Use this skill whenever writing, modifying, or reviewing Python code. Covers Python 3.11+ requirement, mandatory tools (Ruff linter+formatter, mypy strict type checker, pytest), naming conventions, complete type hints on public signatures, modern type syntax (list[int] not List[int], X | None not Optional[X]), Google-style docstrings on public API, complexity limits (functions under 50 lines, files under 500 lines), and absolute imports only.
---

# Python quality

## Version

- Python 3.11+ minimum.
- Déclaré dans `pyproject.toml` : `requires-python = ">=3.11"`.

## Outils obligatoires

| Outil | Rôle | Config |
|-------|------|--------|
| [Ruff](https://docs.astral.sh/ruff/) | Linting **et** formatting (remplace Black) | `pyproject.toml` |
| [mypy](https://mypy.readthedocs.io/) | Typage statique strict | `pyproject.toml` |
| [pytest](https://docs.pytest.org/) | Tests | `pyproject.toml` |

**Pas de Black** — Ruff format est configuré Black-compatible (`quote-style = "double"`, `line-length = 100`).

Commandes :
```bash
ruff check .          # lint
ruff format .         # format
mypy                  # type check
pytest                # tests
pre-commit run --all-files  # tout d'un coup
```

## Type hints

- **Toute fonction publique a des type hints complets** (paramètres + retour).
- Fonctions privées (`_underscore`) : fortement encouragées.
- Pas de `Any` sans justification documentée.
- Types modernes uniquement : `list[int]`, `dict[str, int]`, `X | None`.

```python
# ✅ CORRECT
def detect(wav_path: Path, threshold: float = 0.5) -> list[Candidate]:
    ...

# ❌ INTERDIT
def detect(wav_path, threshold=0.5):
    ...

# ❌ Anciens types
from typing import List, Optional
def detect(wav_path: str, threshold: Optional[float] = None) -> List[Candidate]:
    ...
```

## Conventions de nommage

| Élément | Convention | Exemple |
|---------|------------|---------|
| Module / fichier | snake_case | `audio_energy.py` |
| Package / dossier | snake_case | `vod_analyzer` |
| Classe | PascalCase | `VodMetadata`, `Candidate` |
| Fonction / méthode | snake_case | `load_vod`, `detect` |
| Variable | snake_case | `wav_path`, `candidate_list` |
| Constante | UPPER_SNAKE_CASE | `PRESETS`, `DEFAULT_SAMPLE_RATE` |
| Type alias | PascalCase | `CandidateList = list[Candidate]` |
| Privé | leading underscore | `_run_ffprobe` |

**Règles transverses** :
- Anglais pour le code et les commentaires de code.
- Noms descriptifs : `wav_path` pas `p`, `candidate_list` pas `cands`.
- Booléens : `is_`, `has_`, `can_`.
- Fonctions : verbe infinitif : `load_vod`, `render_clip`, `extract_audio`.

## Docstrings — Google style

Obligatoire pour toute fonction/classe/méthode **publique** (dans `core/`, `api/`).

```python
def render_clip(
    vod_path: Path,
    candidate: Candidate,
    output_dir: Path,
    preset: str = "h264_balanced",
) -> RenderedClip:
    """Render a single highlight clip as a horizontal MP4.

    Args:
        vod_path: Path to the source VOD file. Must exist and be readable.
        candidate: The highlight candidate to render.
        output_dir: Root directory where the clip will be written.
        preset: Encoder preset key. Must be a key of PRESETS.

    Returns:
        A RenderedClip with the output path and source candidate.

    Raises:
        FileNotFoundError: If vod_path does not exist.
        ValueError: If preset is not a known key.
        subprocess.CalledProcessError: If ffmpeg fails.
    """
```

Inutile pour : fonctions privées < 5 lignes, setters triviaux.

## Complexité — guidelines

| Élément | Limite recommandée |
|---------|--------------------|
| Ligne | 100 caractères (Ruff) |
| Fonction | < 50 lignes |
| Fichier | < 500 lignes |
| Paramètres de fonction | < 6 |

Dépasser ces limites est acceptable avec **justification explicite**.

## Imports

**Toujours absolus, jamais relatifs.**

```python
# ✅ CORRECT
from vod_analyzer.core.ingest import VodMetadata
from vod_analyzer.core.detect.audio_energy import Candidate

# ❌ INTERDIT
from ..ingest import VodMetadata
```

## mypy strict — points clés

- `strict = true` dans `pyproject.toml`.
- Le `cli/` a `disallow_untyped_decorators = false` (Typer decorators).
- Librairies sans stubs (`librosa`, `numpy`) : `ignore_missing_imports = true` par override.
- Pas de `# type: ignore` sans commentaire expliquant pourquoi.
