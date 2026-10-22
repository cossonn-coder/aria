# Sprint 29 — Tronçon 02 : tagueur de motifs tactiques (module pur)

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_sprint29.md` §1,
`docs/sprint29/ref/` (cook.py, util.py, model.py de lichess-puzzler, AGPL-3.0).

## Objectif

Nouveau module **pur** `chess_coach/motifs.py` : à partir d'une position et d'une
ligne de coups, rendre la liste des motifs tactiques présents, à la manière des
thèmes de puzzles Lichess. Aucun branchement dans ce tronçon (fait au tronçon 03).

## Interface

```python
def tag_motifs(fen_before_opponent: str, opponent_uci: str, line_uci: list) -> list[str]
```

- `fen_before_opponent` : position AVANT le coup adverse qui précède le coup de Nico.
- `opponent_uci` : ce coup adverse (joué dans la partie).
- `line_uci` : meilleur coup de Nico puis la suite de la PV (déjà coupée par l'appelant).
- Rend des identifiants (clés anglaises stables, ex. `"fork"`, `"pin"`, `"smotheredMate"`).
  Ce format reproduit exactement le `Puzzle` Lichess : partie qui démarre avant le coup
  adverse, `mainline = [coup adverse, coup de Nico, réponse, …]`, `pov` = camp de Nico
  (`not game.turn()` au départ). Construire un `chess.pgn.Game` depuis le FEN (en-têtes
  `SetUp`/`FEN`) et y ajouter la ligne : les fonctions de `cook.py` s'appliquent telles quelles.

## Portage

- Porter `cook.py` + les fonctions utilisées de `util.py` dans `chess_coach/motifs.py`
  (un seul fichier). En tête : mention de la source (URL lichess-puzzler, fichiers) et
  de la licence AGPL-3.0. Commentaires en français pour ce qui est ajouté/adapté ;
  le code porté garde sa logique.
- Motifs à rendre (et seulement eux) : `hangingPiece` (« gain de matériel »), `fork`,
  `pin`, `skewer`, `discoveredAttack`, `sacrifice`, `trappedPiece`, `advancedPawn`,
  `attackingF2F7`, `capturingDefender`, `doubleCheck`, `exposedKing`, `attraction`,
  `clearance`, `collinearMove`, `deflection`, `interference`, `intermezzo`, `xRayAttack`,
  et les mats nommés ci-dessous. Écarter les tags d'évaluation, de longueur, de finale,
  de côté d'attaque, `quietMove`, `defensiveMove`, `castling`, `enPassant`, `promotion`,
  `underPromotion`, `mate`/`mateInN` (un mat sans motif nommé rend `"mate"` seul,
  pour que le classement « Mats » le compte).
- `cook()` utilise `puzzle.cp` uniquement pour les tags d'évaluation : passer 0 ou
  supprimer ce bloc. `puzzle.id`/`log()` : supprimer.
- Mats déjà couverts par cook.py : étouffée (`smotheredMate`), couloir (`backRankMate`),
  Anastasia, hameçon (`hookMate`), arabes, Boden, deux fous, Cozio (`dovetailMate`).
- **Mats à écrire** (sur la position de mat finale, mêmes conventions que les détecteurs
  de cook.py) : arbalète (`balestraMate`), deux tours (`blindSwineMate` si 7e rangée,
  sinon `twoRooksMate` — ligne/échelle), mat en coin (`cornerMate`), épaulettes
  (`epauletteMate`), mise en boîte (`killBoxMate`), Pillsbury (`pillsburysMate`),
  Morphy (`morphysMate`), opéra (`operaMate`), guéridon (`swallowstailMate`), triangle
  (`triangleMate`), Vukovic (`vukovicMate`). Définitions : celles des pages de thèmes
  Lichess / Wikipédia ; documenter chaque définition retenue en une ligne de commentaire.
  Ordre de priorité dans `cook()` : les mats de cook.py d'abord, puis les nouveaux ;
  un seul mat nommé par ligne.

## Tests à ajouter (cas nominal) — `tests/chess_coach/test_motifs.py`

Une position construite à la main par motif principal : fourchette de cavalier,
clouage, enfilade, attaque à la découverte, mat étouffé, mat du couloir, et un des
nouveaux mats (au choix). Chaque test vérifie que le motif attendu est dans la liste.
Pas de test exhaustif des 37 motifs.

## Hors-scope (NE PAS faire)

- Aucun import de `chess_coach.motifs` ailleurs (tronçon 03).
- Pas de Stockfish dans ce module ; pas de logger nécessaire.
- Ne pas copier `docs/sprint29/ref/` dans le code tel quel (un seul module porté).

## Critère de fin

`pytest tests/ -q` vert ; `chess_coach/motifs.py` sans import mémoire / LLM / exécution.
