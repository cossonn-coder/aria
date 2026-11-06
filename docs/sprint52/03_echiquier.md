# Sprint 52 — Tronçon 03 : échiquier ARIA (Elo sur la précision, rang et performance d'ouverture)

Lire d'abord `CLAUDE.md`, `docs/sprint52/00_etat.md`, `docs/sprint52/audit_niveau_maia.md` §5.
Prérequis : tronçon 01 (`chess_coach/level.py` : `performance`, `accuracy_rank`).

## Objectif

1. **Page** (`interfaces/board/index.html`, l. ≈ 622) : la ligne précision porte l'Elo des champs
   `elo-white` / `elo-black` quand ils sont remplis :
   `Précision : blancs 84 % (1354) · noirs 79 % (1332)`. Champ vide → pas de parenthèses.
2. **Lecture seule des fiches par le serveur** : `start_board_server(submit_text=None, load_games=None)`
   (`interfaces/board_interface.py`) transmet `load_games` à `make_server`, rangé sur le serveur comme
   `submit_text`. `bot.py` passe la méthode `load_chess_games` du bridge déjà construit pour Telegram
   (`MempalaceBridge(store=search, get_by_metadata=get_by_metadata)`, l. ≈ 31 : le sortir dans une variable
   partagée). Règle 2 : aucune lecture directe de `mempalace_store` dans `board_interface.py`.
   Aucune écriture mémoire.
3. **Route `/game`** (PGN chargé) : la réponse gagne une clé `history` (liste de lignes, `[]` par défaut) :
   - camp de Nico : `detect_color(headers, "")` (`chess_coach/analysis.py`, pseudos de
     `config.chess_usernames`) ; si la source est `default`, prendre le champ `playing` envoyé par la page
     dans le corps de `/game` (`"white"` / `"black"` / `""`) ; camp toujours inconnu → `history = []` ;
   - précision de Nico sur la partie : `_game_accuracy(plies, couleur)` sur les plies déjà calculés par
     `analyze_game` dans `game_wins` (même moteur que Telegram) ;
   - ligne 1 : `Précision 84 % : ta 12e meilleure partie sur 140` (`accuracy_rank`, « ta meilleure partie » si rang 1) ;
   - ligne 2 : ouverture par `detect_opening(ucis)` + `opening_group(name)` (`chess_coach/openings.py`) ;
     fiches du même groupe (`game_opening_group`, `chess_coach/player_model.py`) et de la même couleur :
     `Défense hollandaise (noirs) : performance 1420 [12 parties] · 5 dernières : 1510`
     (même règle d'omission que le tronçon 02). Ouverture non détectée ou performance None → pas de ligne 2.
   - `load_games` absent ou en erreur → `history = []` (log `warning`), la courbe part quand même.
4. **Page** : envoie `playing` dans le corps de `/game` et affiche les lignes de `history` sous la ligne
   précision (élément dédié, vide sinon).

## Fichiers

- `interfaces/board_interface.py`, `interfaces/board/index.html`, `bot.py`
- Tests : `tests/interfaces/test_board_interface.py` (adapter `test_game_returns_white_win_curve` à la clé
  `history`, ajouter un cas nominal avec un `load_games` factice et un PGN aux en-têtes d'un pseudo de Nico),
  `tests/test_bot.py` si la signature de `start_board_server` y est simulée (l. ≈ 33).

## Hors scope (ne PAS faire)

- Pas d'authentification du serveur (#166 reste ouverte), pas de nouvelle route.
- Pas de Maia ni d'Elo estimé. Pas d'historique en jeu libre (seulement PGN chargé).
- Ne pas toucher le worker d'analyse live, `/eval`, `/accuracy`, `/send`.

## Critère de fin

`pytest tests/ -q` vert ; page chargée sans erreur JS (vérification visuelle au run live).
