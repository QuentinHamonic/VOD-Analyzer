---
name: testing-python
description: Use this skill whenever writing or modifying Python tests with pytest. Covers the Arrange-Act-Assert pattern, descriptive test names, fixtures over duplicated setup, synthetic WAV/video fixtures via tmp_path (never inside the repo), the ban on time.sleep in tests, and testing behavior over implementation.
---

# Testing Python

## Philosophie

- Le test est la **seule preuve** que le code marche.
- Tester ce que le code **fait** (comportement, sortie pour une entrée), pas comment il le fait.

## Structure

```
tests/
├── conftest.py              # fixtures partagées (tiny_vod, synthetic_wav, ...)
├── test_ingest.py
├── test_audio_energy.py
├── test_render_horizontal.py
└── test_render_vertical.py  # à créer en phase 4
```

Un fichier `test_<module>.py` par module testé dans `core/`.

## Convention de nommage

```python
# ✅ CORRECT
def test_detect_returns_empty_list_when_audio_is_silence():
    ...

def test_render_clip_writes_mp4_to_output_dir():
    ...

def test_load_vod_raises_when_file_not_found():
    ...

# ❌ MAUVAIS
def test_detect():
    ...

def test1():
    ...
```

## Pattern Arrange-Act-Assert

```python
def test_detect_finds_single_peak_above_threshold(tmp_path: Path):
    # Arrange
    wav = make_synthetic_wav(tmp_path, peak_at=1.0, duration=3.0)

    # Act
    candidates = detect(wav, threshold=0.3)

    # Assert
    assert len(candidates) == 1
    assert 0.8 < candidates[0].start < 1.2
```

## Fixtures — conftest.py

Pas de duplication de setup. Centraliser dans `conftest.py`.

```python
# tests/conftest.py
import numpy as np
import pytest
import soundfile as sf
from pathlib import Path

@pytest.fixture
def tiny_wav(tmp_path: Path) -> Path:
    """2-second WAV with a single energy peak at 1 second."""
    sr = 16_000
    silence = np.zeros(sr, dtype=np.float32)
    peak = np.random.uniform(-1, 1, sr).astype(np.float32)
    audio = np.concatenate([silence, peak])
    path = tmp_path / "test.wav"
    sf.write(path, audio, sr)
    return path
```

Pour les tests qui nécessitent un vrai fichier vidéo : utiliser le fixture `tiny_vod` existant dans `conftest.py` (généré via ffmpeg avec un signal de test).

## Tester le comportement, pas l'implémentation

```python
# ✅ CORRECT — teste la sortie
def test_detect_ranks_candidates_by_score_descending(tiny_wav: Path):
    candidates = detect(tiny_wav, threshold=0.1)
    scores = [c.score for c in candidates]
    assert scores == sorted(scores, reverse=True)

# ❌ MAUVAIS — teste l'implémentation interne
def test_detect_calls_librosa_rms():
    with patch("vod_analyzer.core.detect.audio_energy.librosa.feature.rms") as mock:
        detect(tiny_wav, threshold=0.5)
        mock.assert_called_once()
```

## Fichiers temporaires

- **Jamais** de fichiers générés dans le repo.
- Fixture `tmp_path` de pytest — automatiquement nettoyée.

```python
def test_render_writes_to_output_dir(tmp_path: Path, tiny_vod: Path):
    candidate = Candidate(start=0.0, end=1.0, score=0.9, source="audio_energy")
    clip = render_clip(tiny_vod, candidate, tmp_path)
    assert clip.path.exists()
    assert clip.path.suffix == ".mp4"
```

## Mocking ffmpeg/ffprobe

Préférer les vraies commandes sur un tiny_vod fixture quand c'est possible.
Mocker uniquement quand le test vérifie le *chemin d'erreur* (ffmpeg absent, returncode non-zéro).

```python
def test_load_vod_raises_on_ffprobe_failure(tmp_path: Path):
    fake = tmp_path / "bad.mp4"
    fake.write_bytes(b"not a valid video")
    with pytest.raises(RuntimeError, match="ffprobe"):
        load_vod(fake)
```

## Pyramide

```
       /\
      /e2e\       ← full pipeline sur un vrai VOD (CI manual ou fixture lourde)
     /------\
    /  intg  \    ← render réel avec tiny_vod fixture, ffmpeg disponible
   /----------\
  /   unit     \  ← detect sur WAV synthétique, parse metadata mockée
 /--------------\
```

- **Unitaires** : 80%+ — signaux synthétiques, pas d'I/O réel si possible.
- **Intégration** : tests qui appellent ffmpeg avec un tiny_vod fixture (< 1 s).
- **E2E** : pipeline complet sur un vrai fichier — en CI avec un fichier de test commité ou downloadable.

## Pas de `time.sleep`

Anti-pattern. Utiliser des fixtures déterministes plutôt que d'attendre une condition.

## Couverture

- Pas de cible dogmatique.
- Indicatif : 80%+ sur `core/`.
- `pytest --cov=src/vod_analyzer --cov-report=term-missing`.
