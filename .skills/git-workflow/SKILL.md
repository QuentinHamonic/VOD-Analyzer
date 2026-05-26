---
name: git-workflow
description: Use this skill for every task that involves Git operations. Covers branch creation from clean main, Conventional Commits formatting, the rule that AIs never merge into main or push to remote, end-of-task validation checklist (tests, pre-commit, secret scans), and how to announce Git-modifying commands before running them.
---

# Git workflow

## Branche principale

- `main` est stable et démontrable à tout moment.
- Aucun commit direct sur `main`. Toutes les modifications passent par une branche dédiée.

## Créer une branche

Vérifier d'abord que `main` est propre :

```bash
git status
git pull origin main
```

Si `main` ou le working tree n'est pas propre, **s'arrêter et demander au mainteneur**.

Nommage : `<type>/<courte-description-kebab-case>`

- `feat/vertical-clip-renderer`
- `fix/ffmpeg-audio-track-mapping`
- `docs/roadmap-phase4`
- `refactor/detect-module-interface`
- `test/render-horizontal-edge-cases`
- `chore/upgrade-librosa`

## Pendant le travail

- Une seule intention par commit.
- Pas de refactor opportuniste sur du code non lié à la tâche.
- Commits petits et lisibles.

## Messages de commit — Conventional Commits

```
<type>(<scope>): <résumé impératif en minuscules>

<corps optionnel — pourquoi, pas comment>

<footer optionnel — refs ROADMAP, breaking changes>
```

**Types autorisés** : `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`, `security`.

**Scopes courants** : `ingest`, `detect`, `render`, `cli`, `api`, `core`, `skills`.

**Règles** :
- Résumé < 72 caractères, impératif, minuscules.
- Corps explique le *pourquoi*, pas le *quoi*.
- Pas d'emoji sauf demande explicite.
- Un commit = une intention.

**Exemples valides** :
- `feat(render): add vertical center-crop renderer`
- `fix(ingest): handle VODs with no audio track`
- `test(detect): add synthetic multi-peak fixture`

## Annoncer toute commande Git modifiante

Avant `commit`, `branch`, `checkout`, `reset`, `rebase`, `merge`, `push`, `tag`, etc. : annoncer la commande exacte et son intention.

Pas d'annonce nécessaire pour les commandes en lecture (`status`, `diff`, `log`, `show`).

## Fin de tâche — checklist

Avant de marquer une tâche comme terminée :

1. `pytest` passe.
2. `pre-commit run --all-files` passe (ruff lint, ruff format, mypy, hooks).
3. `git diff --stat` montre uniquement les changements attendus.
4. `git status --short` ne montre aucun fichier non commité inattendu.
5. Aucun secret, token, clé API, `.env` n'est commité.
6. Documentation impactée à jour (`CHANGELOG.md`, `ROADMAP.md`, `README.md`).

## Ce que l'IA ne fait jamais

- **Merger dans `main`** — c'est le mainteneur.
- **Pousser sur un remote** — sauf demande explicite confirmée.
- **Forcer un push** (`--force`, `--force-with-lease`) — jamais.
- **Réécrire l'historique** d'une branche partagée — jamais.

## Livraison en fin de tâche

L'IA fournit au mainteneur :

- Nom de la branche.
- Liste des fichiers modifiés.
- Résultat des tests.
- SHA du commit final.
- Commande de merge recommandée.

Exemple :
```
Branche : feat/vertical-clip-renderer
Fichiers : src/vod_analyzer/core/render/vertical.py, tests/test_render_vertical.py
Tests : 14 passed, 0 failed
pre-commit : clean
SHA : abc1234
Merge : git checkout main && git merge --no-ff feat/vertical-clip-renderer
```
