# Sprint 29 — Tronçon 12 : meilleur coup = coup le plus rare

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_run_live_11.md` §2.

## Objectif (décision Nico, Q1 A'')
Le « meilleur coup » de Nico n'est plus le coup qui pose problème à l'adversaire
(score de fautes provoquées : reprises, parades d'échec, prises de pion au run live 11),
mais **le coup le plus rare** : parmi les coups de Nico **après le coup 10** et de
**perte ≤ 2** pts de % de gain, celui dont la probabilité Maia-2 (Elo de Nico) **du coup
joué** est la plus faible. Affichage dans la ligne 🎯 :
`meilleur coup 16...Nd5 (trouvé par 9 % des joueurs de ton niveau)`.

## Fichiers (vérifiés au code, HEAD `1f5c2c4`)
- `chess_coach/analysis.py` : `PlyAnalysis` → nouveau champ `played_p: float | None = None`
  (probabilité Maia du coup joué). `GameAnalysis.best_move` et l'appel
  `find_best_move(...)` dans `analyze` (l. ~456-469) supprimés.
- `chess_coach/difficulty.py` : `assign_difficulty` calcule aussi P(coup joué) dans la
  **même passe batchée** (`_probabilities` prend déjà des couples (fen, uci) : passer
  (fen_before, best_uci) et (fen_before, uci) ensemble) et remplit `p.played_p` pour les
  mêmes coups (après le coup 10). Maia en échec → `played_p` reste None partout.
- `chess_coach/explosive.py` : supprimer la section « Coup qui pose problème »
  (`_BEST_LOSS_MAX`… `_BONUS`, `BestMove`, `_problem_score`, `find_best_move`) et sa
  mention dans l'en-tête du module.
- `chess_coach/summary.py` (l. ~161-166) : meilleur coup choisi ici, depuis les plies
  (pure) : coups de Nico avec `played_p` non None et `loss ≤ 2`, min de `played_p`.
  Clés : `best_move` (label, inchangé) et `best_move_p` (arrondi 3 décimales) ;
  `best_defense`, `best_defense_p`, `best_reply_played` supprimées. Aucun candidat → None.
- `execution/routers/chess_router.py` `_moves_line` (l. ~236) : partie meilleur coup =
  `meilleur coup {label} (trouvé par {p×100:.0f} % des joueurs de ton niveau)`.

## Tests
- Supprimer `test_problem_score_counts_human_faults` et l'import `_problem_score`
  (`tests/chess_coach/test_chess_coach.py`).
- `tests/chess_coach/test_summary.py:81` : adapter (`best_defense` n'existe plus).
- 1 test nominal summary : trois plies Nico (played_p 0,6 perte 0 ; 0,1 perte 1 ; 0,05
  perte 8) → `best_move` = le 2e, `best_move_p` = 0,1.
- Adapter les tests router qui construisent un `summary` avec les anciennes clés.

## Hors-scope
- Pas de réécriture des fiches existantes (pas de rétroactivité).
- Ne pas toucher à `find_explosive` ni à la difficulté affichée ailleurs.
- Pas de seuil de rareté minimal.

## Critère de fin
`pytest tests/ -q` vert ; `grep -rn "find_best_move\|best_defense\|_problem_score" --include=*.py . | grep -v venv` vide.
