# Sprint 38 — audit : charger un PGN dans l'échiquier (#94)

Date : 2026-10-26, code au tag `sprint-37` (`fd1da4a`).

## 1. Ce qui existe

### Serveur — `interfaces/board_interface.py` (182 lignes)

- `GET /` sert `interfaces/board/index.html` (et lance le chargement de Maia).
- `POST /position` `{fen, elo_white, elo_black}` → `BoardWorker.submit` : remplace
  la position courante, rend un `id` croissant. Maia reçoit l'Elo de l'adversaire
  du trait (`submit`, l. 59).
- `GET /state` : état de la **dernière** position seulement (`id`, `pass`, `result`,
  `explosive`, `forced`, `best`, `trap`, `strategy`, `error`).
- `BoardWorker` : **une seule position à la fois**. Passes ×1, ×2, ×4, ×8
  (`live.FACTORS`) ; une nouvelle position abandonne la passe en cours
  (`Superseded` via `EngineProxy`, ou résultat jeté après la passe Maia).
- Aucune notion de partie, d'historique ou de file : le serveur ignore d'où vient
  la FEN. Aucune écriture mémoire, aucun LLM (hors kernel).

### Analyse — `chess_coach/live.py`

`analyse_pass(proxy, fen, elo, models_dir)` : pure, une FEN → un résultat.
Durées constatées : ×1 1,8-9,5 s, médiane ≈ 6 s [journal 2026-10-26, n=24] ;
×4 13-49 s [n=4] (#122).

### Page — `interfaces/board/index.html` (356 lignes)

- `chess` (chess.js 1.4.0) tient la partie ; `chessground` 9.2.1 l'affiche.
- Toute modification de position passe par `newPosition()` : `syncBoard()`, état
  effacé, `positionFen = chess.fen()`, `POST /position`.
- Boutons : Nouvelle partie (`chess.reset()`, vide `saved` et `blueDrawn`),
  Annuler (`chess.undo()` puis `newPosition()`), Retourner. Elo blancs / noirs
  (champs numériques, 1300 par défaut ; `change` → `newPosition`).
- `poll()` toutes les ~1 s ; `save(kind, …)` range explosif / piège / stratégie dans
  `saved[kind]` : `Map FEN → {move, best}`. **Les colonnes sont indexées par FEN**
  et gardées jusqu'à « Nouvelle partie » : naviguer en arrière puis en avant
  conserve les blocs déjà trouvés.
- Flèche bleue rationnée : `blueAllowed()` lit `chess.history()` (coup précédent
  du même camp) et le numéro de coup de la FEN. Fonctionne tel quel sur une partie
  rejouée, puisque `chess.history()` = les coups menant à la position affichée.
- Aucun champ PGN, aucune navigation avant (« Annuler » détruit le coup).

### Tests — `tests/interfaces/test_board_interface.py`

Deux tests serveur (`test_position_then_state_replaces_previous`,
`test_index_serves_chessboard_page`). Rien ne teste le JavaScript de la page
(pas d'outillage JS dans le dépôt).

## 2. Constats

1. **Le cœur du besoin est côté page seule.** chess.js 1.4.0 sait lire un PGN
   (`loadPgn`) et exposer en-têtes (`WhiteElo`, `BlackElo`) et coups. Rejouer une
   partie = garder la liste des coups de la partie et un curseur, et appeler
   `newPosition()` à chaque pas. Le serveur, `live.py` et le worker n'ont pas à
   changer.
2. **Analyse à la demande, pas de la partie entière.** Le worker n'analyse que la
   position affichée. Naviguer vite = analyses `superseded` sans flèche (#122).
   Une pré-analyse de toute la partie (remplir les trois colonnes sans naviguer)
   demanderait une file côté serveur : ≈ 80 demi-coups × ≈ 6 s ≈ 8 min à ×1
   [médiane n=24, ×1 seul], et changerait le contrat « une position à la fois ».
3. **Colonnes par FEN = résumé de partie progressif.** En parcourant la partie,
   les colonnes se remplissent des coups trouvés ; elles ne disent pas aujourd'hui
   quel coup a été **joué** dans la partie à cette position (comparaison
   « joué X / trouvé Y » absente).
4. **Variante hors partie.** Jouer un coup sur l'échiquier au milieu de la partie
   chargée crée une ligne différente : il faut décider si les coups suivants de
   la partie sont oubliés ou gardés.
5. **Tests.** Pas d'outillage JS : la logique de navigation ne sera vérifiée qu'au
   run live, plus le test existant « la page est servie » (on peut y vérifier la
   présence des contrôles).
6. **Doublon possible avec l'analyse Telegram.** Envoyer un PGN à ARIA sur Telegram
   lance déjà une analyse complète (chess_router, explosifs, tournants). Hors
   scope ici : l'échiquier ne lit ni n'écrit le palace (règles 1-2 intactes).

## 3. Règles d'architecture

Aucune touchée si le travail reste dans la page (hors kernel, pas de mémoire,
pas de LLM). Une file de pré-analyse resterait dans `board_interface.py`, hors
kernel elle aussi.

## 4. Complément — graphe d'évaluation (demande de Nico, lot 2)

`chess_coach/analysis.py:199` `analyze_game(game, nico_color, engine_path,
time_per_position=0.15)` évalue déjà les N+1 positions d'une partie (Stockfish
propre, `ENGINE_OPTIONS` Threads 8) et rend une `PlyAnalysis` par demi-coup avec
`win_before` / `win_after` (% de gain **du trait**, formule Lichess `_win`).
`parse_pgn(text)` (l. 105) rend un `chess.pgn.Game` ou None. Pour la courbe :
% blancs de la position i = `win_before` si les blancs sont au trait, sinon
100 − `win_before` ; position finale tirée du `win_after` du dernier demi-coup
(même conversion, camp opposé). Second Stockfish en parallèle du worker live :
contention CPU pendant ≈ 12 s [estimation 0,15 s × 80 positions, non mesurée].
