# Sprint 35 — tronçon 01 : analyse live interruptible + serveur de l'échiquier

À lire avant : `CLAUDE.md`, `docs/sprint35/00_etat.md` (décisions), `docs/sprint35/audit_calque.md` §7.

## Objectif

Un serveur HTTP lancé dans `aria.service` reçoit la position affichée sur l'échiquier
(tronçon 02) et cherche en continu, pour le camp au trait, un coup explosif avec le code
existant de `chess_coach/explosive.py`, **sans le modifier**. Un nouveau coup interrompt
l'analyse en cours. Chaque passe est plus profonde que la précédente et remplace son
résultat ; la page interroge l'état courant.

Pas de kernel, pas de palace, pas de LLM : ce serveur n'écrit aucune mémoire et n'appelle
aucun router (règles 1, 2, 5 respectées par construction).

## Fichiers

| Fichier | Action |
|---|---|
| `chess_coach/live.py` | **créer** — logique d'analyse d'une position (sans HTTP) |
| `interfaces/board_interface.py` | **créer** — serveur HTTP + worker |
| `interfaces/board/index.html` | **créer** — page minimale provisoire (« échiquier : tronçon 02 ») servie sur `GET /` ; le tronçon 02 la remplace |
| `config.py` | ajouter `board_port: int = 5002` dans la section « Coach d'échecs (sprint 26) », avec un commentaire (port vérifié libre sur la VM) |
| `bot.py` | démarrer le serveur dans un thread daemon **avant** `telegram.start()` |
| `tests/test_bot.py` | neutraliser le démarrage du serveur (monkeypatch) pour que le test ne lie pas de port |
| `tests/chess_coach/test_live.py`, `tests/interfaces/test_board_interface.py` | **créer** |

## Comportement attendu

### `chess_coach/live.py`

Faits vérifiés dans `explosive.py` (à utiliser, ne pas recopier) :
- `_search_position(engine, board, played_uci, first_best_uci, elo, models_dir)` (l. 279)
  rend un `ExplosiveMove` ou `None`. Passer `""` pour `played_uci` et `first_best_uci`
  (pas de coup joué en live). Elle n'utilise que `engine.analyse(board, limit, **kwargs)`,
  le `Limit(time=…)` toujours en 2e argument positionnel (6 appels, l. 200-294), plus une
  passe Maia `reply_distribution` (non interruptible, c'est accepté).
- `_win_of(info)` (l. 126) = % de gain du trait ; `_WIN_MIN, _WIN_MAX = 35, 75` (l. 36).
- `ExplosiveMove` (l. 57-87) : `san`, `uci`, `pv_san`, `replies` = liste de
  `{"san", "p", "line_san", "win"}` (Maia, probabilité décroissante), `trap_line_san`.
- `chess_coach.difficulty._load(models_dir)` charge Maia une fois par process (cache
  global `_model`), partagé avec l'analyse Telegram.
- `ENGINE_OPTIONS` vient de `chess_coach.analysis`.

À écrire :

1. **Proxy moteur** : enveloppe un `chess.engine.SimpleEngine`. Son `analyse(board, limit,
   **kwargs)` :
   - lève une exception dédiée (ex. `Superseded`) si une position plus récente est arrivée
     (callable `is_stale()` fourni à la construction) ;
   - sinon délègue avec `chess.engine.Limit(time=limit.time * factor)`.
2. **Une passe** sur une position (`fen`, Elo de l'adversaire du trait, `factor`) :
   - partie terminée (`board.is_game_over()`) → état `game_over` (indispensable :
     `_search_position` lit `reference[0]["pv"][0]` et casserait sur une position terminale) ;
   - une analyse `multipv=2` via le proxy (temps de base 0,5 s) donne le % de gain du
     meilleur coup et du 2e. **Seul coup** = un seul coup légal, ou 2e coup à ≥ 20 points de
     % de gain derrière le meilleur → renvoyer ce meilleur coup (`uci`, `san`) ;
   - % de gain du trait hors `[_WIN_MIN, _WIN_MAX]` → état `decided` (pas de recherche
     d'explosif, le seul coup reste renvoyé s'il existe) ;
   - sinon `_search_position(proxy, …)` → `explosive` (uci, san, pv_san, replies,
     trap_line_san) ou `none`.
3. **Passes** : facteurs ×1, ×2, ×4, ×8 (constante de module). Après la passe ×8, l'état
   est marqué terminé. Le résultat de chaque passe **remplace** le précédent.

### `interfaces/board_interface.py`

- stdlib uniquement (`http.server.ThreadingHTTPServer`) : aucun framework web dans le venv.
  Écoute sur `0.0.0.0:config.board_port` (la page est ouverte depuis le PC Windows de Nico
  sur le LAN, `192.168.1.124`).
- Un **worker** unique (thread) tient un `SimpleEngine` Stockfish ouvert
  (`config.stockfish_path`, `ENGINE_OPTIONS`) et un état partagé protégé par un verrou :
  numéro de position courant, fen, Elo, et résultat courant.
- Routes :
  - `GET /` → `interfaces/board/index.html` ; déclenche en arrière-plan le chargement de
    Maia s'il n'est pas fait (14 s une fois, audit §7) — pas au démarrage du bot (mémoire).
  - `POST /position` JSON `{"fen", "elo_white", "elo_black"}` → incrémente le numéro de
    position, réveille le worker, répond `{"id": n}`. Le worker abandonne la passe en
    cours (`Superseded`) et démarre ×1 sur la nouvelle position.
  - `GET /state` → JSON de l'état courant, au minimum : `id`, `pass` (1-4), `passes` (4),
    `running` (bool), `result` parmi `pending | explosive | none | decided | game_over`,
    `explosive` (ou null), `forced` (ou null), `error` (ou null).
    La page ignore un `id` différent du sien.
- Elo envoyé à `_search_position` = Elo de l'adversaire du trait (blancs au trait →
  `elo_black`).
- Erreur moteur pendant une passe : logger `log.exception`, état `error` renseigné, le
  worker reste vivant pour la position suivante (pas d'autre `try/except` défensif).
- Logs (`get_logger(__name__)`) : démarrage du serveur avec le port ; par passe
  `board_analysis id=… pass=… result=… duration=…s` ; abandon `board_analysis superseded id=…`.
  Ce sont les lignes que Nico lira au run live.

### `bot.py`

Lancer le serveur dans un thread daemon avant `telegram.start()` (fonction publique du
module, ex. `start_board_server()`). Le reste de `main()` est inchangé (`os._exit(0)` tue
le thread daemon à l'arrêt).

## Tests (cas nominal, faux moteur — pas de Stockfish ni de Maia en test)

- Proxy : `analyse` multiplie le temps par le facteur ; lève `Superseded` quand `is_stale()`
  est vrai.
- Passe : seul coup détecté (écart ≥ 20) / non détecté ; hors fenêtre → `decided` sans
  appel à `_search_position` (monkeypatch) ; position terminale → `game_over`.
- Serveur (port éphémère, worker avec une passe factice monkeypatchée) : `POST /position`
  puis `GET /state` rend le résultat avec le bon `id` ; une seconde position remplace la
  première.
- `tests/test_bot.py` reste vert.
- `pytest tests/ -q` vert.

## Hors scope (ne PAS faire)

- Modifier `chess_coach/explosive.py`, `difficulty.py`, `analysis.py` ou le chess_router.
- Écrire dans le palace, appeler le kernel, un router ou un LLM.
- La vraie page échiquier (tronçon 02).
- Connexion à chess.com, multijoueur, pendule, sauvegarde de partie.
- Nouveau fichier systemd ou dépendance pip.

## Critère de fin

Tests ajoutés verts, `pytest tests/ -q` vert, commit local. Le délai réel (≤ 10 s pour la
passe 1) se vérifie au run live (tronçon 03).
