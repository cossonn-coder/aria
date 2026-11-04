# Sprint 48 — état vivant

**Phase courante** : sprint clos (tag `sprint-48`).
**Branche** : `feat/sprint48-miniatures-parties` (depuis `main`).

Sprint sans `/conception` ni kickoff de tronçon : demande directe de Nico, le 2026-11-04.

## Décisions arrêtées

- Nico : pas de miniature sur les 6 premiers coups du Göring ; idéalement, aucune tant qu'une ouverture rejoue les mêmes coups et qu'il n'y a pas de nouveauté.
- Nico : l'idée du Göring est d'ouvrir les colonnes c et d et les diagonales a1-h8 et a2-g8 pour attaquer ; reprendre en d4 du cavalier, c'est la Scotch normale.
- Nico : `/parties` montre toutes les parties du jour, le bilan et les statistiques d'ouvertures.
- Nico : icône de pion pour la page de l'échiquier.
- Par défaut annoncés à Nico : un coup est connu s'il a été joué dans ≥ 2 autres parties après exactement les mêmes coups ; plancher du Göring seulement avec les blancs ; jour = date du PGN, sinon jour d'analyse.

## Livré

- `first_shown_move` (`chess_coach/analysis.py`), fiches lues par `_past_games` (`execution/routers/chess_router.py`).
- Consignes LLM : idée du Göring ; aucune entrée « Position » quand aucune position n'est retenue.
- `parties_text` (`interfaces/meta_commands.py`), icône SVG intégrée à `interfaces/board/index.html`.
- 491 tests verts.

## Run live

« Tout est nickel » par Nico, 2026-11-04 [validation globale, sans détail par point].

## Dettes

- Nouvelles, inscrites au kickoff du sprint 49 : #173, #174, #175.
- #81 (déviations de répertoire) : partiellement résolue, pour le choix des miniatures seulement.

## §REPRISE

Sprint clos. Suite : `/conception sprint 49` (`docs/sprint49/context_kickoff_sprint_49.md`).
