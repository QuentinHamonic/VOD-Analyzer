# Skills index

> Liste des skills disponibles pour le projet VOD Analyzer.
> Chaque skill est un dossier sous `.skills/` contenant un `SKILL.md`.
> L'IA charge cet index en début de session puis charge à la demande les SKILL.md pertinents pour la tâche.

---

## Workflow et méthode

| Skill | Quand l'utiliser |
|-------|------------------|
| [`git-workflow`](git-workflow/SKILL.md) | À chaque tâche — branches, commits, validation avant fin. |

## Qualité du code

| Skill | Quand l'utiliser |
|-------|------------------|
| [`python-quality`](python-quality/SKILL.md) | Tout code Python — Ruff (lint + format), mypy strict, type hints, nommage. |
| [`error-handling`](error-handling/SKILL.md) | Toute capture d'exception — pas d'`except: pass`, `raise from`, hiérarchie. |

## Sécurité

| Skill | Quand l'utiliser |
|-------|------------------|
| [`injection-prevention`](injection-prevention/SKILL.md) | Tout subprocess ffmpeg/ffprobe — shell=True banni, args en liste, paths validés. |
| [`input-validation`](input-validation/SKILL.md) | Tout argument CLI ou chemin de fichier provenant de l'utilisateur. |

## Tests

| Skill | Quand l'utiliser |
|-------|------------------|
| [`testing-python`](testing-python/SKILL.md) | Tests pytest — structure AAA, fixtures, tmp_path, synthetic WAV fixtures. |

## Spécifique VOD Analyzer

| Skill | Quand l'utiliser |
|-------|------------------|
| [`vod-analyzer-architecture`](vod-analyzer-architecture/SKILL.md) | Toute nouvelle fonctionnalité — règles de dépendance core/api/cli, où placer le code. |
| [`vod-analyzer-pipeline`](vod-analyzer-pipeline/SKILL.md) | Modification du pipeline ingest→detect→render — contrats entre étapes, types de données. |
| [`vod-analyzer-ffmpeg`](vod-analyzer-ffmpeg/SKILL.md) | Tout appel ffmpeg ou ffprobe — construction des commandes, presets, gestion d'erreur. |

---

## Conventions de cet index

- Une skill = un dossier `.skills/<nom>/` avec au minimum `SKILL.md`.
- `SKILL.md` commence par un frontmatter YAML : `name` + `description`.
- Le `description` dit **quand** la skill s'applique, pas seulement ce qu'elle est.

---

## Ajouter une nouvelle skill

1. Créer le dossier `.skills/<nom-kebab-case>/`.
2. Créer `SKILL.md` avec frontmatter complet et corps < 200 lignes.
3. Mettre à jour cet INDEX.
4. Commit dédié : `docs(skills): add <nom> skill`.
