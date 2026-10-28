# Sprint 39 — audit : courbe du meilleur coup, mats, jeu libre, export PGN (#127-#130)

Date : 2026-10-27, code au tag `sprint-38` (`dc905d8`).

## 1. Ce qui existe

### Serveur — `interfaces/board_interface.py` (210 lignes)

- `POST /game` {pgn} → `_Handler._game` (l. 174) : `parse_pgn(pgn)`, réessai avec
  `[Event "?"]` en tête ; 400 « PGN illisible » ; sinon `game_wins(game)` → `{"wins": [...]}`.
- `game_wins(game)` (l. 130) : `analyze_game(game, "white", stockfish_path)` (0,15 s par
  position, Stockfish neuf à chaque appel, Threads 8) ; N+1 valeurs, % de gain **des
  blancs** (`win_before` du trait ramené aux blancs, dernière tirée de `win_after`).
- `POST /position` / `GET /state` : worker live, une position à la fois (inchangé
  depuis sprint 35). `state.best` = `{uci, san, pv_san}` **sans évaluation** ; les
  `_win_of` internes de `live.py` ne sortent pas dans l'état.
- Aucune écriture disque ni mémoire : la page est la seule à tenir la partie.

### Analyse — `chess_coach/analysis.py`

- `analyze_game` (l. 199) : `cp = score(mate_score=100000)` ; `PlyAnalysis.eval_before_cp`
  = cp **non borné** côté blancs (`sign * cp_before`). Un mat en N donne ±(100000 − N)
  (vérifié : `Mate(3).score(mate_score=100000) == 99997`) ; position de mat terminale :
  −100000 pour le trait (`_terminal_cp`). **Le mat en N est donc récupérable sans
  toucher `analyze_game`** : |cp| ≥ 90000 → N = 100000 − |cp|.
- `_win` borne à ±1000 cp avant conversion : un mat s'affiche ≈ 97,5 % sur la courbe,
  comme un +10. Aujourd'hui rien ne distingue un mat d'un gros avantage.
- `pv_mate` (booléen, mat pour le trait) existe aussi, sans le N.

### Page — `interfaces/board/index.html` (499 lignes)

- `game` = `{start, sans, played (Map FEN → SAN), cursor, wins, message}` ; null en jeu
  libre. `drawGraph()` (l. 396) : `svg.style.display = game ? "" : "none"` → **courbe
  absente en jeu libre** (#129). Une polyline blanche, ligne des 50 %, trait bleu au
  curseur ; x = indice de demi-coup dans la partie chargée.
- En variante (coup hors partie), la courbe reste celle de la partie chargée.
- Aucune liste de coups affichée ; aucun export ; aucune persistance (`localStorage`
  absent) : un rechargement de page perd la partie jouée.
- `chess.pgn()` (chess.js 1.4.0) sait produire le PGN de l'historique courant.

## 2. Constats

1. **#127 — la « courbe du meilleur coup » est déjà dans la courbe.** wins[i] =
   valeur de la position i avec le meilleur jeu, donc **la valeur du meilleur coup
   joué depuis i**. Une seconde courbe « si le meilleur coup avait été joué » placée en
   i+1 vaut wins[i] : c'est la courbe jouée décalée d'un demi-coup. L'écart entre les
   deux en i+1 = wins[i] − wins[i+1] = la **perte du coup joué** (`loss` de
   `analyze_game`, au bruit de 0,15 s près). Donc rien à calculer de neuf : la
   comparaison se dessine à partir de `wins`. Ce qui manque est **le nom du meilleur
   coup** (`best_san`), disponible dans `PlyAnalysis` mais non renvoyé par `/game`.
2. **#128 — mat en N disponible sans nouvelle analyse** (§1), à renvoyer par position.
   « Chances de mat » au sens probabilité n'existe pas chez Stockfish : seul « mat
   forcé en N vu à 0,15 s » est mesurable.
3. **#129 — jeu libre.** Deux mécanismes possibles :
   - renvoyer tout l'historique à `/game` à chaque coup : coût 0,15 s × N par coup,
     12 s par coup à 80 demi-coups [estimation, non mesurée], en concurrence CPU avec
     le worker live (#122) ;
   - évaluer seulement la nouvelle position (route une-FEN, ≈ 0,15 s + ouverture
     Stockfish) et garder les valeurs côté page dans une Map FEN → valeur. Coût
     constant par coup.
   Le worker live ne peut pas servir : pas d'évaluation dans l'état, passes
   `superseded` en jouant vite.
4. **#130 — « enregistrée » : sens à préciser.** Page seule (`localStorage` +
   bouton d'export `chess.pgn()` → fichier .pgn / presse-papier) suffit à « ne pas
   perdre la partie » et « l'exporter ». Une écriture palace (`write_chess_game`)
   depuis l'échiquier contournerait le kernel (hors kernel, pas de handler) :
   drapeau rouge, règle 1 / « Bypasser le kernel ». Écriture fichier serveur
   possible mais sans besoin identifié.
5. **Tests.** Toujours pas d'outillage JS : la page n'est vérifiée qu'au run live +
   présence des contrôles dans `test_index_serves_chessboard_page`. Le serveur
   (`/game` étendu, éventuelle route une-FEN) se teste comme `test_game_returns_white_win_curve`.

## 3. Règles d'architecture

Aucune touchée si : calcul dans `board_interface.py` / `analysis.py` (hors kernel,
pas de LLM), persistance côté navigateur, pas d'écriture palace. Palace prod non touché.
