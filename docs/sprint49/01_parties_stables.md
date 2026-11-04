# Tronçon 01 — parties envoyées stables et moins de recherche inutile

## Objectif

La même partie analysée deux fois donne exactement le même résultat, sans ralentir, et on ne cherche plus d'explosifs quand le résultat ne peut pas servir. Mesures : `audit_analyse_stable.md` §2 à §5.

## Fichiers

- `chess_coach/analysis.py` : `analyze_game`, `analyze`, `select_critical`, constantes.
- `chess_coach/explosive.py` : `find_explosive`.
- `tests/chess_coach/test_chess_coach.py`.

## Comportement attendu

**Moteur à nœuds fixes** (parties envoyées et `/game`, qui passe par `analyze_game`) :
- Options : Threads=1, Hash=16 ; 8 Stockfish en parallèle ; une constante pour les nœuds par seconde demandée, 590 000. Nouvelles constantes : `ENGINE_OPTIONS` (Threads=8) reste celle du live et de `position_eval`, ne pas la changer.
- Une enveloppe du moteur, sur le modèle d'`EngineProxy` (`live.py`) : elle reçoit `analyse(board, Limit(time=t), **kwargs)` et lance `Limit(nodes=int(t * 590000), time=<plafond>)` avec `game=object()`, ce qui vide le hash à chaque appel. `_search_position` et `_human_replies` ne changent pas.
- **Plafond de temps obligatoire** : python-chess n'applique aucun timeout si `limit.time` est absent (`_timeout_for`, `chess/engine.py:2922`). Sans lui, un gel de Stockfish (#171) bloquerait l'analyse sans fin. Plafond conseillé : 60 s, jamais atteint en marche normale. Garder `ENGINE_TIMEOUT` à l'ouverture.
- `analyze_game` : positions réparties sur les 8 moteurs, résultats remis dans l'ordre de la partie. Elle garde sa signature (`time_per_position` converti en nœuds).
- `find_explosive` : positions éligibles réparties sur les 8 moteurs (`ThreadPoolExecutor`, un moteur par thread), `found` dans l'ordre de la partie. Maia reste partagé (`_load` avant les threads). Prototype validé ainsi [2 parties, 4 runs].
- Tous les moteurs sont fermés, y compris sur exception.

**Moins de recherche** (`analyze`, ordre : `first_shown_move` avant `find_explosive`) :
- `find_explosive` ne cherche que sur les coups `>= first_move` (#160).
- Si les erreurs (`a`, `b`) retenues par `select_critical` atteignent `_CRITICAL_BUDGET`, `find_explosive` n'est pas appelé (#162) ; une ligne au journal le dit (`chess_explosive skipped: …`). Extraire le calcul des erreurs de `select_critical` pour le réutiliser, sans changer ses résultats. `critical` est le seul consommateur des explosifs (vérifié).

## Tests (cas nominal)

- Stockfish réel (`skipif` comme le test existant, ligne 37) : `analyze_game` deux fois sur une courte partie → mêmes `best_uci`, `win_before`, `quality`.
- 4 erreurs simulées → `find_explosive` non appelé (monkeypatch) ; moins de 4 → appelé.
- `first_move` : aucune recherche avant ce coup.
- `test` lignes 321-340 (`timeouts == [60, 60]`) : `find_explosive([], …)` peut ne plus ouvrir de moteur ; l'adapter avec une position éligible, sans affaiblir la vérification du timeout.

## Hors périmètre

Live (`live.py`, `board_interface.py`) ; `position_eval` ; définition du coup explosif ; seuils ; #176-#178 ; #171.

## Critère de fin

`pytest tests/ -q` vert. Au sandbox ou par script, une partie analysée deux fois donne la même liste `critical`.
