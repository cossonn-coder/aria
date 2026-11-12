# Sprint 57 — Tronçon 01 : classement 🏅 par catégorie (cadence × longueur)

Lire d'abord : `CLAUDE.md`, `docs/sprint57/00_etat.md`, `docs/sprint57/audit_classer_parties.md` §1.

## Objectif

Dans la dernière ligne du bilan d'une partie analysée, le rang de la précision **sur toutes
les fiches** est remplacé par le rang **parmi les fiches de même catégorie** (même cadence et
même longueur). Les segments « aujourd'hui » et « en <ouverture> (<couleur>) » ne changent pas.

Avant : `🏅 Précision 86 % : 12e sur 300 · 2e sur 3 aujourd'hui · 5e sur 37 en Göring Gambit (blancs)`
Après : `🏅 Précision 86 % : 12e sur 102 en rapide, partie moyenne (26-40 coups) · 2e sur 3 aujourd'hui · 5e sur 37 en Göring Gambit (blancs)`

## Fichiers à toucher (vérifiés au code)

- `chess_coach/level.py` (module pur, déjà `accuracy_rank`) : ajouter le calcul de catégorie.
- `execution/routers/chess_router.py:563` `_rank_line(summary, games)` : 1er segment.
- Tests : `tests/chess_coach/test_level.py`, `tests/execution/test_chess_router.py:1046`
  (`test_rank_line_gives_overall_day_and_opening_ranks`, à adapter).

## Comportement attendu

- **Longueur** en coups = `(n_plies + 1) // 2` (champ `n_plies`, présent sur toutes les fiches ;
  ne PAS utiliser `nico_moves`, absent de 154 fiches). Courte ≤ 25, moyenne 26-40, longue > 40.
  Libellés : `partie courte (≤ 25 coups)`, `partie moyenne (26-40 coups)`, `partie longue (> 40 coups)`.
- **Cadence** depuis `time_control` (ex. `"600"`, `"300+3"`, `""`) : durée estimée
  = base + 40 × incrément (règle Lichess) ; < 180 s `bullet`, < 480 s `blitz`, < 1500 s `rapide`,
  sinon `classique`. Vide ou illisible (`"-"`, `"?"`, format inattendu) → `cadence inconnue`.
- Catégorie d'une fiche = (cadence, longueur). Le segment 1 classe la précision parmi les
  fiches de même catégorie (partie courante incluse, comme aujourd'hui), via `accuracy_rank`.
  Segment toujours affiché, même « 1re sur 1 ».
- Texte du segment : `{rang} sur {total} en {cadence}, {libellé longueur}` (ex. « en rapide,
  partie moyenne (26-40 coups) » ; « en cadence inconnue, partie courte (≤ 25 coups) »).
- `summary` (sortie de `summarize`) porte déjà `n_plies` et `time_control` ; les fiches aussi.

## Tests à ajouter (cas nominal)

- Catégorie : `"600"` + 60 demi-coups → (rapide, moyenne) ; `"300+3"` → blitz ; `""` → cadence inconnue ;
  bornes 25/26 et 40/41 coups.
- `_rank_line` : fiches de catégories mélangées → le 1er segment ne compte que la catégorie de la partie.

## Hors scope (ne pas faire)

- L'échiquier web (`interfaces/board_interface.py:198`) garde son rang global.
- Pas de temps passé par coup, pas de catégorie dans les segments jour / ouverture.
- Pas de nouveau champ écrit dans les fiches.

## Critère de fin

`pytest tests/ -q` vert ; nouveau test de catégorie et `_rank_line` adapté.
