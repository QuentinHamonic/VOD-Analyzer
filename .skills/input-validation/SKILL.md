---
name: input-validation
description: Use this skill whenever code accepts data from the user via CLI arguments or file paths. Covers: validating VOD file paths (must exist, must be a file, sane extension), validating numeric CLI parameters (sample_rate bounds, threshold 0-1, audio_track >= 0, max_candidates > 0), validating encoder presets against the PRESETS dict, and the rule to validate at the CLI boundary only — core functions trust their typed arguments.
---

# Input validation

## Principe

Toute entrée externe est **hostile par défaut**. Pour ce projet, les entrées externes sont :
- Le chemin du fichier VOD (argument positionnel CLI).
- Les options numériques : `--sample-rate`, `--threshold`, `--audio-track`, `--max-candidates`, `--pre-padding`, `--post-padding`.
- Le preset d'encodage (`--preset`).
- Le répertoire de sortie (`--output-dir`).

**Valider à la frontière CLI uniquement.** Le code `core/` fait confiance aux types et valeurs qu'on lui passe.

## Validation du chemin VOD

```python
# Dans cli/main.py — avant tout appel à core/
if not path.exists():
    typer.echo(f"Error: file not found: {path}", err=True)
    raise typer.Exit(code=1)

if not path.is_file():
    typer.echo(f"Error: not a file: {path}", err=True)
    raise typer.Exit(code=1)
```

Extensions vidéo acceptées (optionnel mais recommandé) :
```python
VALID_EXTENSIONS = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".ts"}

if path.suffix.lower() not in VALID_EXTENSIONS:
    typer.echo(f"Warning: unexpected extension {path.suffix!r}", err=True)
    # Continuer — ffprobe détectera les vrais problèmes de format.
```

## Validation des numériques

```python
# threshold — doit être dans ]0, 1]
if not 0.0 < threshold <= 1.0:
    typer.echo("Error: --threshold must be in (0, 1]", err=True)
    raise typer.Exit(code=1)

# audio_track — entier non négatif
if audio_track < 0:
    typer.echo("Error: --audio-track must be >= 0", err=True)
    raise typer.Exit(code=1)

# sample_rate — plage raisonnable
if not 8_000 <= sample_rate <= 192_000:
    typer.echo("Error: --sample-rate must be between 8000 and 192000", err=True)
    raise typer.Exit(code=1)

# max_candidates — au moins 1
if max_candidates < 1:
    typer.echo("Error: --max-candidates must be >= 1", err=True)
    raise typer.Exit(code=1)

# paddings — non négatifs
if pre_padding < 0 or post_padding < 0:
    typer.echo("Error: padding values must be >= 0", err=True)
    raise typer.Exit(code=1)
```

## Validation du preset

```python
from vod_analyzer.core.render.horizontal import PRESETS

if preset not in PRESETS:
    typer.echo(
        f"Error: unknown preset {preset!r}. Choose from: {list(PRESETS)}",
        err=True,
    )
    raise typer.Exit(code=1)
```

## Validation du répertoire de sortie

Le répertoire de sortie peut ne pas exister — c'est normal, on le crée.
Mais valider qu'on ne pointe pas vers un fichier existant :

```python
if output_dir.exists() and not output_dir.is_dir():
    typer.echo(f"Error: {output_dir} exists and is not a directory", err=True)
    raise typer.Exit(code=1)
```

## Ce que core/ ne doit PAS valider

Le code `core/` reçoit des arguments déjà validés par le CLI. Il ne doit pas :
- Re-vérifier `path.exists()` à chaque appel (sauf dans les tests unitaires qui appellent core directement).
- Re-valider que `threshold` est dans `[0, 1]`.

Exception : lever une exception propre (`VodNotFoundError`, `FfmpegError`) si une condition inattendue survient à l'exécution (la vidéo disparaît entre la validation et l'appel ffmpeg, etc.).

## Messages d'erreur

- Courts et actionnables : `"Error: file not found: /path/to/vod.mp4"`.
- Toujours vers `err=True` (stderr), pas stdout.
- Pas de stack trace en sortie normale. Avec `--verbose` uniquement.
