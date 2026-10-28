# Sprint 39 — tronçon 01 : courbe côté serveur (mats, meilleur coup, une position)

Lire d'abord `CLAUDE.md` et `00_etat.md` (décisions lots 1-3).

## Objectif

Le serveur de l'échiquier fournit, pour chaque position, le % de gain des blancs, le mat
forcé éventuel et le meilleur coup : pour une partie entière (`POST /game`, étendu) et
pour une position seule (`POST /eval`, nouveau, jeu libre). Et la page servie reçoit le
pseudo d'échecs de Nico (export PGN, tronçon 03).

## Fichiers

- `interfaces/board_interface.py` (seul fichier de prod).
- `tests/interfaces/test_board_interface.py`.

## Comportement attendu

1. **`game_wins(game)`** (l. 130) — garder le nom ou le renommer, au choix — rend en plus
   de `wins` :
   - `mates` : N+1 valeurs, mat forcé **côté blancs** : entier signé (+N = les blancs
     matent en N, −N = les noirs matent en N), `None` sinon. Source sans toucher
     `analyze_game` : `PlyAnalysis.eval_before_cp` (position i) et, pour la dernière
     position, `eval_after_cp` du dernier demi-coup ; ce sont des centipions **non
     bornés, point de vue des blancs** ; un mat en N vaut ±(100000 − N)
     (`Mate(3).score(mate_score=100000) == 99997`, vérifié). Règle : 90000 ≤ |cp| <
     100000 → mat en 100000 − |cp|, signe de cp. |cp| == 100000 = position déjà matée
     (`_terminal_cp`) → `None` (la page n'y met pas de repère).
   - `best` : N+1 valeurs, `best_san` du demi-coup i pour les positions 0..N−1, `None`
     pour la dernière.
   - Réponse de `/game` : `{"wins": [...], "mates": [...], "best": [...]}` (même ordre,
     même longueur). Le 400 « PGN illisible » est inchangé.
2. **`POST /eval {fen}`** → `{"win": float, "mate": int|None, "best": str|None}`, mêmes
   conventions (blancs, arrondi 0,1 pour win) :
   - fonction module (ex. `position_eval(fen)`) : Stockfish ouvert pour l'appel
     (`config.stockfish_path`, `ENGINE_OPTIONS`), `analyse` 0,15 s (même temps que
     `analyze_game`), score `.white()` ; win = `_win` de `chess_coach.analysis` sur le
     cp blancs (`score(mate_score=100000)`) ; mate = `.white().mate()` ; best = SAN de
     `pv[0]`.
   - position terminale : pas d'analyse ; win 100 / 0 si mat (blancs gagnants / perdants),
     50 sinon ; mate et best `None`.
   - Une requête = un Stockfish (pas de partage avec le worker live ni de file).
   - Log d'une ligne `board_eval duration=…s` (comme `board_game`).
3. **Pseudo dans la page** : `do_GET "/"` remplace dans `index.html` le texte
   `__CHESS_USERNAME__` par `config.chess_username` avant envoi (no-op tant que la page
   ne contient pas le marqueur ; le tronçon 03 l'ajoute).

`/position`, `/state`, `BoardWorker`, `live.py`, `analysis.py` : inchangés.

## Tests (cas nominal)

- Mettre à jour `test_game_returns_white_win_curve` : plies factices avec en plus
  `eval_before_cp`, `eval_after_cp`, `best_san` ; dont un mat (ex. dernier
  `eval_after_cp = -99999` → `mates[-1] == -1`) ; vérifier `wins`, `mates`, `best`.
- `/eval` : monkeypatch de la fonction d'évaluation → la route rend son dict.
- Optionnel si trivial : un test de la fonction d'évaluation sur une position matée
  (pas de Stockfish appelé).
- Le test de la page servie (`test_index_serves_chessboard_page`) reste vert.

## Hors scope

- Ne pas toucher `analyze_game`, `live.py`, le worker, la page.
- Pas de cache serveur, pas de file d'évaluation, pas de mat pour la position terminale.

## Critère de fin

`pytest tests/ -q` vert ; `/game` et `/eval` conformes aux formes ci-dessus.
