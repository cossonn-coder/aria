# Sprint 64 — audit `/parties` sans échiquier (62-4, 62-5, 62-6)

Audit du 2026-11-20 sur `main` @ `9ab136f`. Lecture du code réel ; données prod lues
en lecture seule dans `chroma.sqlite3` (`?mode=ro`), sans ouvrir le palace.

## 1. Chemin d'une commande

`interfaces/telegram_interface.py:450` `_cmd_parties` / `:461` `_cmd_ouvertures` :
`bridge.load_chess_games()` (règle 2 respectée), `meta_commands.parse_period_args(args)`,
puis une fonction texte pure de `interfaces/meta_commands.py`, puis `_deliver` (texte brut).
Pas de LLM, pas d'écriture : sujet purement présentation, palace non touché.

- `/parties` : période par défaut `day` ; requête → `parties_opening_text`, sinon `parties_text`.
- `/ouvertures` : période par défaut `all` ; requête → `parties_opening_text`, sinon `openings_text`.
- `parse_period_args` (`meta_commands.py:160`) : seul le **dernier** mot peut être une période ;
  tout le reste est la requête d'ouverture. Un mot de cadence ou `details` y finirait
  aujourd'hui dans la requête (« Aucune ouverture ne correspond à « blitz » »).

## 2. Tri des ouvertures (62-4)

`_opening_stat_lines` (`meta_commands.py:259`) : tri `-games` seul ; à égalité, ordre
d'insertion du dict `opening_stats` (ordre des fiches) → ordre instable pour l'œil.
- `parties_text` : du plus joué au moins joué (haut → bas).
- `openings_text` : liste **inversée** (`[::-1]`), la plus jouée en bas, choix délibéré :
  Telegram affiche le bas du message.
- `opening_report_text` : sections couleur triées par nombre de parties (une ou deux lignes,
  hors sujet).
`OpeningStats` (`chess_coach/player_model.py`) porte `wins/draws/losses/games/win_rate` :
toutes les clés de tri voulues sont déjà disponibles. Correctif = une clé de tri dans
`_opening_stat_lines`.

## 3. Cadence (62-5)

`summarize` écrit `time_control` = en-tête `TimeControl` brut. Prod [488 fiches] :

| `time_control` | fiches | base + 40 × incrément | catégorie chess.com |
|---|---|---|---|
| `600` | 458 | 600 s | rapide |
| `600+0` | 9 | 600 s | rapide |
| `300` | 6 | 300 s | blitz |
| `180+2` | 3 | 260 s | blitz |
| `300+3` | 1 | 420 s | blitz |
| vide | 11 | — | inconnue |

Règle chess.com : durée estimée = base + 40 × incrément ; bullet < 180 s, blitz < 600 s,
rapide < 3600 s (≥ 600 s). Aucune fiche bullet ni classique aujourd'hui.
Aucun code ne classe la cadence : à écrire (une fonction pure).

## 4. `/parties` par défaut et `details` (62-6)

`parties_text` (`meta_commands.py:207`) produit, pour `day` : une ligne par partie
(couleur · adversaire · issue · ouverture), puis stats d'ouvertures, classement 🏆/📉 par
précision, et en dernier le bilan « Aujourd'hui : 3 V, 1 D — 75 % · performance … ».
Au-delà du jour : pas de ligne par partie.

Demande 62-6 : « liste cliquable des parties ; sans `details` : V/D du jour et des 10
dernières ». Il n'existe pas de ligne « 10 dernières » dans `/parties` (`_performance_line`
de `/ouvertures` a une notion « 5 dernières », `RECENT_GAMES = 5`, tri `_game_date_key`).

**Cliquable** : les fiches ne stockent **aucun lien** (pas d'en-tête `Link` chess.com dans
les clés). Le seul lien possible est l'échiquier ARIA (`config.board_url`, bouton WebApp
`telegram_interface.py:393-397`), qui ne sait pas ouvrir une partie donnée : c'est l'étape 4
de la feuille de route (62-3 + 62-7). Sprint 64 « sans échiquier » → liste non cliquable.

## 5. Règles d'architecture

Rien à risque : lecture via bridge déjà en place, fonctions texte pures, aucune écriture,
aucun router. Tests existants : `tests/interfaces/test_meta_commands.py`.

## 6. Run live

Runtime touché (commandes Telegram) → tronçon run live : `/parties`, `/parties details`,
`/parties blitz`, `/ouvertures`, contrôle visuel du tri et des compteurs.
