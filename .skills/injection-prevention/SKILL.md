---
name: injection-prevention
description: Use this skill whenever code calls subprocess (ffmpeg, ffprobe) or constructs file paths from user input. The primary risk in this project is shell injection via ffmpeg command construction and path traversal. Covers: subprocess args as lists (never shell=True with user input), shlex.quote if shell=True is unavoidable, Path.resolve() + is_relative_to() for path containment, and bans on eval/exec/pickle on external data.
---

# Injection prevention

## Subprocess ffmpeg / ffprobe — règle absolue

**Toujours passer les arguments en liste. Jamais `shell=True` avec des variables.**

```python
import subprocess
from pathlib import Path

# ✅ CORRECT — args en liste, pas de shell
subprocess.run(
    [
        "ffmpeg",
        "-i", str(vod_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-map", f"0:a:{audio_track}",
        str(output_path),
    ],
    capture_output=True,
    check=True,
)

# ❌ INTERDIT — injection possible si vod_path contient des espaces ou des caractères spéciaux
subprocess.run(
    f"ffmpeg -i {vod_path} -vn -acodec pcm_s16le {output_path}",
    shell=True,
)

# ❌ INTERDIT — os.system
import os
os.system(f"ffmpeg -i {vod_path} ...")
```

## Si `shell=True` est techniquement nécessaire

Justifier dans un commentaire. Utiliser `shlex.quote()` sur **toutes** les variables dérivées de l'input utilisateur.

```python
import shlex

# Acceptable uniquement si subprocess liste est impossible
cmd = f"ffmpeg -i {shlex.quote(str(vod_path))} -vn {shlex.quote(str(output_path))}"
subprocess.run(cmd, shell=True, check=True)
```

Mais préférer systématiquement la liste d'arguments.

## Path traversal — chemins utilisateur

Tout chemin fourni par l'utilisateur via CLI doit être résolu et validé avant usage.

```python
from pathlib import Path

# ✅ CORRECT — résolution absolue + vérification existence
def validate_vod_path(user_input: Path) -> Path:
    resolved = user_input.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"VOD not found: {resolved}")
    if not resolved.is_file():
        raise ValueError(f"Not a file: {resolved}")
    return resolved

# ❌ INTERDIT — chemin non validé passé directement à ffmpeg
subprocess.run(["ffmpeg", "-i", str(user_path), ...])
```

Pour les répertoires de sortie fournis par l'utilisateur (`--output-dir`), s'assurer que le chemin est absolu et créer le répertoire proprement :

```python
output_dir = Path(user_output_dir).resolve()
output_dir.mkdir(parents=True, exist_ok=True)
```

## Audio track index

L'index de piste audio (`--audio-track`) est un entier passé directement dans `-map 0:a:N`. Valider qu'il s'agit d'un entier non négatif avant de construire la commande.

```python
if audio_track < 0:
    raise ValueError(f"audio_track must be >= 0, got {audio_track}")
# Puis utiliser comme entier dans la liste d'args, jamais interpolé dans une string shell
"-map", f"0:a:{audio_track}",  # sûr car audio_track est un int validé
```

## Désérialisation — sortie ffprobe JSON

La sortie `ffprobe -print_format json` est parsée via `json.loads()`. C'est sûr, mais :
- Ne pas utiliser `eval()` sur la sortie.
- Ne pas utiliser `pickle` pour cacher des résultats ffprobe.
- `yaml.safe_load()` si YAML, jamais `yaml.load()` sans SafeLoader.

```python
# ✅ CORRECT
import json
meta = json.loads(ffprobe_stdout)

# ❌ INTERDIT
meta = eval(ffprobe_stdout)
```

## Anti-patterns interdits — récapitulatif

| Pattern | Risque | Alternative |
|--------|--------|-------------|
| `subprocess.run(f"ffmpeg ... {path}", shell=True)` | Shell injection | Args en liste |
| `os.system(f"ffmpeg {path}")` | Shell injection | `subprocess.run` avec liste |
| `open(user_input)` sans resolve | Path traversal | `Path(user_input).resolve()` + validation |
| `eval(ffprobe_output)` | RCE | `json.loads()` |
| `pickle.loads(cache_file)` | RCE | JSON, ou ne pas cacher en pickle |
