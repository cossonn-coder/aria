# Sprint 57 — Tronçon 02 : occasions manquées avant les erreurs de Nico

Lire d'abord : `CLAUDE.md`, `docs/sprint57/00_etat.md`, `docs/sprint57/audit_classer_parties.md` §2.

## Objectif

1. Dans le choix des 4 miniatures, les **occasions manquées** passent avant les erreurs simples
   de Nico : erreur adverse non punie (sorte `b`), puis occasion explosive non jouée (sorte `d`),
   puis erreur de Nico (`a`), puis tournant (`e`), puis coup unique (`c`). Affichage toujours
   chronologique.
2. Une ligne 🔎 dans le bilan écrit par le code liste les occasions manquées de la partie.

## Fichiers à toucher (vérifiés au code)

- `chess_coach/analysis.py:525` `select_critical` : aujourd'hui groupes
  `(errors, explosives, turns, uniques)`, `errors` = a + b mélangées (`_critical_errors`, l. 511).
  Séparer b et a : ordre `(b, d, a, e, c)`, chaque groupe trié par score décroissant comme
  aujourd'hui ; docstring à mettre à jour.
- `chess_coach/analysis.py:688-695` `analyze` : le saut de `find_explosive` (log
  `chess_explosive skipped: %d errors fill the budget`) ne compte plus que les erreurs **b** :
  sauté seulement si les b remplissent à elles seules `_CRITICAL_BUDGET`.
- `execution/routers/chess_router.py:586` `_moves_line(summary, analysis)` : ajouter la ligne 🔎
  après la ligne `Erreurs : …` (avant `💥 Coups brillants`).
- Tests : `tests/chess_coach/test_chess_coach.py` (tests `select_critical` existants l. 160-280,
  certains à adapter si leur attendu dépendait de l'ancien ordre), `tests/execution/test_chess_router.py`.

## Comportement attendu — ligne 🔎

Absente s'il n'y a aucune occasion. Sinon, segments joints par ` · ` :

`🔎 Occasions manquées : erreur adverse non punie 13...Bg4? (joué 14.Nc3, meilleur 14.Qb3) · explosif 18.Bxh7+!? (joué 18.Re1)`

- **Erreurs adverses non punies** : sur toute la partie, même règle que `summarize`
  (`chess_coach/summary.py`, compteur `opponent_errors_punished`) : coup adverse à perte ≥ 20,
  réponse de Nico (demi-coup suivant) à perte ≥ 10. Toutes listées, ordre chronologique.
  Format : `erreur adverse non punie {coup adverse}? (joué {réponse de Nico}, meilleur {best_san de la réponse})`
  (labels via `_move_label`).
- **Explosifs** : `analysis.explosive` (toutes les occasions trouvées, retenues ou non) ; les 3 de
  plus fort `score`, puis affichés en ordre chronologique.
  Format : `explosif {coup explosif}!? (joué {coup joué})` (`critical.explosive.san`, `critical.ply.san`).
- Ligne écrite par le code, en notation anglaise comme le reste de `_moves_line`.

## Tests à ajouter (cas nominal)

- `select_critical` : une erreur `a` à forte perte + une `b` + un explosif `d` + 2 autres `a`
  → `b` et `d` retenues malgré une perte `a` plus forte.
- `analyze` ou la condition extraite : 4 erreurs `a` et 0 `b` → la recherche explosive n'est pas sautée
  (tester la condition, pas lancer Stockfish).
- `_moves_line` : une erreur adverse non punie + un explosif → ligne 🔎 attendue ; aucun → pas de ligne.

## Hors scope (ne pas faire)

- Pas de nouvelle détection, pas de changement de seuils (20 / 10, budget 4).
- Pas de changement des légendes de miniatures ni de `_KIND_FR`, pas d'ajout dans les faits du LLM.
- Pas d'optimisation de la durée de `find_explosive` (#189) : durée mesurée au run live.
- Pas de nouveau champ de fiche.

## Critère de fin

`pytest tests/ -q` vert ; tests ci-dessus ajoutés.
