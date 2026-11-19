# Sprint 61 — tronçon 01 : calcul de la pointe et des défenses réfutées

## Objectif

Pour chaque erreur de Nico (positions critiques de sorte a / b, celles dont
`best_line_san` est rempli), calculer à partir de la suite du meilleur coup :
1. **le gain** : le coup de Nico où se fait le gain matériel final, et la pièce gagnée ;
2. **la préparation** : le coup de Nico qui précède ce gain, et le clouage qu'il crée ;
3. **le mécanisme** : pièce adverse amenée sur la ligne du clouage, défenseur éliminé ;
4. **jusqu'à 3 défenses réfutées** : réponses humaines probables (Maia) après le coup
   préparatoire, chacune avec sa réfutation Stockfish et, si elle existe, la reprise
   naturelle qui perd.

Ce tronçon ne produit que des données (aucun texte, aucune consigne : tronçon 02).

Cas de référence (audit `docs/sprint61/audit_pointe_combinaison.md` §1) :
FEN `r1b1k2r/1pq1bppp/p4n2/3p4/1n1P4/3B1N2/2P1QPPP/RNB1R1K1 w kq - 0 12`, Nico blancs,
suite du meilleur coup `Qxe7+ Qxe7 Rxe7+ Kxe7 Ba3 Be6 Bxb4+ Kd7`.
Attendu : gain index 6 (`Bxb4+`, gagne `Nb4`), préparation index 4 (`Ba3`), clouage
`Nb4` sur `Ke7`, roi amené par index 3 (`Kxe7`), défenseur éliminé `Be7` pris à l'index 0
(`Qxe7+`). Défense Maia attendue : `a5` (93 % à Elo 1711, 1 position mesurée) ; réfutation
commençant par `Bxb4+` ; reprise naturelle `axb4` suivie de `Rxa8`.

## Fichiers

- **Nouveau `chess_coach/combination.py`** : fonction pure (python-chess, sans moteur).
- `chess_coach/analysis.py` : champs de `CriticalPosition` (l. 115) et fonction
  `assign_defenses`, appelée dans `analyze` (l. 685) après `assign_human_lines`.
- Tests : `tests/chess_coach/test_combination.py` (nouveau).

## Comportement attendu

### `combination.point_of(fen: str, line_san: list, nico_color: str) -> dict | None`

Valeurs : P 1, N 3, B 3, R 5, Q 9, K 0. Solde = matériel de Nico − matériel adverse.
- `initial` = solde dans `fen`, `final` = solde après le dernier coup de la ligne.
  `final <= initial` → `None` (pas de gain matériel : mat ou gain positionnel, hors scope).
- **gain** = le plus petit index `i` d'un coup de Nico **qui prend** tel que le solde
  après `i` et après chaque coup suivant est `>= final`. Aucun → `None`.
- **préparation** = `gain - 2` si `gain >= 2`, sinon `None`.
- **clouage** : si préparation, dans la position après le coup préparatoire, la pièce prise
  au coup de gain (case d'arrivée du gain) est clouée sur son roi (`board.is_pinned`) →
  `(libellé pièce, libellé roi)`, ex. `("Nb4", "Ke7")`. Sinon `None`. Clouage absolu seul.
- **amené** : si clouage, index du coup adverse de la ligne (avant la préparation) qui a
  amené le roi sur sa case ; sinon `None`.
- **défenseur** : premier coup de Nico (avant le gain) qui prend une pièce adverse qui, dans
  la position avant cette prise, défendait la case de la pièce gagnée (`board.attackers`)
  → `(index, libellé pièce prise)`. Sinon `None`.

Retour : `{"gain": int, "won": str, "prep": int | None, "pin": tuple | None,
"brought": int | None, "defender": tuple | None}`. Libellés au format du router :
`Nf3`, `pion e5` (même convention que `_square_label`, `execution/routers/chess_router.py:234` ;
ne pas importer le router depuis `chess_coach`, réécrire la petite fonction).

### `analysis.assign_defenses(critical, engine_path, opponent_elo, models_dir)`

- Pour chaque position de sorte a / b avec `best_line_san` : `c.point = point_of(...)`.
- Si `c.point` et `c.point["prep"]` : position après `best_line_san[:prep + 1]` (trait à
  l'adversaire). Réponses Maia : `reply_distribution([fen], opponent_elo, models_dir)`
  (`chess_coach/difficulty.py:98`, une passe batchée pour toutes les positions), sans le coup
  joué par la ligne à `prep + 1`, **3 au plus**, dans l'ordre de probabilité.
- Évaluation : une analyse MultiPV restreinte à ces coups (`root_moves`, comme
  `_human_replies`, `chess_coach/explosive.py:251`), via `run_on_engines`
  (`analysis.py:280`), `Limit(time=0.3)`. Ligne de réfutation : 4 demi-coups après la
  défense au plus.
- **Reprise naturelle** : si le premier coup de Nico de la réfutation est une prise, dans la
  position après cette prise, `explosive._natural_capture(board, case)` ; si elle existe et
  n'est pas le coup suivant de la réfutation, une analyse de la position après cette reprise
  donne le coup de Nico qui répond. Enregistrer `(reprise SAN, réponse SAN)`.
- Champs ajoutés à `CriticalPosition` : `point: dict | None = None`,
  `defenses: list = field(default_factory=list)` ; chaque défense :
  `{"san": str, "p": float, "line_san": list, "recapture": tuple | None}`
  (`line_san` commence par la défense).
- Elo : celui de l'adversaire (il défend), `DEFAULT_ELO` s'il manque.
- Sans Maia (`maia_models_dir is None`) ou si Maia échoue : `point` rempli, `defenses` vide,
  `log.exception("maia_defenses FAILED")`, l'analyse continue (même tolérance que
  `assign_human_lines`).

## Tests (cas nominal)

1. `point_of` sur le cas de référence → valeurs attendues ci-dessus.
2. `assign_defenses` avec `reply_distribution` et le moteur remplacés par des doublures
   (monkeypatch) : une défense `a5` enregistrée avec sa reprise `axb4` / `Rxa8`.

## Hors scope

- Aucun texte, aucune modification de `chess_router.py` (tronçon 02).
- Pas de clouage relatif, pas de mat, pas de sortes c / d / e.
- Pas de nouvelle requête mémoire, pas de changement des motifs (`motifs.py`).

## Critère de fin

`pytest tests/ -q` vert ; sur le cas de référence, `point_of` rend les valeurs attendues.
