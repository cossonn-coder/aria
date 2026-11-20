# Sprint 65 — tronçon 01 : l'échiquier ouvre une fiche stockée sans recalcul

À lire avant : `CLAUDE.md`, `docs/sprint65/00_etat.md`, `docs/sprint65/audit_parties_echiquier.md`
(§2 l'échiquier, §3 ce que la fiche stocke).

## Objectif

L'échiquier ARIA, ouvert avec l'identifiant d'une fiche `chess_game`, affiche cette partie
avec la courbe, les meilleurs coups et l'historique **lus dans la fiche**, sans aucune
analyse Stockfish de la partie (62-7). Le tronçon 02 fabriquera les liens Telegram.

## Identifiant

`hash` = id de la fiche sans le préfixe `chess_game_` (16 caractères hexadécimaux,
`execution/routers/chess_router.py:978` `_game_hash`). La fiche s'obtient en filtrant
`self.server.load_games()` (= `bridge.load_chess_games`, déjà injecté, règle 2) sur
`id == "chess_game_" + hash`. Pas de nouvelle méthode bridge.

## Fichiers à toucher

### `interfaces/board_interface.py`

1. `do_GET` (`:280`) compare `self.path == "/"` strictement. Telegram ouvre la Mini App avec
   des paramètres d'URL (`?tgWebAppStartParam=…`, et un fragment) : comparer sur le chemin
   seul (`urllib.parse.urlsplit(self.path).path`), sinon la page tombe en 404.
2. Nouvelle route qui sert une fiche, par exemple `POST /stored` `{"id": "<hash>"}`
   (même style que `/game`). Réponse, mêmes clés que `/game` plus deux :
   - `pgn` : PGN reconstruit, coups = `uci` de `plies_json` rejoués depuis la position initiale
     (toutes les fiches prod le permettent, audit §3) ; en-têtes : `White` / `Black` =
     `"Nico"` du côté `nico_color` et `opponent` de l'autre, `WhiteElo` / `BlackElo`
     (`elo_nico` / `elo_opponent`, si présents), `Date`, `Result`, `TimeControl` si présents.
   - `playing` : `nico_color`.
   - `wins` : même formule que `game_wins` (`:177`) appliquée aux `win_before` / `win_after`
     de `plies_json` (N+1 valeurs, point de vue des blancs).
   - `best` : `best_san` de chaque demi-coup, puis `None`.
   - `mates` : `None` partout (pas d'`eval_*_cp` dans la fiche, décision Nico).
   - `history` : `game_history(game, plies, nico_color, games)` avec `plies` =
     `SimpleNamespace(**p)` de `plies_json` (comme `scripts/backfill_chess_accuracy.py:42` ;
     `_game_accuracy` ne lit que `color`, `win_before`, `win_after`, `loss`, `quality`).
   - Fiche introuvable (ou `load_games` absent) → 404 JSON `{"error": "partie introuvable"}`.
   - Un log `board_stored id=<hash> plies=<N>`. **Jamais** d'appel à `analyze_game`.
   Une fonction pure (fiche + fiches → dict) testable sans serveur est souhaitable.

### `interfaces/board/index.html`

3. Au démarrage (là où `restoreState()` est appelé, `:1187`) : lire l'identifiant dans
   `Telegram.WebApp.initDataUnsafe.start_param`, à défaut dans le paramètre d'URL
   `tgWebAppStartParam`. S'il est présent, il **prime** sur l'état `localStorage` :
   `POST /stored`, puis charger la partie comme `loadGame` (`:1001`) le fait — `#pgn`
   rempli, « Je joue » réglé sur `playing`, noms/Elo depuis les en-têtes, curseur au
   départ — mais en rangeant `wins/mates/best/history` de la réponse dans `evals` /
   `game` **au lieu** d'appeler `POST /game`. Puis `saveState()`.
   Erreur → ligne d'état « partie introuvable » et la page continue comme sans identifiant.
   Prescrit l'intention : factoriser ce qu'il faut de `loadGame` pour ne pas dupliquer la
   mise en place de la partie, sans réécrire le reste de la page.

## Tests (cas nominal, `tests/interfaces/test_board_interface.py`)

- `GET /?tgWebAppStartParam=abc` → 200 et la page.
- `/stored` sur une fiche factice (`load_games` injecté, 2-3 demi-coups) : `pgn` rejouable,
  `wins` attendus (un coup noir pour vérifier le retournement), `best`, `mates` tout `None`,
  `playing` ; `analyze_game` monkeypatché pour lever si appelé.
- `/stored` id inconnu → 404.

## Hors-scope (ne PAS faire)

- Repères de mat, texte du coach, affichage de `kind` (étape 5 / 62-8).
- Chargement d'une FEN (dette 65-1).
- Toute écriture mémoire, tout changement de `summary.py` / `plies_json`.
- Liens Telegram (tronçon 02).

## Critère de fin

`pytest tests/ -q` vert ; nouveaux tests ci-dessus verts.
