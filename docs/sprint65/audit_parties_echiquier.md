# Sprint 65 — audit `/parties` → échiquier ARIA (62-3 + 62-7)

Audit du 2026-11-20 sur `main` @ `5a44242`. Lecture du code réel ; fiches prod lues en
lecture seule dans `chroma.sqlite3` (`?mode=ro`), sans ouvrir le palace.

## 1. Ce que Telegram affiche aujourd'hui

`interfaces/telegram_interface.py:450` `_cmd_parties`, `:462` `_cmd_ouvertures` :
`bridge.load_chess_games()` → `meta_commands.parse_period_args` → fonction texte pure →
`_deliver(chat_id, text)` (texte brut, pas de `parse_mode`, pas de `reply_markup`).

Parties nommées une à une dans les sorties :

| Sortie | Fonction | Lignes par partie |
|---|---|---|
| `/parties` (court, défaut) | `_short_parties_text` | aucune (bilans seulement) |
| `/parties details` | `parties_text` | une ligne par partie de la période (`couleur · contre X · issue · ouverture`), puis classement `_ranking_lines` (🏆 5 meilleures / 📉 5 pires) |
| `/parties <ouv.>`, `/ouvertures <nom>` | `opening_report_text` | classement `_ranking_lines` de l'ouverture |
| `/ouvertures` | `openings_text` | aucune (classement retiré au sprint 64) |

`_ranking_lines` (`meta_commands.py:236`) : au plus 10 parties (5 + 5), ou une liste unique
« Par précision : » si ≤ 5 parties classées. La liste `details` peut compter des dizaines de
lignes sur `week` / `month` / `all`.

## 2. L'échiquier ARIA

`interfaces/board_interface.py` : serveur HTTP (`ThreadingHTTPServer`, port
`config.board_port` = 5002), lancé par `bot.py:39`
`start_board_server(telegram.submit_text, bridge.load_chess_games)`.
`config.board_url` = `BOARD_URL` du `.env`, en **https** (tailscale serve) → `/board`
envoie un bouton Mini App (`InlineKeyboardButton(web_app=WebAppInfo(url))`,
`telegram_interface.py:386-402`).

Routes :
- `GET /` → `index.html` ; **`self.path == "/"` strict** (`board_interface.py:281`) :
  `/?game=…` tomberait en 404 aujourd'hui.
- `GET /state` ; `POST /position` (worker live Maia/Stockfish par position), `/game`,
  `/eval`, `/send`, `/accuracy`.
- `POST /game` (`_game`, `:302`) : parse le PGN, **`analyze_game(game, "white",
  stockfish)` complet** (0,15 s par position), puis `game_wins(plies)` →
  `{wins, mates, best}` + `history` (`game_history`, lit les fiches via `load_games`).

Page (`interfaces/board/index.html`) : `loadGame(cursor)` (`:1001`) lit le PGN du
`<textarea id="pgn">`, rejoue les coups, puis `POST /game` et range
`wins/mates/best` par FEN dans `evals` ; `history` dans `game.history`.
`restoreState()` (`:981`) recharge l'état `localStorage` (PGN, curseur, « Je joue »).
**Aucune lecture de paramètre d'URL** : la page ne sait pas ouvrir une partie donnée.

## 3. Ce que la fiche stocke (62-7)

`chess_coach/summary.py:279` `plies_json`, par demi-coup : `ply, move_number, color, san,
uci, win_before, win_after, loss, best_san, quality, phase, tags, clock, kind, difficulty,
second_gap, motifs`. Métadonnées : `date, nico_color, opponent, elo_nico, elo_opponent,
result, time_control, opening, accuracy…`. **Pas de PGN, pas d'en-tête FEN, pas
d'`eval_*_cp`.**

Ce que `/game` renvoie, reconstruit depuis la fiche :

| Champ `/game` | Source fiche | Remarque |
|---|---|---|
| coups (PGN) | `uci` de `plies_json` + en-têtes depuis métadonnées | rejouables depuis la position initiale : 499/499 fiches [lecture prod 2026-11-20] |
| `wins` | `win_before` / `win_after` ramenés côté blancs (même formule que `game_wins`) | identique : même `analyze_game` (0,15 s) côté Telegram (`analysis.py:810`) et échiquier |
| `best` | `best_san` | présent sur toutes les fiches [lecture prod 2026-11-20] |
| `mates` | — | `eval_before_cp` non stocké : pas de repère de mat sur la courbe |
| `history` | `game_history` | lit `win_before/after`, `quality` (via `_game_accuracy`) et les fiches : calculable sans moteur |

`kind` (positions critiques de l'analyse Telegram) est stocké mais l'échiquier n'a aucun
affichage pour lui. Le texte du coach (Pourquoi, miniatures) n'est pas dans la fiche.

## 4. Règles d'architecture

- Lecture : `load_games` = `bridge.load_chess_games` déjà injecté (règle 2 respectée).
  Retrouver une fiche par id = filtrer cette liste (pas de nouvelle méthode bridge requise).
- Aucune écriture mémoire, aucun router, aucun LLM, kernel non touché.
- Identifiant d'URL : `id` de la fiche (`chess_game_<hash>`), stable (upsert sur le hash des
  coups) ; une fiche remplacée par une partie prolongée change d'id → lien d'un ancien
  message cassé (cas rare, message d'erreur suffit).
- Palace prod : lecture seule.

## 5. Mécanismes Telegram possibles

1. **Boutons Mini App** (`InlineKeyboardButton(web_app=WebAppInfo(url + "?game=<id>"))`) :
   même mécanisme que `/board`, ouvre l'échiquier dans Telegram. Un bouton par partie,
   sous le message ; adapté à ≤ 10 parties (classement), pas à une liste longue.
2. **Liens dans le texte** (`parse_mode=HTML`, `<a href>`) : chaque ligne cliquable, sans
   limite, mais ouvre le navigateur (hors Mini App, `localStorage` séparé) et impose
   d'échapper le texte (pseudos).
Requis dans les deux cas : `BOARD_URL` en https (c'est le cas en prod), page qui lit
`?game=` et route serveur qui sert la fiche.

## 6. Run live

Runtime touché (commande Telegram + page) : `/parties details` → boutons → l'échiquier
s'ouvre sur la partie, courbe affichée **aussitôt** (pas de « courbe en calcul… »),
`journalctl` sans `board_game plies=` (pas d'analyse moteur), une ligne de log de chargement
de fiche à la place.
