# Roadmap

This document describes the development roadmap for **VOD Analyzer**, a tool
that ingests stream VODs and extracts the most interesting moments as ready-to-share
short-form (vertical) and long-form (horizontal) clips.

The roadmap is intentionally split into small, self-contained phases. Each
phase produces a usable proof-of-concept that subsequent phases refine and
extend. The goal is to keep the project releasable at every milestone, with
a clean git history and a clean public surface — no half-broken intermediate
states on `main`.

---

## 1. Vision

VOD Analyzer takes a long stream recording (Twitch / YouTube / local file) and
produces a ranked list of candidate highlights, each rendered as horizontal
and vertical clips suitable for short-form publishing.

The detection pipeline combines **three independent signals**:

- **Audio** — energy peaks, voice activity, laughter / crowd reactions.
- **Vision** — scene boundaries and basic visual saliency.
- **Language** — automatic transcription scored by a local LLM to identify
  semantically interesting passages (jokes, reveals, key plays, emotional
  beats).

Each signal is implemented as a separate, testable module. The final ranking
combines them with configurable weights so that users can tune the detector
to their content (gameplay, talk show, music, etc.).

## 2. Design principles

The project is a portfolio piece, but it is also designed to be lifted as a
module into other Python applications without modification. To make that
possible, three rules govern every decision:

1. **Strict layering.** A `core/` package contains pure, dependency-light logic
   (detection, scoring, fusion, clip generation). On top of it sit thin
   adapters: a Python `api/`, a `cli/` (Typer), and later a `webui/`. Adapters
   may depend on `core/`; `core/` never depends on adapters.
2. **No global state, no hidden side-effects.** Configuration is explicit —
   passed as arguments or loaded from a TOML file by the adapter layer. No
   reading from environment variables inside `core/`. No `print()` — only
   structured logging via the `logging` module.
3. **Backend-agnostic integrations.** External services (LLM, transcription,
   diarization) are accessed through small interfaces with at least one
   default local implementation. Swapping `faster-whisper` for another ASR,
   or `ollama` for `llama.cpp`, must not require touching `core/`.

These principles also serve the portfolio goal: the code should read well as
a textbook example of layered Python.

## 3. Tech stack

| Concern               | Choice                                       |
| --------------------- | -------------------------------------------- |
| Language              | Python 3.11+                                 |
| Packaging             | `pyproject.toml` (PEP 621), `src/` layout    |
| Linting / formatting  | `ruff` + `black`                             |
| Type checking         | `mypy` (strict on `core/`)                   |
| Testing               | `pytest`                                     |
| Pre-commit            | `pre-commit` with the above                  |
| CI                    | GitHub Actions (lint, type-check, tests)     |
| Media I/O             | `ffmpeg` (subprocess) + `ffmpeg-python`      |
| Audio analysis        | `librosa`, `silero-vad`                      |
| Speech-to-text        | `faster-whisper`                             |
| Speaker diarization   | `pyannote.audio`                             |
| LLM access            | OpenAI-compatible HTTP client (ollama, vLLM, llama.cpp, …) |
| Scene detection       | `PySceneDetect`                              |
| CLI                   | `Typer`                                      |
| Web UI (later)        | `Gradio` or `FastAPI` + small frontend       |
| Licence               | MIT                                          |

## 4. Phases

The roadmap is split into twelve phases (Phase 0 is the engineering
foundation). Each phase has a clear **Definition of Done** so that progress
is measurable and the public state of the project never regresses.

### Phase 0 — Foundations

Set up everything needed to ship clean code: project layout, packaging,
tooling, CI, and contributor-facing documentation.

- `pyproject.toml` with project metadata and dependency groups.
- `src/vod_analyzer/{core,api,cli}` skeleton.
- `tests/` skeleton with one trivial passing test.
- `ruff`, `black`, `mypy`, `pytest` configured.
- `pre-commit` hooks for lint + format + type check.
- GitHub Actions workflow running lint and tests on push / PR.
- `README.md` expanded with quickstart, usage, and roadmap link.
- `CHANGELOG.md` started in Keep-a-Changelog format.

**Definition of Done:** `pre-commit run --all-files` passes locally, the CI
workflow is green on the branch, and a fresh clone can run `pip install -e .[dev]`
and `pytest` successfully.

### Phase 1 — VOD ingestion

The first end-to-end vertical slice: load a local video file, extract its
audio track, and report basic metadata.

- `core.ingest` module with a `load_vod(path)` function returning a
  metadata object (duration, video codec, audio codec, resolution, fps).
- Audio extraction via `ffmpeg` to a temp WAV at a known sample rate.
- CLI command `vod-analyzer ingest <path>` that prints the metadata and the
  path to the extracted audio.
- Unit tests on metadata parsing using a tiny fixture video.

**Definition of Done:** `vod-analyzer ingest` works on a real test VOD and
produces both a metadata dump and a usable audio file.

### Phase 2 — Audio highlight detection (POC)

First detector: a naive but useful audio-energy-based highlight finder.

- `core.detect.audio_energy` computes RMS energy windows via `librosa`.
- A threshold-based heuristic (configurable) selects candidate peaks.
- Returns a list of `Candidate(start, end, score, source="audio_energy")`.
- Unit tests cover the detector on synthetic signals (silence vs. peak).

**Definition of Done:** Running the detector on the test VOD returns a
non-empty, ranked list of plausible candidate windows.

### Phase 3 — Horizontal clip generation

Turn a list of candidates into ready-to-share horizontal clips.

- `core.render.horizontal` extracts a clip with optional pre/post padding.
- Encoder presets (`h264_fast`, `h264_balanced`) configurable via TOML.
- Output directory layout: `output/<vod_id>/horizontal/<index>_<slug>.mp4`.
- CLI command `vod-analyzer clips horizontal <vod>` chains the previous
  phases end-to-end.

**Definition of Done:** Running the CLI on the test VOD writes playable
horizontal MP4s to disk for every candidate.

### Phase 4 — Vertical clip generation

Render the same candidates in 9:16. Two stages so the project keeps
shipping useful clips early.

- **Stage A (simple).** Center-crop to 9:16 with optional letterbox / blurred
  fill background.
- **Stage B (smart).** Face / action tracking via `opencv` to keep the
  subject framed across the clip.
- CLI command `vod-analyzer clips vertical <vod>` (Stage A by default,
  `--smart` to enable tracking).

**Definition of Done:** Each candidate is available in both horizontal and
vertical format, and Stage B noticeably outperforms Stage A on a clip with
camera movement.

### Phase 5 — Speech-to-text

Add a transcript so that downstream phases can reason about content.

- `core.transcribe` wraps `faster-whisper` behind an `ASRBackend` interface.
- Configurable model size, language, and compute type.
- Output: a list of `TranscriptSegment(start, end, text, words?)` aligned
  with the audio timeline.
- Optional VAD pre-filter (`silero-vad`) to skip long silent stretches.

**Definition of Done:** Transcription runs end-to-end on the test VOD, with
timestamps that align (within a small tolerance) with the original audio.

### Phase 6 — Speaker diarization

Identify who speaks when, so highlights can be filtered or weighted by
speaker.

- `core.diarize` wraps `pyannote.audio` behind a `DiarizationBackend`
  interface.
- HuggingFace authentication handled via env var, never committed.
- Output merged with the transcript: each `TranscriptSegment` carries an
  optional `speaker_id`.

**Definition of Done:** Test VOD transcript is annotated with consistent
speaker labels across segments, validated by spot-checking.

### Phase 7 — LLM highlight scoring

Use a local LLM to score transcript segments for "highlightability".

- `core.llm.LLMClient` interface, default implementation talks to an
  OpenAI-compatible endpoint (works with `ollama`, `llama.cpp` server,
  `vllm`, etc.).
- Prompt template asking the model to score a segment from 0 to 10 with a
  short rationale.
- Output: each `TranscriptSegment` gains an `llm_score` and `llm_reason`.
- Caching layer keyed on (segment_text, model, prompt_version) so re-runs
  are cheap.

**Definition of Done:** Running the scorer on the test transcript returns
sensible scores with rationales, and re-running uses the cache.

### Phase 8 — Multi-signal fusion

Combine the audio, transcript, and LLM signals into a single ranked list.

- `core.rank.fuse` takes per-source candidate lists and merges them.
- Configurable weights per source, normalized scoring.
- De-duplication and merging of overlapping windows.
- Output: top-N highlights with combined score and provenance per source.

**Definition of Done:** The top-N list on the test VOD is qualitatively
better than any single-source ranking, and weights are exposed in config.

### Phase 9 — Vision layer

Bring scene boundaries and visual saliency into the pipeline.

- `core.detect.scene` wraps `PySceneDetect` to produce shot boundaries.
- Optional `core.detect.visual` adds simple frame-level features (motion,
  brightness changes) as a third highlight signal.
- Fusion in Phase 8 is extended with vision weights.

**Definition of Done:** Scene boundaries are respected when picking clip
in/out points, and the vision signal contributes measurable lift on at
least one test VOD genre.

### Phase 10 — Stable public API and mature CLI

Lock down the surface for reuse by other projects (and for the upcoming
Web UI).

- Public `api/` module with a small, documented set of entrypoints.
- All CLI commands have `--help`, `--config`, and `--verbose` flags.
- `mkdocs` site generated from docstrings + handwritten guides.
- Example scripts under `examples/`.
- API stability commitment from this point onward.

**Definition of Done:** The documented API is enough to run the full
pipeline from a notebook in fewer than 10 lines, and the CLI is consistent
across commands.

### Phase 11 — Web UI

A lightweight web frontend for non-technical users.

- Upload (or point to) a VOD, see detected highlights, preview and download
  clips.
- Built on `Gradio` for speed of iteration, or `FastAPI` + a minimal
  frontend if more control is needed.
- Strictly an adapter on top of the public API — no business logic in the
  UI layer.

**Definition of Done:** A user with no Python knowledge can produce
horizontal and vertical clips from a VOD entirely through the web UI.

## 5. Phase summary table

| #   | Phase                          | Status      | Depends on      | Key deliverables                                     |
| --- | ------------------------------ | ----------- | --------------- | ---------------------------------------------------- |
| 0   | Foundations                    | done        | —               | `pyproject.toml`, lint/test/CI, base layout, README+ |
| 1   | VOD ingestion                  | in progress | 0               | `load_vod`, audio extraction, `cli ingest`           |
| 2   | Audio highlight detection      | not started | 1               | RMS-energy detector, candidate list                  |
| 3   | Horizontal clip generation     | not started | 2               | ffmpeg-based horizontal clips, CLI                   |
| 4   | Vertical clip generation       | not started | 3               | 9:16 clips (center-crop, then tracking)              |
| 5   | Speech-to-text                 | not started | 1               | `faster-whisper` ASR backend, transcript             |
| 6   | Speaker diarization            | not started | 5               | `pyannote` diarization, speaker-labeled segments     |
| 7   | LLM highlight scoring          | not started | 5               | LLM client, scored segments, score cache             |
| 8   | Multi-signal fusion            | not started | 2, 7            | unified ranked highlight list                        |
| 9   | Vision layer                   | not started | 3, 8            | scene detection, visual saliency, extended fusion    |
| 10  | Stable API + mature CLI        | not started | 8 (9 helpful)   | public `api/`, full CLI, mkdocs site                 |
| 11  | Web UI                         | not started | 10              | Gradio / FastAPI frontend                            |

## 6. Out of scope (for now)

To keep the project focused, the following are explicitly excluded from the
initial roadmap. They may be revisited later as separate workstreams.

- **Live / streaming analysis.** The pipeline is batch-only; real-time
  detection on a live stream is a different problem.
- **Auto-publishing.** No upload to YouTube / TikTok / Twitch; the tool
  produces files, the user publishes them.
- **Multi-language UI.** Transcription and LLM scoring support multiple
  languages, but the interface (CLI / Web UI) ships English-only first.
- **Cloud-hosted inference.** All ML runs locally by default. Cloud backends
  may be plugged in later via the existing interfaces, but no managed cloud
  service is part of the project itself.

## 7. Notes on the Definition of Done

A phase is **done** only when all of the following are true:

- All deliverables listed in the phase are implemented.
- Unit tests cover the new logic (`core/`) and pass in CI.
- The CHANGELOG entry for the phase is written.
- The phase summary table above is updated to reflect the new status.
- A demo (script or short README section) shows the new capability working
  end-to-end on a real VOD.

This keeps the public state of the project honest: a phase marked "done"
can actually be used.
