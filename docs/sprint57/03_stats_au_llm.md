# Sprint 57 — Tronçon 03 : statistiques d'échecs dans le contexte LLM (dette #209)

Lire d'abord : `CLAUDE.md`, `docs/sprint57/00_etat.md`, `docs/sprint57/audit_classer_parties.md` §3.

## Objectif

« Quelle est ma meilleure ouverture avec les blancs ? » : le LLM répond à partir des chiffres
calculés par le code, pas d'une invention. Sur une question d'échecs, le contexte LLM reçoit,
après la liste des parties (sprint 56), une section de statistiques.

## Fichiers à toucher (vérifiés au code)

- `chess_coach/summary.py:347` `games_context_section(games, n)` (module pur) : ajouter les
  statistiques à la suite, ou une fonction sœur appelée au même endroit.
- `execution/routers/llm_router.py:332-341` : le seul point d'injection (`chess_games_context`).
- `execution/routers/llm_router.py:81` `_CHESS_WORDS` : **ajouter `ouvertures?`**. Constat de
  conception : la question de #209 (« quelle est ma meilleure ouverture avec les blancs ? ») ne
  contient aucun mot-clé actuel → ni liste ni statistiques injectées. Le test porte sur cette phrase.
- Sources à réutiliser : `chess_coach/player_model.py:160` `opening_stats(games)`,
  `chess_coach/level.py:18` `performance(games)`.
- Tests : `tests/chess_coach/test_summary.py`.

## Comportement attendu

Section calculée sur **toutes** les fiches (pas seulement les n listées) :

```
[Statistiques d'échecs — calculées par le code sur 300 fiches]
Performance Elo : <perf> (<n> parties à issue et Elo adverse connus)
Ouvertures jouées au moins 3 fois (groupe, couleur : V / N / D — % de victoires [parties]) :
Göring Gambit (blancs) : 20 V, 0 N, 17 D — 54 % [37 parties]
…
```

- Ouvertures : `opening_stats(games)`, seulement les entrées à ≥ 3 parties, de la plus jouée à la
  moins jouée ; même format de ligne que `/ouvertures` (`interfaces/meta_commands.py:255`
  `_opening_stat_lines`) mais **sans importer `interfaces/`** depuis `chess_coach/` ni depuis
  `llm_router` (couplage, cf. #204) : réécrire la ligne (une f-string).
- Performance : ligne omise si `performance(games)` est `None`.
- Taille cible ≈ 2 500 car. sur le palace actuel (≈ 35 ouvertures).

## Tests à ajouter (cas nominal)

- Fiches factices : une ouverture à 3 parties et une à 2 → seule la première apparaît ;
  ligne de performance présente.
- `mentions_chess_games("quelle est ma meilleure ouverture avec les blancs ?", [])` → vrai.

## Hors scope (ne pas faire)

- Pas de réduction de la liste des 20 parties ni du plafond Groq (#211).
- Pas de modification du prompt AnalystAgent ni des règles d'honnêteté.
- Pas d'autre mot-clé que `ouvertures?` ; `requested_games_count` inchangé.
- `/ouvertures` inchangé.

## Critère de fin

`pytest tests/ -q` vert ; test ci-dessus ajouté.
