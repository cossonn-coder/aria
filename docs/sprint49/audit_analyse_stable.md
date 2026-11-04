# Sprint 49 — audit : analyse instable, lente, meilleur coup limité

Date : 2026-11-04. Dettes : #85, #108, #125, #160, #162. Code lu sur `985a06a`.
Mesures sur la machine de dev, service en marche, script hors dépôt, aucune écriture mémoire.
Le temps varie d'un run à l'autre : les durées ci-dessous sont des ordres de grandeur.

## 1. Deux chemins d'analyse

| | Partie envoyée (Telegram, `/game`) | Échiquier live (`/board`) |
|---|---|---|
| Entrée | `analysis.analyze` | `BoardWorker._analyse` → `live.analyse_pass` |
| Moteur | `ENGINE_OPTIONS` Threads=8, Hash=256, limites en temps | idem, temps × `FACTORS` (1, 2, 4, 8) |
| Passes Stockfish | `analyze_game` 0,15 s par position, puis `find_explosive` | tête 0,5 s, `_human_moves`, `_search_position` |
| Résultat | d'un bloc, à la fin | état lu chaque seconde par la page, **remplacé à la fin de chaque passe** |

Commentaire `explosive.py:27` : « Threads=8 + limites en temps : deux rejeux du même PGN peuvent différer (accepté) ». C'est la cause racine.

Écart avec le tableau des dettes : `test_explosive_early_queen_nf6` (#85) n'existe plus dans `tests/`. À corriger à la clôture.

## 2. Instabilité : mesure sur Stockfish seul

Partie 1 de `docs/sprint46/run_live_parties.txt`, 60 positions.

| Réglage | Durée | Rejeu : meilleurs coups différents | Écart max de % de gain |
|---|---|---|---|
| Actuel (8 threads, 0,15 s) ≈ 176 000 nœuds médians | 10 s | 7, 11, 18 [3 comparaisons] | 4,0 à 6,7 pts |
| 1 thread, nœuds fixes, 8 Stockfish | 16,5 / 17,5 s | 0 [1 rejeu] | 0 |
| 1 thread, nœuds fixes, 1 Stockfish | 98,7 / 76,9 s | 0 [1 rejeu] | 0 |
| 1 thread, nœuds fixes, 12 Stockfish | 14,4 / 20,8 s | 0 [1 rejeu] | 0 |

Réglage testé : `Limit(nodes=…)`, `game=object()` (hash vidé à chaque appel), Hash=16. Le résultat ne dépend pas de l'ordre des positions : les trois réglages donnent le même écart à l'actuel (9 coups, 6,5 pts), indice et non preuve.

Justesse, écart à une référence de 5 M de nœuds [1 partie] : actuel 12 coups différents, nœuds fixes 13. Pas de perte visible à budget égal.

## 3. Instabilité et durée : analyse complète

Prototype : conversion temps → nœuds (`K` nœuds par seconde demandée), 8 Stockfish à 1 thread pour `analyze_game` et pour les positions de `find_explosive`, Maia partagé entre threads (aucun plantage observé). Durée = Stockfish + Maia + explosifs.

| Partie | Réglage | Durées totales | Miniatures retenues |
|---|---|---|---|
| 1 (au moins 4 erreurs) | Actuel | 80 / 69 / 85 s [3 runs] | stables, sauf la sorte a/b de 28.Nf5 |
| 1 | K = 1,17 M | 112 / 141 s [2 runs] | identiques |
| 1 | K = 0,59 M | 88 / 86 s [2 runs] | identiques |
| 2 (une seule erreur) | Actuel | 122 / 115 / 107 s [3 runs] | **3 listes différentes** |
| 2 | K = 1,17 M | 162 / 196 s [2 runs] | identiques |
| 2 | K = 0,59 M | 75 / 84 s [2 runs] | identiques |

Sur la partie 2, l'actuel donne : `d:11 d:15 d:19 a:21`, `a:15 a:17 d:19 a:21`, `d:11 d:19 a:21 e:24`. Les qualités de coups changent aussi : 4 à 9 demi-coups sur 47 à 59 [2 comparaisons par partie].

**Stable ne veut pas dire juste.** La liste d'explosifs change avec le budget (partie 2 : `d:14` à K = 0,59 M, `d:17` à K = 1,17 M). Les nœuds fixes rendent le résultat reproductible ; ils ne suppriment pas la sensibilité du détecteur à la profondeur. Le résultat changera une fois au passage au nouveau réglage, puis plus du tout pour une même version de Stockfish.

## 4. Rappel des sacrifices connus selon le budget

`_search_position`, mode live (meilleur coup candidat), Elo 1500.

| Position | Attendu | Actuel [3 essais] | K = 0,59 M [2 essais] | K = 1,17 M [1 essai] |
|---|---|---|---|---|
| Göring 4.c3 | c3 | Bc4, c3, c3 | c3, c3 | c3 |
| Göring accepté | Bxf7+ | 3/3 | 2/2 | oui |
| Evans | b4 | 3/3 | 2/2 | oui |
| Grec | Bxh7+ | Nb3, aucun, Nb3 | Nb3, Nb3 | Nb3 |
| Opéra 10 | Nxb5 | 3/3 | 2/2 | oui |
| Opéra 13 | Rxd7 | 3/3 | 2/2 | oui |
| Italienne calme | aucun | aucun 3/3 | aucun 2/2 | aucun |

K = 0,59 M ne perd rien sur cet échantillon [6 sacrifices]. Le grec est perdu partout ici alors qu'il sortait 1 fois sur 2 à l'étude AggroChess : le déterminisme peut figer un manque (#177, un seul coup par position).

## 5. Temps perdu dans les parties envoyées

- `critical` est le seul consommateur de `find_explosive` (`analysis.py:524-526` ; `summary.py:109` et `chess_router.py` lisent `analysis.critical`). `select_critical` remplit le budget de 4 avec les erreurs d'abord : **si 4 erreurs distinctes sont retenues, la recherche ne change rien**. Sur la partie 1, elle coûte 57 à 70 s sur 69 à 85 s [3 runs] pour un résultat jeté (#162, réponse à « autres usages à vérifier » : aucun).
- `find_explosive` cherche aussi avant `first_move`, écarté ensuite par `select_critical` (#160).
- `analyse_game` et `find_explosive` gardent chacun un Stockfish ; le coût réel est dans les explosifs.

## 6. Échiquier live : pourquoi le meilleur coup tarde

1. **Publié trop tard.** `analyse_pass` calcule `best` dès l'analyse de tête (0,5 s, `live.py:138`), mais `_analyse` ne l'écrit dans l'état qu'à la fin de la passe (`board_interface.py`, `self._state.update(outcome)`) : 16,3 et 31,4 s aux deux dernières passes 1 du journal [n=2], médiane ≈ 6 s au sprint 37 [n=24].
2. **Déjà connu ailleurs.** La page reçoit `best` en SAN par `/eval` (0,15 s de recherche, Stockfish à part, durée réelle non mesurée) ou par `/game`, dans `evals`, mais la flèche ne lit que `state.best`.
3. **Recherche non interruptible pendant un appel moteur.** `EngineProxy` ne teste `is_stale` qu'avant chaque appel : à ×8, un appel dure jusqu'à 4,8 s [calcul : 0,6 × 8], plus Maia. Une nouvelle position attend d'autant. Le point 2 contourne ce délai pour le meilleur coup.

## 7. Limites du meilleur coup (`interfaces/board/index.html`)

| Limite | Où |
|---|---|
| Seulement si aucune autre flèche n'est dessinée | `drawShapes`, `!shapes.length` |
| Pas avant le coup 10 | `blueAllowed` |
| 3 flèches par camp et par partie | `blueAllowed`, `blueDrawn` |
| Pas deux coups de suite du même camp | `blueAllowed` |
| Case décochée au chargement d'un PGN et à « Nouvelle partie » | lignes 907 et 944 (retour live du sprint 39) |

Coup identique à une autre flèche : `drawn` saute les doublons, à trancher pour le bleu. Le seul coup (vert) est par définition le meilleur coup.

## 8. Instabilité du live

Les passes ×1 à ×8 changent de profondeur : une flèche peut changer ou disparaître d'une passe à l'autre, c'est l'approfondissement (journal : `explosive` trois passes puis `none` à la 4e [n=1]). Revenir sur une position relance tout depuis ×1, donc les flèches peuvent différer et s'éteindre : c'est corrigeable sans toucher au moteur, en gardant le dernier résultat par position dans `BoardWorker`.
Nœuds fixes en live écartés : 1 thread rendrait la tête bien plus lente (≈ 2 à 4 s pour 295 000 nœuds [calcul sur le débit de la §2]).

## 9. Hors périmètre, à inscrire en dettes

- Interruption de la recherche pendant un appel moteur (§6.3).
- Le texte LLM reste variable d'un envoi à l'autre, même à miniatures identiques.
- `/eval` et le worker donnent deux meilleurs coups de profondeurs différentes, le second remplace le premier.
