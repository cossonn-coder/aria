# Sprint 47 — audit : topo par ouverture (`/ouvertures <nom>`)

Date : 2026-11-02. Chiffres mesurés sur une copie du palace prod (73 fiches `chess_game`), en lecture seule.

## Demande

`/ouvertures göring gambit` : performances sur l'ouverture, ce qui a fait gagner, ce qui a fait perdre,
pistes d'amélioration ; valable pour chaque ouverture.

## Code actuel

- `interfaces/telegram_interface.py:395` `_cmd_ouvertures` : charge les fiches par `self.bridge.load_chess_games`,
  ignore `context.args`, livre `meta_commands.openings_text(games)`. Précédent d'argument : `_cmd_logs` (ligne 371).
- `interfaces/meta_commands.py:165` `openings_text` : une ligne par (groupe, couleur), via
  `chess_coach/player_model.py:160` `opening_stats`. Issue inconnue non comptée.
- Les métacommandes ne passent pas par le kernel et n'ont **aucun accès au LLM** (`TelegramInterface` n'a que
  `kernel`, `bridge`). Bypasser le kernel pour un router est interdit (CLAUDE.md).
- Chemin kernel possible : `_process_text` crée l'`Event` (metadata `chat_id`) ; `classify_operation(message, llm_router,
  metadata, bridge)` a déjà des règles sur metadata (`image`) ; `core/kernel.py:70` table op → router ;
  `ChessExecutionRouter` détient déjà `mempalace_bridge` et `llm_execution_router` (`core/kernel.py:110`) et relit les
  fiches pour la progression. Le payload porte `op_type`.
- `llm_router.py:171,190` : `skip_history` (pas d'historique en entrée, échange écrit en fin de pipeline),
  `skip_intent` (ni intent ni rappel lié).
- Hallucinations LLM connues sur les échecs : #82 (ouverture sans PGN), #84, #92 (faits inventés autour des coups).

## Données disponibles par fiche

`outcome`, `opening` (variante Lichess), `opening_group`, `nico_color`, `elo_opponent`, `date`, `accuracy`,
`first_error_nico`, `first_error_opponent`, `max_win_nico`, `min_win_nico`, `opponent_errors`,
`opponent_errors_punished`, `worst_move`, `plies_json` (par demi-coup : `san`, `loss`, `best_san`, `phase`,
`win_before`, `motifs` du meilleur coup). Tout est stocké : pas besoin de Stockfish, réponse sans réanalyse.

## Mesures

Fiches : 73 ; issues 45 V, 2 N, 17 D, 9 inconnues.

| Taille de l'échantillon (groupe, couleur) | Nombre de couples |
|---|---|
| 1 partie | 16 |
| 2 parties | 9 |
| 3 parties | 3 |
| 4 parties | 1 |
| 6 parties (Dutch Defense, noirs) | 1 |
| 11 parties (Göring Gambit, blancs) | 1 |

**Écart avec le brief** : « ce qui m'a fait gagner / perdre » n'est une tendance que sur 2 ouvertures sur 31 ;
ailleurs on ne peut que raconter des parties.

Causes sur toutes les fiches, seuils du code existant :

| Issue | Cause | Parties |
|---|---|---|
| Défaite [n=17] | avantage gâché (`max_win_nico` ≥ 80) | 9 |
| Défaite [n=17] | erreur ≥ 20 pts, jamais gagnant | 5 |
| Défaite [n=17] | dérive, aucune erreur ≥ 20 pts | 3 |
| Victoire [n=45] | adversaire a craqué (erreur ≥ 20 pts) | 34 |
| Victoire [n=45] | aucune erreur adverse ≥ 20 pts | 10 |
| Victoire [n=45] | retournement (`min_win_nico` ≤ 20) | 1 |

Göring Gambit, blancs [n=11, 8 V 3 D] :
- précision moyenne : victoires 84,7 % [n=7], défaites 70,0 % [n=2] ; 26 fiches sur 73 n'ont pas de précision (avant sprint 29) ;
- % de gain au coup 10 : victoires 69,1 [n=8], défaites 62,1 [n=3] ;
- Elo adverse moyen : victoires 1545 [n=8], défaites 1394 [n=3] ;
- erreurs adverses ≥ 20 pts : 10, dont 9 punies en victoire [n=8] ; 1, punie, en défaite [n=3] ;
- défaites : Falestinhurra 26.Qc3 (−77, meilleur Rxd4) puis 39.Bb2 (−85,1, meilleur Qe4+) ;
  adv-jhuton 19.Bg5 (−69,2, meilleur Qxf5+) ; ProfSiko : aucune erreur ≥ 20 pts, jamais au-dessus de 60,5 %.

## Fausse bonne idée écartée par la mesure

« Même position, même erreur d'une partie à l'autre » (déviation de répertoire, #81) : sur Göring, Dutch et
Portsmouth, les seules positions répétées avec perte ≥ 5 pts sont **les coups du gambit eux-mêmes** (4.c3, 5.Bc4,
6.Qb3, 3.b4) : le moteur y préfère refuser le gambit. Une piste « joue 4.Nxd4 » serait absurde. Non retenu.

## Limites des données

- Aucune des 73 fiches n'a d'horloge (`clock` toujours vide) : le temps n'est pas mesurable. Touche #161, dont le
  constat d'origine (« calculés mais jamais relus ») ne dit pas que la donnée est absente. Cause non recherchée.
- 11 fiches à issue connue ont `color_source=default` (#159) : camp invérifiable.
- Noms de groupes en anglais (`Dutch Defense`) : « hollandaise » ne correspondrait pas.

## Suite donnée par Nico (2026-11-02)

Seules les statistiques sont gardées : pas de LLM, donc pas de passage par le kernel. Le topo rédigé et les causes
mesurées ci-dessus ne sont pas construits. Ajouts mesurés sur le Göring : 27,5 coups par partie, % de gain au coup 20 :
victoires 86,3 [5 victoires sur 8 atteignent ce coup], défaites 41,0 [n=3], 5 dernières : 4 V, 1 D. L'ordre des 5 dernières
est le même par date de partie et par date d'analyse sur le Göring, la Hollandaise et l'ensemble des fiches.
