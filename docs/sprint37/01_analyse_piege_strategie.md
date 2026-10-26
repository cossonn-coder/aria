# Sprint 37 — tronçon 01 : piège (cyan) et stratégie (rose) dans l'analyse live

Lire d'abord : `CLAUDE.md`, `docs/sprint37/00_etat.md` (décisions), `audit_retournement.md`
(§2-3 : briques existantes ; §5 : mesures du prototype, `proto/games2.py`).

## Objectif

À chaque passe de l'échiquier, pour **toute position non terminale** (y compris « décidée »),
le serveur rend en plus de l'existant :

- `trap` (piège, flèche cyan) : un coup du camp au trait dont au moins 20 % des réponses
  humaines probables (Maia, probabilités brutes cumulées) lui rapportent ≥ meilleur coup + 15
  pts de % de gain ; sinon `None`.
- `strategy` (stratégie, flèche rose) : le coup au plus fort pronostic humain Maia-2 (tête
  de valeur) ; toujours rendu en position non terminale (la page décide de l'afficher).

L'orange (`explosive`) est inchangé : même fenêtre 35–85 %, même `_search_position`.

## Fichiers

### `chess_coach/difficulty.py`

Ajouter `position_values(fens, elo, models_dir) -> list[float]` : pronostic Maia-2 du **camp
au trait** de chaque fen, en % (0-100), une passe batchée. Même préparation que
`reply_distribution` (`inference.preprocessing`, `elo_self = elo_oppo = elo`), mais lecture
de la 3e sortie du réseau : `logits, _, values = net(...)` puis
`(values / 2 + 0.5).clamp(0, 1)`. Ne **pas** retourner selon la couleur : la sortie brute est
déjà du point de vue du trait (`maia2/inference.py:78-93` ne retourne que pour exprimer le
résultat côté blancs). Le prototype `proto/measure_lib.py` `maia_values` fait exactement ça.

### `chess_coach/live.py`

Nouvelle fonction (nom libre, ex. `_human_moves(proxy, board, elo, models_dir)`) appelée
dans `analyse_pass` **après** le calcul de `forced`/`best_dict` et **avant** le test de
fenêtre `_WIN_MIN/_WIN_MAX`, pour que `decided` en profite aussi.

1. Candidats : analyse MultiPV 8 à `_HEAD_TIME` (via `proxy`, donc ×facteur et
   interruptible) + coups de forme `explosive._by_shape(board)` absents du MultiPV, analysés
   en `root_moves` (même schéma que `explosive._search_position` lignes « reference » /
   « shaped »). `win_best` = % de gain du 1er MultiPV. Garder les coups à perte
   `win_best − win ≤ 15` (constante nommée, ex. `_HUMAN_WINDOW = 15`) dont la position
   suivante n'est pas terminale.
2. **Stratégie** : `position_values` sur les positions après chaque candidat (une passe) ;
   pronostic du camp au trait = `100 − valeur` (dans la position suivante c'est l'adversaire
   au trait). Retenir le max. Rendre
   `{"uci", "san", "value", "best_value", "pv_san"}` : `value` = pronostic du coup retenu,
   `best_value` = pronostic du 1er coup MultiPV, `pv_san` = PV Stockfish du coup retenu
   (SAN depuis `board`, coup compris, `_REPLY_LINE_PLIES + 1` demi-coups au plus, comme
   `best_dict`). Pour les coups de forme, prendre la PV de leur analyse `root_moves`.
3. **Piège** : au plus 6 candidats (constante, ex. `_TRAP_MAX_DEEP = 6`), triés coups
   prioritaires d'abord (`explosive._priority`) puis perte croissante. Une passe
   `reply_distribution` batchée sur leurs positions suivantes, puis
   `explosive._human_replies(proxy, after, distribution)` par candidat. Probabilité du piège
   = somme des `p` des réponses dont `win ≥ win_best + 15` (constante, ex. `_TRAP_GAIN = 15`).
   Retenir le candidat de plus forte probabilité si elle est ≥ 0,20 (constante
   `_TRAP_P_MIN`). Rendre `{"uci", "san", "p", "replies"}` où `replies` = les seules
   réponses piégeantes, au format de `_human_replies` (`san`, `p`, `line_san`, `win`).
4. Rendre `{"trap": …, "strategy": …}` ; `analyse_pass` les ajoute à **chaque** retour
   (`None`, `None` pour `game_over`).

Docstring d'`analyse_pass` mise à jour (nouvelles clés).

### `interfaces/board_interface.py`

`BoardWorker._initial` : ajouter `"trap": None, "strategy": None` ; docstring de la classe
(liste de l'état) mise à jour. Rien d'autre : `self._state.update(outcome)` propage déjà.

## Tests (cas nominal, faux moteur / Maia monkeypatché)

- `tests/chess_coach/test_live.py` : adapter `test_forced_move_detected` (égalité de dict :
  ajouter `trap` / `strategy`, ou passer à des assertions par clé) ; monkeypatcher
  `position_values` et `reply_distribution` dans `_pass` pour que les tests existants ne
  chargent pas Maia.
- Nouveau test : un candidat dont la réponse humaine probable (p ≥ 0,2) donne ≥ +15 pts →
  `trap` rendu avec cette réponse ; un candidat de plus fort pronostic Maia → `strategy.uci`.
- `tests/interfaces/test_board_interface.py` : rien d'obligatoire (le faux `run_pass` ne rend
  pas les clés ; l'état initial les porte).

## Hors scope (ne PAS faire)

- Toucher `_search_position`, `_admissible`, `find_explosive`, la fenêtre de l'orange.
- Telegram / `chess_router` (dette #123).
- La page (`index.html`) : tronçon 02.
- Optimiser la latence (#122) au-delà du plafond de 6 candidats.

## Critère de fin

`pytest tests/ -q` vert ; un `analyse_pass` réel (Stockfish + Maia, script jetable non
commité ou test `skipif` existant) sur une position du prototype rend `strategy` non nul ;
la durée de la passe ×1 est notée dans le rapport.
