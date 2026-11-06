# Sprint 51 — Audit : convertir une position gagnante, analyse du temps

Date : 2026-11-06. Code audité : `main` @ `4d3b3d9` (tag `sprint-50`).

## 1. Partie de référence

BaguetteChaussette (blancs, 1180) – dusha28 (1300), 2026-11-06, 600 s, 0-1 au temps.
Fiche prod : `chess_game_*` (id SQLite 1295, room `chess_goring-gambit`), `unconverted=1`,
`max_win_nico=92.6`, `min_win_nico=46.0`, 1 imprécision (55.b6), 0 erreur.

### 1.a Courbe (plies_json de la fiche)

- Nico ≥ 80 % sans interruption du coup 9 au coup 55 : **47 coups** [plies_json, 0,15 s / position].
- Plafond : 82-93 %, jamais au-delà. Formule Lichess : 85 % ↔ ≈ +4,7, 92 % ↔ ≈ +6,6 [calcul inverse de `_win`].
  Le % de gain sature : il ne mesure pas une progression dans cette zone.
- Pertes de Nico pendant la période : toutes < 5 pts sauf 55.b6 (−13,8). Aucune n'est une
  « erreur » au sens du code (seuil 10) → `select_critical` ne voit rien entre 23 et 54.

### 1.b Meilleur coup répété, non joué (calcul sur la fiche)

Meilleur coup du moteur ≠ coup joué, même SAN, sur la période ≥ 80 % :

| Coup du moteur | Proposé aux coups | Joué au coup | Concept |
|---|---|---|---|
| Kd3 | 31, 32, 33, 35 | 37 | activer le roi |
| b5 | 43, 44, 45, 47, 48 | 52 | pousser le pion passé |
| Nd5 | 34, 41, 42 | 51 | (cavalier) |
| Nc2 | 17, 37, 38, 50 | 42 | dispersé, pas une idée suivie |

Adversaire : son meilleur coup `g5` revient 9 fois de 27 à 52 (majorité de l'aile roi).

### 1.c Horloge

- PGN collé au run (stocké en `aria_conversation`) : **aucun `%clk`**. Cause de #170 : la
  copie chess.com sans l'option horodatage. Nico a recollé la même partie avec
  `[%clk …][%timestamp …]` (2026-11-06) : `python-chess` lit `node.clock()` même
  quand le commentaire est coupé en fin de ligne [vérifié sur un extrait].
- L'API publique `api.chess.com/pub/player/<pseudo>/games/2026/11` renvoie aussi le PGN avec
  `%clk` (4 parties sur 4) [1 appel] — piste #83, pas nécessaire si Nico colle avec horodatage.

Temps par coup (différence de `%clk`, incrément nul) :

| | Nico | dusha28 |
|---|---|---|
| Pendule au coup 23 (début finale B+N contre T) | 299 s | 417 s |
| Temps sur les coups 23-55 | 298 s pour 33 coups | 225 s pour 33 coups |
| Rythme | irrégulier, 0,8 à 35 s | 6-9 s par coup, métronome |
| Réflexions ≥ 20 s pendant la période | 25.Bh4 22 s, 29.Be5 32 s, 30.Ke2 23 s, 31.f4 34 s, 37.Kd3 35 s | aucune |
| Réflexions ≥ 20 s avant | 11.Bxe4 35, 13.Nd5 24, 14.Rxb4 54, 19.Ng5+ 25, 21.Nexc7 30, 22.Re1 43 | 14...Nxb4 60 |

37.Kd3 (35 s) est le coup du moteur depuis le coup 31 : Nico a trouvé l'idée, tard et cher.

### 1.d Réponse d'ARIA au run

Bilan LLM : « Le point faible est la gestion du temps en finale », « avec peu de temps à la
pendule » — **sans aucune donnée d'horloge** dans le bloc (déduit de `Termination`, présent dans
le PGN brut en fin de message). Les 4 positions (10, 23, 29?, 55) ne parlent pas de conversion.

## 2. Code existant

### `chess_coach/analysis.py`
- `PlyAnalysis.clock` (l. 96) = `node.clock()` (l. 365). `eval_before_cp` / `eval_after_cp`
  présents dans l'objet, **absents de `plies_json`**.
- `select_critical` (l. 522) : budget 4, sortes a/b (perte ≥ 10), d, e, c. Rien pour une
  période sans erreur.

### `chess_coach/summary.py`
- `summarize` l. 233 : `unconverted = max(wins) >= 80 and outcome != "win"` (aussi vrai
  sur `*`, #96). **Jamais relu** (grep : seul `test_summary.py`).
- l. 246-250 : `errors_low_clock` (erreurs à < 60 s) ou `None` sans horloge. **Jamais relu** (#161).
- `plies_json` stocke `clock` par demi-coup (null partout aujourd'hui, #170).
- `story_line` (l. 118) : « Défaite sans coup décisif : de 93 % au coup 52 à 81 % au coup 55.
  Pire coup 55.b6 » — ne dit ni la durée au-dessus de 80 %, ni le temps.

### `chess_coach/player_model.py`
- Thème `convert` (l. 229) : épreuves à `win_before ≥ 70`, mais `_is_trial` exige
  `win_before ≤ 90` et (perte ≥ 10 ou écart au 2e ≥ 10). Une conversion lente à 85 % faite
  de coups à perte 2 ne crée **aucune épreuve** : le thème ne voit pas ce défaut.

### `execution/routers/chess_router.py`
- `execute` (l. 728) : doublon par hash des coups (`_pgn_hash`) → « déjà envoyée » (#182).
  **La même partie recollée avec horloges est refusée** : bloquant pour le run live sur la
  partie de référence.
- `_build_enriched` (l. 884) : bloc de données + consigne. Aucune ligne temps, aucune
  ligne conversion. Le message original (PGN brut, `Termination`) est ajouté en fin.
- `_execute_game` : `story` au-dessus du texte du LLM ; `_moves_line`, bloc progression après.

### `memory/writer.py`
- `write_chess_game` : `upsert`, `timestamp = _now_iso()` (une réécriture déplace la partie
  dans la chronologie, cf. #97 / #185).

## 3. Diagnostic

1. Le défaut de conversion est **invisible** au pipeline : aucune perte ≥ 10, % de gain saturé.
   Le signal exploitable est le **meilleur coup répété et non joué** (Kd3 ×4, b5 ×5) sur une
   longue période ≥ 80 %.
2. Le LLM a affirmé une cause (temps) sans données : faute de consigne et de ligne temps.
3. Les horloges existent dès que Nico copie avec horodatage ; le code les parse et les stocke,
   personne ne les relit.
4. Rejouer la partie de référence est impossible aujourd'hui (doublon, #182).
