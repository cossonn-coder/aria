# Sprint 38 — tronçon 01 : route `POST /game` (courbe d'évaluation)

Lire d'abord : `CLAUDE.md`, `docs/sprint38/00_etat.md`, `docs/sprint38/audit_pgn.md` §4.

## Objectif

Le serveur de l'échiquier rend, pour une partie PGN, le % de gain des blancs de
chaque position (N+1 valeurs pour N demi-coups). La page (tronçon 02) en trace la
courbe. Aucune analyse nouvelle : on réutilise `chess_coach.analysis.analyze_game`.

## Fichier à toucher

- `interfaces/board_interface.py` : `_Handler.do_POST` (aujourd'hui seule la route
  `/position`, l. 150-156) + une fonction de calcul.
- `tests/interfaces/test_board_interface.py` : un test.

## Comportement attendu

`POST /game` avec `{"pgn": "<texte>"}` :

1. Lecture : `analysis.parse_pgn(pgn)` (l. 105). `parse_pgn` exige une ligne
   d'en-tête `[` ; un PGN réduit aux coups (« 1. e4 e5 … ») doit être accepté aussi :
   s'il rend None, réessayer avec `'[Event "?"]\n' + pgn`. Toujours None → réponse
   400 `{"error": "PGN illisible"}`.
2. Évaluation : `analyze_game(game, "white", config.stockfish_path)` (l. 199, temps
   par position par défaut 0,15 s ; `nico_color` sans effet sur les mesures).
   Il ouvre son propre Stockfish : ne pas toucher au worker live.
3. Conversion en % des blancs (`PlyAnalysis.win_before` / `win_after` sont du point
   de vue du **trait**, champ `color` = camp du demi-coup, `"white"` / `"black"`) :
   - position i (avant le demi-coup i) : `win_before` si `color == "white"`,
     sinon `100 - win_before` ;
   - position finale : `win_after` du dernier demi-coup si `color == "white"`,
     sinon `100 - win_after`.
4. Réponse 200 `{"wins": [w0, …, wN]}` (floats arrondis à 1 décimale), N+1 valeurs.
5. Log : `log.info(f"board_game plies={N} duration={…:.1f}s")`.

La requête est synchrone dans son thread (`ThreadingHTTPServer`) : ≈ 12 s pour
80 demi-coups [estimation, non mesurée] ; `/state` reste servi pendant ce temps.

Importer `analyze_game` et `parse_pgn` au niveau du module
(`from chess_coach.analysis import ENGINE_OPTIONS, analyze_game, parse_pgn`) pour que
le test puisse les remplacer par monkeypatch sur `interfaces.board_interface`.

## Test (cas nominal)

`test_game_returns_white_win_curve` : monkeypatch de
`interfaces.board_interface.analyze_game` par une fonction factice rendant deux
demi-coups (`SimpleNamespace(color="white", win_before=60, win_after=45)`,
`SimpleNamespace(color="black", win_before=55, win_after=30)`) ; `POST /game` avec
`"1. e4 e5"` (sans en-tête) → `{"wins": [60, 45, 70]}`. Même montage serveur que
`test_position_then_state_replaces_previous` (port 0, threads daemon).

## Hors scope

- Toute modification de `chess_coach/analysis.py`, `live.py`, `BoardWorker`.
- Qualité des coups, points d'erreur, Elo (lus par la page), cache des courbes.
- Écriture mémoire ou appel LLM (le serveur reste hors kernel).

## Critère de fin

`pytest tests/ -q` vert, nouveau test compris.
