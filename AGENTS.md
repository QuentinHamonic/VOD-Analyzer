# AGENTS.md

> Règles transverses du projet VOD Analyzer.
> Ce fichier est court par design (< 200 lignes). Les règles détaillées vivent dans `.skills/`.
> Toute IA contributrice lit ce fichier + `.skills/INDEX.md` en début de session, puis charge les skills pertinents à la demande.

---

## 1. Principes non négociables

Ces principes tranchent les cas non couverts par une skill précise.

1. **Lisibilité avant performance prématurée** — pas d'optimisation sans mesure.
2. **Explicite avant implicite** — pas de magie cachée.
3. **Tests avant confiance** — le test est la seule preuve.
4. **Documentation avant mémoire** — ne pas dépendre de la mémoire de quiconque.
5. **Petites tâches** — une tâche tient en une session de travail.
6. **YAGNI** — pas d'abstraction sans deux usages réels.
7. **Sécurité par défaut** — toute entrée externe est hostile.
8. **Observabilité par défaut** — un chemin critique est instrumenté dès sa création.
9. **Cohérence** — le projet ressemble à un projet écrit par une seule personne.
10. **Le code est la vérité, la doc l'explique** — si divergence, le code gagne, la doc se met à jour.
11. **Dégradation gracieuse** — ffmpeg absent ou fichier invalide ne crash pas le système, il se dégrade avec un message clair.
12. **Commentaires sur l'intention** — commenter le *pourquoi* non évident (contrainte cachée, contournement, invariant subtil), jamais le *quoi*.
13. **`core/` ne dépend jamais de `cli/` ni de `api/`** — la dépendance va toujours du haut (cli/api) vers le bas (core). Violer cette règle casse la réutilisabilité.
14. **Une fonctionnalité, ses tests** — toute fonctionnalité nouvelle ou correction comportementale doit ajouter ou mettre à jour au moins un test pertinent ; si ce n'est pas possible, documenter explicitement pourquoi.
15. **Clôture roadmap explicite** — quand une phase de `ROADMAP.md` est terminée, la marquer done, expliquer ce qui a été livré, citer les tests, et signaler les limites restantes.

---

## 2. Workflow obligatoire

- **Branche dédiée** depuis `main` propre pour chaque tâche.
- **Ne jamais merger dans `main`** — le mainteneur s'en occupe.
- **Ne jamais push** sans demande explicite.
- **Annoncer toute commande Git modifiante** avant exécution.
- **Conventional Commits** : `feat(scope): summary` / `fix(scope): summary` / `docs(scope): ...`
- **Avant fin de tâche** : tests passent, `pre-commit run --all-files` passe, doc à jour, pas de secret commité.

Détails dans `.skills/git-workflow/SKILL.md`.

---

## 3. Comment naviguer les skills

1. **Lire `.skills/INDEX.md`** en début de session — liste les skills disponibles avec leur description.
2. **Pour chaque tâche**, identifier les skills pertinents via leur `description` et **charger leur `SKILL.md`** avant de coder.
3. **Plusieurs skills peuvent s'appliquer** à une même tâche — les charger toutes.
4. **En cas de doute** sur l'applicabilité d'une skill, la charger.

Exemples :
- Tâche "ajouter un nouveau renderer (vertical)" → charger `vod-analyzer-architecture`, `vod-analyzer-ffmpeg`, `vod-analyzer-pipeline`, `testing-python`.
- Tâche "ajouter un paramètre CLI" → charger `input-validation`, `injection-prevention`, `python-quality`.
- Tâche "modifier le détecteur audio" → charger `vod-analyzer-pipeline`, `testing-python`.
- Tâche "ajouter une dépendance" → vérifier la phase roadmap, documenter dans `pyproject.toml`.
- Tâche "corriger un subprocess ffmpeg" → charger `injection-prevention`, `error-handling`, `vod-analyzer-ffmpeg`.

---

## 4. Quand s'arrêter et demander confirmation

L'IA **ne procède pas** sans validation explicite du mainteneur dans ces cas :

1. Changement d'architecture (nouveau composant majeur, nouveau module `core/`).
2. Ajout d'une dépendance runtime non triviale.
3. Suppression de code ou de fichiers non explicitement demandée.
4. Toute opération sur la branche `main`.
5. Tout push vers un remote.
6. Modification d'un `SKILL.md` ou d'`AGENTS.md`.
7. Toute solution qui enfreint une règle d'une skill — demander avant d'enfreindre.
8. Travail découvert hors scope de la tâche initiale.
9. Utilisation de `shell=True` dans un subprocess — toujours challenger d'abord.

Format : annoncer ce qu'on s'apprête à faire, pourquoi c'est sensible, proposer, attendre validation.

---

## 5. Definition of Done

Une tâche est terminée si **toutes** ces conditions sont remplies :

- [ ] Comportement attendu fonctionne.
- [ ] Tests pertinents ajoutés ou mis à jour.
- [ ] `pytest` passe.
- [ ] `pre-commit run --all-files` passe (ruff, mypy, checks).
- [ ] Documentation impactée à jour (`README.md`, `ROADMAP.md`, `CHANGELOG.md`).
- [ ] Toute phase roadmap terminée est marquée done dans `ROADMAP.md` avec résultat, preuves/tests et commit de référence.
- [ ] Aucun secret, `.env`, cache ou artefact inutile commité.
- [ ] Limites connues documentées si solution incomplète.
- [ ] Commit Conventional Commits propre.
- [ ] Aucune règle de skill silencieusement enfreinte.

---

## 6. Faire évoluer les skills

- Une skill évolue par commit dédié : `docs(skills): refine vod-analyzer-ffmpeg on preset handling`
- Une skill obsolète est marquée `status: deprecated` dans son frontmatter avant suppression.
- Une nouvelle skill demande une mise à jour de `.skills/INDEX.md`.
- Toute modification d'une skill est annoncée au mainteneur avant exécution (cf. section 4).
