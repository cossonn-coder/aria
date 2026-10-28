# Sprint 39 — état de conception

**Phase** : B — conception figée (2026-10-28), prête pour `/sprint-auto`.
**Branche** : `feat/sprint39-courbe-pgn`.
**Cible** : #127-#130 — courbe du meilleur coup, mats sur la courbe, courbe en jeu
libre, enregistrement + export PGN.

## Audit

`audit_courbe_pgn.md` : la courbe du meilleur coup = courbe jouée décalée d'un
demi-coup, l'écart = perte du coup (rien à recalculer, manque `best_san`) ; mat en N
récupérable depuis `eval_before_cp` sans toucher `analyze_game` ; courbe absente en jeu
libre (`drawGraph`) ; aucune persistance ni export ; écriture palace = contournement
du kernel.

## Décisions arrêtées

- Cible = #127-#130 (Nico, run live 38).

Lot 1 (Nico, 2026-10-27) :
- **#127 écart ombré + meilleur coup** : sur la courbe, la perte de chaque coup est
  ombrée entre « si meilleur coup » (valeur de la position avant) et « coup joué »
  (position après), seulement si perte ≥ 10 pts ; sous l'échiquier « joué : X —
  meilleur : Y (−Z pts) ». Rien à recalculer : `best_san` à renvoyer par position.
- **#129 une position par coup** : en jeu libre, chaque nouvelle position est évaluée
  seule (route une-FEN, ≈ 0,15 s), valeurs gardées côté page ; en variante d'une
  partie chargée, la courbe reste celle de la partie.
- **#130 navigateur + bouton export**, et Nico veut **alimenter le palace** avec ces
  parties (historique des parties).

Lot 2 (Nico, 2026-10-27) :
- **#130 bouton « Envoyer à ARIA »** : la page envoie le PGN au serveur de l'échiquier,
  qui le remet à `TelegramInterface` comme un message texte de Nico (même chemin que
  `_handle_message` : verrou utilisateur, `kernel.handle_event`, `send`) ; la réponse
  (analyse + fiche `chess_game` + progression) arrive sur Telegram. Kernel non
  contourné, écriture par `chess_router` → `write_chess_game` (règle 1 intacte).
  **Palace prod touché** par ce nouveau point d'entrée (chemin d'écriture existant).
- **#130 « Je joue »** sur la page : blancs / noirs / aucun ; l'export met
  `config.chess_username` dans White ou Black, WhiteElo / BlackElo des champs, Date.
- **#128 marque « #N »** aux positions où Stockfish voit un mat forcé (0,15 s), en haut
  (mat blanc) ou en bas (mat noir), et « mat en N » sous l'échiquier.

## Audit complémentaire (lot 2, envoi à ARIA)

- `bot.py` : `kernel`, puis `TelegramInterface(kernel, token)`, puis
  `start_board_server()` (threads daemon), puis `telegram.start()` (bloquant,
  `run_polling`) : la boucle asyncio PTB n'existe qu'une fois `start()` lancé.
- `TelegramInterface._handle_message` (l. 94) : `user_locks[user_id]`,
  `Event.create(TEXT, user_id, content, {"chat_id"})`, `_handle_with_waiting`
  (écrit… + ⏳), `send(chat_id, result)`. Rien n'expose la boucle ni un point
  d'entrée hors update Telegram.
- `config.allowed_user_id` (`ALLOWED_USER_ID`, renseigné dans `.env`) : sans caller
  aujourd'hui ; en chat privé, chat_id = user_id.
- `detect_pgn` (`cognitive_classifier.py:128`) exige `[White "` ou `[Black "` **et**
  `1.` : le PGN exporté doit porter ces en-têtes pour partir vers `chess_router`.
- `chess_router` : fiche identifiée par le hash des coups → renvoyer la même partie
  remplace la fiche ; couleur par en-tête (`detect_color`, `chess_username`).

Lot 3 (Nico, 2026-10-28) :
- **Contenu exporté / envoyé** : partie chargée hors variante → toute la partie (avec
  ses en-têtes) ; en variante ou en jeu libre → la ligne de l'échiquier.
- **Envoi permis avec « Je joue : aucun »** (ARIA prend alors les blancs par défaut).
- **OK pour figer** le découpage ci-dessous, branche `feat/sprint39-courbe-pgn`.

Recos de conception (Claude, figées avec l'OK) :
- Mat côté blancs signé (+N blancs, −N noirs) tiré de `eval_before_cp` /
  `eval_after_cp` (cp non bornés) ; position déjà matée → pas de repère.
- Route `POST /eval {fen}` : un Stockfish par requête, 0,15 s, pas de file ni de cache
  serveur ; la page garde une Map FEN → `{win, mate, best}`.
- Jeu libre : la ligne sous l'échiquier parle du **dernier coup joué** (pas de coup
  suivant) ; partie chargée : du coup joué depuis la position affichée (inchangé).
- Pseudo d'échecs injecté dans la page par le serveur (`__CHESS_USERNAME__` →
  `config.chess_username`), pas de route dédiée.
- Conservation au rechargement par `localStorage` ; une variante en cours est perdue.
- `submit_text` : boucle PTB mémorisée par `post_init` ; avant elle, `/send` → 503.

## Questions ouvertes

(aucune)

## Tronçons

- 01 serveur : `/game` + mates / best, `POST /eval`, pseudo dans la page (`01_serveur_courbe.md`) ✅ (372 tests verts ; `game_wins` rend un dict `{wins, mates, best}`, `position_eval(fen)` ; vérifié VM sur Stockfish réel : mat en 1 → `mate 1`, `win 97.5` [cp borné à 1000 par `_win`])
- 02 envoi à ARIA : `TelegramInterface.submit_text`, `POST /send`, `bot.py` (`02_envoi_aria.md`) ⏳
- 03 page : ombrage, « meilleur : Y », « #N », jeu libre, « Je joue », export, envoi, rechargement (`03_page.md`) ⏳
- 04 run live, Nico (`04_run_live.md`, parties : `run_live_parties.txt`) ⏳

## Dettes

Visées : #127, #128, #129, #130. Aucune autre touchée.
Palace prod touché par le tronçon 02 (nouveau point d'entrée, chemin d'écriture
`chess_router` → `write_chess_game` inchangé).

## §REPRISE

Tronçon 01 fait (non commité). Prochaine étape : tronçon 02 (envoi à ARIA), puis 03,
puis run live 04 par Nico. Lire `CLAUDE.md`, ce fichier, le kickoff du tronçon.
