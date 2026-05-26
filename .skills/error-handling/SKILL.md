---
name: error-handling
description: Use this skill whenever code catches, raises, or transforms an exception. Covers the absolute ban on silent except: pass, the requirement to use raise ... from ... to preserve causes, catching specific exceptions rather than Exception, defining a project exception hierarchy rooted in VodAnalyzerError, and surfacing errors cleanly in the Typer CLI.
---

# Error handling

## Hiérarchie d'exceptions du projet

```python
# src/vod_analyzer/core/exceptions.py
class VodAnalyzerError(Exception):
    """Base exception for all VOD Analyzer errors."""

class IngestError(VodAnalyzerError):
    """Errors during VOD loading or audio extraction."""

class VodNotFoundError(IngestError):
    def __init__(self, path: Path) -> None:
        super().__init__(f"VOD file not found: {path}")
        self.path = path

class FfprobeError(IngestError):
    """ffprobe returned a non-zero exit code or unparseable output."""

class DetectError(VodAnalyzerError):
    """Errors during audio/visual highlight detection."""

class RenderError(VodAnalyzerError):
    """Errors during clip rendering."""

class FfmpegError(RenderError):
    """ffmpeg returned a non-zero exit code."""
    def __init__(self, returncode: int, stderr: str) -> None:
        super().__init__(f"ffmpeg failed (rc={returncode}): {stderr[:200]}")
        self.returncode = returncode
        self.stderr = stderr
```

## Règle absolue — pas d'`except: pass` muet

```python
# ❌ INTERDIT
try:
    do_stuff()
except Exception:
    pass

# ✅ ACCEPTABLE avec justification
try:
    wav_path.unlink()
except FileNotFoundError:
    # Temp file already cleaned up — expected on Windows.
    pass
```

## Capturer les exceptions spécifiques

```python
# ❌ TROP LARGE
try:
    result = subprocess.run(cmd, check=True)
except Exception as e:
    raise RenderError(str(e))

# ✅ CORRECT
try:
    result = subprocess.run(cmd, capture_output=True, check=True)
except subprocess.CalledProcessError as e:
    raise FfmpegError(e.returncode, e.stderr.decode()) from e
```

## `raise ... from ...` — toujours préserver la cause

```python
# ✅ CORRECT
try:
    meta = json.loads(stdout)
except json.JSONDecodeError as e:
    raise FfprobeError("ffprobe output is not valid JSON") from e

# ❌ Perd le contexte original
try:
    meta = json.loads(stdout)
except json.JSONDecodeError:
    raise FfprobeError("ffprobe output is not valid JSON")
```

## Fail-fast vs fail-safe

- **Fail-fast** : configs invalides au démarrage, preset inconnu, chemin vide. Crasher tôt avec un message clair.
- **Fail-safe** : fichier WAV temporaire introuvable lors du nettoyage, stat de fichier optionnel. Logger et continuer.

```python
# Fail-fast — preset inconnu
if preset not in PRESETS:
    raise ValueError(f"Unknown preset {preset!r}. Choose from: {list(PRESETS)}")

# Fail-safe — nettoyage temporaire
try:
    wav_path.unlink()
except OSError:
    logger.debug("Could not clean up temp WAV %s", wav_path)
```

## CLI — surface propre à l'utilisateur

Dans `cli/`, capturer `VodAnalyzerError` et afficher un message lisible sans stack trace.

```python
try:
    meta = load_vod(path)
except VodNotFoundError as e:
    typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(code=1)
except VodAnalyzerError as e:
    typer.echo(f"Error: {e}", err=True)
    raise typer.Exit(code=1)
```

Jamais de stack trace en sortie standard. Uniquement via `--verbose` + logging.

## Logging avant re-raise

```python
try:
    result = subprocess.run(ffmpeg_cmd, capture_output=True, check=True)
except subprocess.CalledProcessError as e:
    logger.error("ffmpeg failed", extra={"cmd": ffmpeg_cmd, "stderr": e.stderr.decode()})
    raise FfmpegError(e.returncode, e.stderr.decode()) from e
```
