# Sprint 54 — Audit : « pourquoi j'ai fait cette erreur, à quoi j'ai pensé »

Date : 2026-11-09. Code au tag `sprint-53` (de3f178).

## Demande de Nico

« L'analyse doit comprendre pourquoi j'ai fait une erreur et à quoi j'ai pensé quand j'ai
joué cette erreur. » Exemple : partie du 2026-11-09 contre Ashiki321x321 (Scandinave, noirs),
position 1, 9...Qd7 (39 % → 18 %).

## Ce qu'ARIA a écrit

> Pourquoi : 9...Qd5 garde la dame active et ne recule pas, alors que 9...Qd7 la place sur
> une case où 10.Ne5 l'attaque et force un repli coûteux.

Le texte compare deux coups comme si Nico avait choisi librement de « reculer ». Il ne dit pas :
1. que 9.Ba3 attaquait Qd6 : la dame DEVAIT bouger (coup forcé quant à la pièce) ;
2. ce que 9...Qd7 cherchait : déclouer Nc6 (cloué sur Ke8 par Bb5) et le défendre ;
3. ce que 9...Qd7 a négligé : la dame se met derrière Nc6 sur la diagonale de Bb5 ; Nc6 est
   désormais cloué sur la dame, donc 10.Ne5 attaque Qd7 et Nc6 sans que Nc6 puisse prendre
   (…Nxe5 ?? Bxd7+).

## Faits vérifiés au code (python-chess, fonctions réelles du router)

| Position | `_attacked_line` | `_move_facts` |
|---|---|---|
| après 8...e6 (avant 9.Ba3) | noirs Nc6 (par Bb5) | — |
| après 9.Ba3 (= `fen_before` de l'erreur) | blancs Ba3 (par Qd6) ; noirs Nc6 (par Bb5), **Qd6 (par Ba3)** | 9.Ba3 (**attaque Qd6**) |
| 9...Qd7 | — | 9...Qd7 (**décloue Nc6**) |
| 9...Qd5 | attaque Bb5 et Nf3 (défendus) | 9...Qd5 (aucun fait : `new_targets` ne garde que les cibles non défendues ou de valeur supérieure) |

Conclusion : le bloc LLM contenait déjà « Qd6 (par Ba3) » (ligne `attaquées` de `fen_before`)
et « décloue Nc6 ». Il manquait le reste.

## Chaîne actuelle (positions d'erreur, sortes a/b)

- `chess_coach/analysis.py:621` `assign_forcing_lines` : remplit `best_line_san` /
  `played_line_san` des erreurs (sortes a et b) seulement.
- `execution/routers/chess_router.py:1014+` (bloc LLM), par position : `suite jouée, faits`,
  `meilleur … ligne`, `faits`, `pièces`, `matériel`, `attaquées` (sur `fen_before`), `structure`,
  `évaluation`, `motifs` ; si `best_line_san` : `suite du meilleur coup, faits` + fin,
  `suite du coup joué, faits` + fin.
- Le coup adverse précédent n'est donné (avec ses faits) **que** pour la sorte e
  (`erreur adverse`, l. ~1060), jamais pour une erreur de Nico.
- Consigne (l. ~1112) : « Pourquoi : … explique en 1 à 2 phrases pourquoi le meilleur coup
  vaut mieux que le coup joué, **en comparant uniquement ces deux suites**, leurs faits et leur
  fin ». → la consigne interdit de fait d'utiliser la ligne `attaquées` ou le coup adverse :
  la question « qu'est-ce que tu voulais faire ? » n'est jamais posée au LLM.
- Faits de coup (`_move_fact_items`, l. ~258) : prise/reprise, échec, mat, roque, promotion,
  `attaque` (nouvelles cibles non défendues ou de valeur supérieure), `décloue` (clouage sur
  le roi seulement, `board.is_pinned`). **Aucun fait pour** : pièce qui fuit une attaque,
  pièce défendue par le coup, clouage relatif (pièce clouée sur dame/tour).

## Données disponibles non utilisées pour l'intention

- Temps par coup (`chess_coach/clock.py:move_times`) quand le PGN a des `%clk` : seul l'usage
  « réflexion longue ≥ 20 s » existe. Un coup d'erreur joué en 2 s (réflexe) n'est pas signalé.
  Le PGN de l'exemple n'a pas d'horloge.
- Maia-2 (`p.played_p`, P(coup joué) à l'Elo de Nico) : calculé seulement après le coup 10
  (`difficulty.py`, Maia jugé non fiable avant) ; 9...Qd7 n'en a pas.

## Diagnostic

Le « pourquoi » d'ARIA est un pourquoi **moteur** (quel coup vaut mieux), pas un pourquoi
**joueur** (quel problème tu résolvais, quelle idée tu as eue, ce que ton idée a oublié).
Cause : (1) la consigne restreint la comparaison aux deux suites ; (2) le coup adverse qui a posé
le problème n'est pas dans les données d'une erreur de Nico ; (3) aucun fait ne décrit le
défaut du coup joué quand il crée lui-même la cible (clouage relatif auto-infligé).

## Dettes adjacentes (hors scope)

- #115 (suivi « pourquoi mon 12e coup… » en conversation) : autre chemin (analyst), non touché.
- `Ton coup` : la suite forcée du moteur (perte de la dame contre un fou) diffère de la partie
  (10...Qd5 11.d4) — comportement voulu (sprint 52/53), non touché.
