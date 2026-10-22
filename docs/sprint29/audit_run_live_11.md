# Sprint 29 — audit des retours du run live 11 (phase A'')

HEAD `1f5c2c4`, 2026-10-22. Reproduction hors service : `analyze` + `_build_enriched`
(sans LLM) sur les parties 1 et 4 de `run_live_11_parties.txt` (script scratch, non commité).

## 1. Légende ❌ — formule creuse, pas de variante expliquée

### Ce que reçoit le LLM (deepseek-v4-pro, REASONING)

Extrait réel, partie 4, Position 1 (`_build_enriched`, `execution/routers/chess_router.py:542`) :

```
Position 1 (occasion explosive) — coup 13 :
  joué 13...O-O, perte 0 pts de % de gain (68 % → 69 %)
  meilleur 13...Qe7, ligne : 13...Qe7 14.Ba3 O-O 15.Bxd6 Qxd6 16.g3
  étiquettes : coup de roi, roque, phase : milieu de partie
  pièces : blancs Ke1 Qe2 … ; noirs Ke8 Qd8 …
  matériel : égal
  attaquées : aucune
```

Positions 3, 4 (partie 4) : idem `matériel : égal` + `attaquées : aucune`, à 75 % et 65 %.

### Causes

1. **Consigne contradictoire.** Elle demande la variante « expliquée coup par coup »,
   puis interdit : « Ne décris aucune attaque, défense, menace ou colonne absente des
   lignes matériel / attaquées ». Or ces lignes décrivent la position **avant** le coup ;
   aucune donnée ne dit ce que fait chaque coup de la ligne. Expliquer = enfreindre
   l'interdit → le LLM se rabat sur la paraphrase des seules données autorisées.
2. **Idée générale sans matière.** La consigne dit « d'après les pièces, le matériel,
   les attaquées et les motifs ». Hors moments tactiques, ces lignes valent
   « égal / aucune » et les motifs sont vides → « Position équilibrée, matériel égal,
   aucune pièce attaquée » répété partout.
3. **« Équilibrée » à 75 %.** Le % de gain n'apparaît que dans la ligne « perte … (68 % →
   69 %) », lue comme une perte, pas comme l'état de la position. Aucune ligne ne dit
   « avantage Nico ».
4. Historique de conversation (20 messages, `conversation_history loaded`) : les réponses
   d'échecs précédentes y figurent ; la formule peut s'auto-entretenir. Non mesuré.

## 2. Meilleur coup ❌ — reprises, réponses aux échecs, prises de pion

### Code (`chess_coach/explosive.py:393-462`)

`_problem_score` = Σ p_Maia(réponse adverse) × (win − win meilleure défense) sur les
réponses fautives. Mesure **la difficulté de la position laissée à l'adversaire**, pas
le mérite du coup de Nico. Une reprise forcée (32...bxa5) ou une parade d'échec (20.Kd2)
qui laisse une position piégeuse obtient un gros score : le coup lui-même n'y est pour rien.

### « 0 % de chances »

`defense_p = dict(distribution).get(defense.uci(), 0.0)` : la meilleure défense est hors
des réponses Maia gardées (90 % cumulés) sur 4/4 parties [n=4] — biais de sélection : le
score est maximal précisément quand les humains ne la voient pas.

### Signal disponible et inutilisé

`difficulty.assign_difficulty` (sprint 28) calcule déjà, coup par coup après le coup 10,
l'Elo auquel le meilleur coup Stockfish est trouvé une fois sur deux (Maia-2, Elo de Nico).
Mesure sur le code actuel (Elo par défaut 1300 si absent) :

| Partie | Coup | joué = meilleur | perte | difficulté |
|---|---|---|---|---|
| 4 | 32...bxa5 (choisi au live) | oui | 1,4 | **650** |
| 4 | 16...Nd5 | oui | 0 | 1773 |
| 4 | 23...c5 | oui | 0 | 1630 |
| 4 | 38...Qd1+ | oui | 0 | 1679 |
| 1 | 20.Kd2 (choisi au live) | non (Kf1) | 5,1 | — |
| 1 | 15.e6 | oui | 0,4 | 1602 |
| 1 | 29.Nc5+ | oui | 0 | 1607 |
| 1 | 14.Bg3 (reprise d'un recul) | oui | 0 | 775 |

Les reprises / coups évidents ont une difficulté basse (650-930) ; les coups plausibles
comme « meilleur coup » sont en haut. Limite : la difficulté porte sur le meilleur coup
Stockfish ; un coup équivalent joué par Nico (ex. 39...Qf3+ au lieu de Bf3+, perte 0)
n'est pas couvert → calculer P(coup joué) plutôt que P(meilleur coup)
(`_probabilities` prend déjà des couples (fen, uci)).

Non-déterminisme : au rejeu, le meilleur coup actuel de la partie 4 devient 33...Qd8
(live : 32...bxa5) — Threads=8 + limites en temps, déjà accepté.

## 3. Occasions explosives — bruit d'ouverture

Rejeu partie 1 : occasions 3.Bc4 et 6.Bb5 (live : 2.Nf3, 4.c3), toutes deux « pari »
(admises par la règle sprint 28 seule). Maia est jugé non fiable avant le coup 10
(`difficulty._OPENING_MOVES = 10`) mais `find_explosive` l'utilise dès le coup 1
(décision phase A « toute la partie »).

Texte « contradictoire » : la consigne d demande « quelles réponses perdent » ET la ligne
« pari » dit que l'espérance n'est pas meilleure ; les deux sont vraies ensemble
(les réponses perdent par rapport à la position de départ, mais pas plus qu'après le
meilleur coup). Problème de formulation LLM, pas de calcul.
