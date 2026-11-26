# Sprint 68 — tronçon 04 : échiquier, côté serveur (anticipation + vitesse)

Lire d'abord `CLAUDE.md`, `docs/sprint68/00_etat.md`, puis `audit_joueur_du_bas.md` §2 et §6.1-6.3.
Fichiers : `interfaces/board_interface.py`, `chess_coach/live.py`, leurs tests
(`tests/interfaces/test_board_interface.py`, `tests/chess_coach/test_live.py`). La page
(`interfaces/board/index.html`) est le tronçon 05 : n'y toucher que si un test l'exige.

## 1. Anticipation au tour adverse

- `POST /position` reçoit en plus `bottom` (`"white"` | `"black"`, camp du bas ; absent →
  `"white"`). `BoardWorker.submit(fen, elo_white, elo_black, bottom)`.
- Camp au trait == `bottom` : comportement actuel (`analyse_pass`, Elo Maia = Elo de
  l'adversaire du trait, comme aujourd'hui).
- Camp au trait != `bottom` : passe `live.anticipate_pass(proxy, fen, elo, models_dir)` **à la
  place** d'`analyse_pass`, avec Elo Maia = Elo **du camp au trait** (ce sont ses coups qu'on
  prédit). Aucune analyse explosive / piège / stratégie dans ce cas (décision Nico : vitesse).
- Le mode entre dans la clé du cache `_finished` (aujourd'hui `(fen, elo)`) : par exemple
  `(fen, elo, mode)`.
- Injection pour les tests : `BoardWorker(..., run_pass=analyse_pass, run_anticipation=anticipate_pass)`.

`anticipate_pass` (dans `live.py`, module pur) :
- partie terminée → `{"result": "game_over", "anticipated": []}` + les clés habituelles à `None` ;
- `difficulty.reply_distribution([fen], elo, models_dir)[0]`, coups de p ≥ 0,10, 3 au plus ;
- `explosive._human_replies(proxy, board, distribution)` : `line_san[0]` est le coup adverse,
  `line_san[1]` (s'il existe) la meilleure réponse du joueur du bas ;
- rend `{"result": "anticipation", "anticipated": [{"uci", "san", "p", "reply_uci",
  "reply_san", "line_san", "win"}, …], "explosive": None, "forced": None, "best": None,
  "trap": None, "strategy": None}`. `reply_uci` / `reply_san` à `None` si le coup adverse
  termine la partie. `win` = % de gain du joueur du bas (déjà ainsi dans `_human_replies`).
- `BoardWorker._initial` gagne la clé `"anticipated": None`.

## 2. Vitesse

- **`/eval` sans relancer Stockfish** : `position_eval` ouvre aujourd'hui un Stockfish par appel
  (`popen_uci` + `configure(ENGINE_OPTIONS)`, ~80 % du temps [3 mesures]). Un moteur de module,
  ouvert au premier appel, gardé, protégé par un `threading.Lock` (le serveur est un
  `ThreadingHTTPServer`). `Limit(time=0.15)` inchangé.
- **Piège et stratégie dès qu'ils sont prêts** : dans `analyse_pass`, juste après
  `human = _human_moves(...)`, `proxy.on_head({"trap": human["trap"], "strategy": human["strategy"]})`.
  `BoardWorker._publish_head` ne met à jour que tant que `result == "pending"` : c'est voulu
  (passe 1 seulement).
- **Passe ×8 supprimée** : `FACTORS = (1, 2, 4)` ; corriger le commentaire (« ≈ 75 s »).
- **PGN collé déjà en fiche** : dans `_Handler._game`, avant `analyze_game`, calculer le hash des
  coups de la ligne principale avec la même formule que `chess_router._game_hash`
  (`sha256("".join(ucis))[:16]`, la dupliquer avec un commentaire qui renvoie à l'original) ;
  si `load_games()` contient `chess_game_<hash>`, répondre `stored_game(fiche, games)` (même
  réponse que `/stored`, avec `minis` et `playing`) et loguer `board_game stored id=…`. Sinon,
  chemin actuel.

## Tests (cas nominal)

- Worker : position où le camp au trait n'est pas `bottom` → `run_anticipation` appelée (pas
  `run_pass`), avec l'Elo du camp au trait ; état `result == "anticipation"`.
- `anticipate_pass` avec moteur et Maia factices (monkeypatch de `reply_distribution` et
  `_human_replies`) : 3 coups au plus, seuil 0,10, `reply_uci` déduit de `line_san[1]`.
- `/game` sur un PGN dont le hash est une fiche connue : réponse de `stored_game`, `analyze_game`
  non appelé.
- Un test que les deux formules de hash donnent le même résultat sur une même liste de coups.

## Hors scope

Page (tronçon 05), Telegram (01-03), réglages de la recherche explosive (03).

## Critère de fin

`pytest tests/ -q` vert ; `board_analysis … result=anticipation` visible dans un test de
worker. Comportement réel : run live (tronçon 06).
