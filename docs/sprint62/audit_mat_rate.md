# Sprint 62 — audit : mat raté non commenté (dette 62-1)

Date : 2026-11-20. Code lu : `chess_coach/analysis.py` (HEAD `88673aa`),
`execution/routers/chess_router.py` (`_caption`, `_line_end`, `_compared_lines`, bloc LLM).

## Cas réel

Partie du 2026-11-20 contre Loveyoulongtime69 (Modern Defense, Nico blancs, 1-0).
Après 9.e6+ fxe6 :

```
r n b . . . . r
p p p k p . b p
. . . . p . p .
. . . N . . . n
. . . . . B . .
. . . . . . . .
P P P . . P P P
. . . R K B N R
```

Stockfish (profondeur 22) : `#+2 10.Bb5+ c6 11.Nf6#`. Joué : 10.Nxc7+ (+467).

Log du run (journalctl 07:11:40) :
`chess_analysis OK plies=107 nico=white source=header first_move=3
critical=['a:13.Be3', 'a:19.gxh5', 'd:20.Kxd1', 'd:35.Rd4+']`.
`first_move=3` : le coup 10 était éligible. Il a été écarté par le budget.

## Chemin de données

1. `analyze_game` (analysis.py:310) : `cp = score.relative.score(mate_score=_MATE_SCORE)`,
   `_MATE_SCORE = 100000`. `pv_mate = best_score.is_mate() and best_score.mate() > 0` est
   stocké sur le `PlyAnalysis`. La longueur du mat (`best_score.mate()`) n'est **pas** stockée.
2. `_win(cp)` (analysis.py:202) borne à `_CP_CLAMP = 1000` avant la formule Lichess :
   mat → 97,5 %, +467 → 84,8 %. `loss = 12,7` → `_quality` = `inaccuracy`.
3. `_critical_errors` (analysis.py:516) : `loss ≥ 10` → sorte a, `score = loss = 12,7`.
4. `select_critical` (analysis.py:538), budget 4 et ordre des groupes :
   `worst` (13.Be3, 31) → `missed` b (aucune) → `sure` d (20.h6, 35.Kb2) →
   `plain` a (19.gxh5, 30 ; budget atteint) → 10.Nxc7+ (12,7) écarté.

Le mat raté n'est donc qu'une imprécision parmi d'autres, rangée par perte en points.
Rien dans la sélection ne connaît le mat.

## Ce qui marche déjà si la position est retenue

- `assign_forcing_lines` : `forcing_line` suit les coups forcés (échecs). La suite du meilleur coup
  va jusqu'à `11.Nf6#`.
- `_line_end` (chess_router.py:467) écrit `→ mat` si la suite finit sur un mat.
- La consigne LLM autorise un mat « s'il figure dans une ligne ».
- `point_of` (pointe du sprint 61) ne traite pas le mat (dette 61-3) : pas de ligne « Pointe »,
  ce qui n'est pas bloquant.

## Ce qui serait trompeur même si la position était retenue

`_caption` (chess_router.py:876), sorte a/b : `évaluation : 97 % → 85 % (−13 pts)`. Rater un mat en 2
se lit comme une petite imprécision.

## Pistes écartées

- Changer `_win` / `_CP_CLAMP` pour que le mat vaille 100 % : il resterait 15 pts. Ça décalerait aussi
  la précision, les qualités et les Elo de compétence de toutes les parties.
- Changer la qualité du coup (`blunder`) : touche les statistiques et la progression. Ce n'est pas
  nécessaire pour commenter la position.

## Piste retenue (à arbitrer)

- Stocker la longueur du mat du meilleur coup (`mate_in`, en coups de Nico) sur `PlyAnalysis`.
- Mat raté = coup de Nico, `pv_mate`, `mate_in ≤ N`, coup joué qui ne garde pas de mat pour Nico
  (score après le coup différent d'un mat).
- `select_critical` : nouveau groupe en tête du budget, toujours retenu.
- `_caption` : `mat en 2 manqué` à la place de la ligne en pts.
