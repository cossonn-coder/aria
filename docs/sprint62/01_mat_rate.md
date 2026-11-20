# Sprint 62 — tronçon 01 : mat raté, toujours commenté

## Objectif

Quand le meilleur coup de Nico mate de force en 7 coups ou moins (coups de Nico) et que le
coup joué ne garde pas de mat, la position est **toujours** une miniature, la **première**
retenue du budget, et sa légende dit « mat en N manqué » au lieu de la perte en points.

Audit : `docs/sprint62/audit_mat_rate.md` (chemin de données complet, cause : `_win` borne à
`_CP_CLAMP = 1000`, le mat ne vaut que 12,7 pts de perte, écarté par le budget de 4).

Cas de référence (partie 2026-11-20, Nico blancs) :
FEN `rnb4r/pppkp1bp/4p1p1/3N3n/5B2/8/PPP2PPP/3RKBNR w K - 0 10`, joué `10.Nxc7+`,
meilleur `10.Bb5+ c6 11.Nf6#` (Stockfish : mat en 2). Vérifier la FEN au début du tronçon
en rejouant `1.e4 g6 2.d4 Bg7 3.Nc3 d6 4.Bf4 Nf6 5.e5 dxe5 6.dxe5 Qxd1+ 7.Rxd1 Nh5 8.Nd5 Kd7
9.e6+ fxe6`.

## Fichiers

- `chess_coach/analysis.py` : `PlyAnalysis` (l. 72), `analyze_game` (l. 310),
  `_critical_errors` (l. 515), `select_critical` (l. 535), `forcing_line` /
  `assign_forcing_lines` (l. 617-649).
- `execution/routers/chess_router.py` : `_caption` (l. 876), bloc de données LLM des positions
  (l. ~1310, liste `lines += [...]`).
- Tests : `tests/chess_coach/test_chess_coach.py` (style des tests `select_critical` existants).

## Comportement attendu

1. **Donnée** : nouveau champ `PlyAnalysis.missed_mate: int | None = None`, rempli dans
   `analyze_game` : N = `best_score.mate()` si le meilleur coup mate pour le trait
   (`> 0`), N ≤ 7 (constante `_MISSED_MATE_MAX = 7`), et le coup joué ne garde pas de mat
   (`cp_after` est un score de mat pour le trait seulement s'il est ≥ `_MATE_SCORE - _CP_CLAMP` ;
   le mat donné par le coup joué lui-même donne `cp_after = _MATE_SCORE`, donc pas raté).
   Calculé pour les deux camps, comme les autres champs.
2. **Sélection** : `_critical_errors` retient aussi un coup de Nico à `missed_mate` même si
   `loss < 10` (sorte a / b selon la règle existante). `select_critical` : nouveau groupe
   « mats ratés » **avant** `worst`, trié par N croissant. Le filtre `first_move` reste.
   Le reste de l'ordre ne change pas.
3. **Suite du meilleur coup** : pour une position à `missed_mate`, `best_line_san` va
   jusqu'au mat (dernier coup en `#`), même au-delà de `_FORCING_MAX` et même sur un coup
   calme (ex. `Qh5` dans un sacrifice grec). Borne : `2 * N - 1` demi-coups, réanalyse si la
   PV moteur est trop courte (comme `forcing_line`). `_line_end` affiche alors déjà « → mat ».
4. **Légende** : sortes a / b avec `missed_mate` : `évaluation : …` remplacé par
   `mat en N manqué`. Ex. : `Position 1 — coup 10 (blancs) : joué … 10.Nxc7+, meilleur 🟢
   10.Bb5+, mat en 2 manqué`.
5. **Données LLM** : pour ces positions, une ligne `  mat en N manqué : le meilleur coup mate
   de force` dans le bloc de la position. La consigne n'est pas modifiée.

## Tests (cas nominal)

- `analyze_game` n'est pas testable sans moteur : tester la règle de remplissage si elle est
  extraite en petite fonction pure, sinon seulement la sélection.
- `select_critical` : 5 erreurs à perte ≥ 30 + un ply à `missed_mate=2` et `loss=12` →
  le ply mat est retenu, en première position du budget (ordre chronologique en sortie).
- `_caption` : position a avec `missed_mate=2` → contient « mat en 2 manqué », pas « pts ».
- `forcing_line` (ou sa variante mat) sur la FEN de référence avec `["f1b5"]` et un moteur
  factice → finit par `Nf6#`.

## Hors scope (ne PAS faire)

- Ne pas toucher `_win`, `_CP_CLAMP`, `_quality`, la précision, la progression, les Elo :
  la qualité du coup reste celle calculée (décision Nico 2026-11-20).
- Ne pas modifier la ligne « pire coup » du résumé (`chess_coach/summary.py`) : dette 62-11.
- Pas de « Pointe » pour le mat (`combination.point_of`, dette 61-3).
- Pas de changement à la consigne LLM ni au suivi Telegram (dette 62-2).

## Critère de fin

`pytest tests/ -q` vert ; les 3 tests ci-dessus passent.
