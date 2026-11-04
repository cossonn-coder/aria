# Audit sprint 49 — AggroChess face au calcul des coups explosifs

Date : 2026-11-04. Version auditée : AggroChess 4.5.0, commit `bbdb4a5`. Banc hors dépôt (scratchpad de session).
Aucun code de prod touché. Chiffres : Stockfish 17.1 et AggroChess, 8 threads sauf mention.

## 1. Ce qu'est AggroChess

Moteur UCI en Rust (GPL-3.0, 12 étoiles, créé en 2026-03, versions presque quotidiennes en 2026-10), « à la Tal ».
Son but affiché n'est pas d'être juste : il joue des sacrifices spéculatifs, avec une personnalité figée
(agression 220, bonus de sacrifice ≈ 3 pions, mépris du nul 50, escroqueries, livre de gambits intégré).
Son README le dit : le score affiché inclut le bonus de sacrifice.

Droits : la GPL-3.0 autorise copie, fork, modification. Lancé comme processus UCI séparé, il n'impose rien à ARIA
(même situation que Stockfish, GPL aussi). Le code source n'est à publier que si on distribue un binaire modifié.
Les versions publiées ne contiennent qu'un `.exe` Windows : sous Debian il faut compiler (`cargo` absent de la VM ;
compilation réussie en 1 min 05 avec Rust 1.82, installé dans le scratchpad).

## 2. Remplacement de Stockfish dans `explosive.py` : impossible sans fork, et sans intérêt avec

Vérifié par exécution via python-chess :

| Appel d'ARIA | Résultat avec AggroChess |
|---|---|
| `engine.configure({"Threads": 8, "Hash": 256})` (`ENGINE_OPTIONS`) | `EngineError` : pas d'option `Hash` |
| `engine.analyse(..., multipv=5)` (`_search_position`, `analyse_pass`) | `EngineError` : pas d'option `MultiPV` |
| `engine.analyse(board, Limit(time=…))` en position de livre | pas de `score` ni de `pv` : `_win_of` lèverait `KeyError` |

Sur le fond, le détecteur a besoin d'une évaluation objective (fenêtres de 5/10/15 pts de % de gain), or le score
d'AggroChess est biaisé par construction : Nxe4 +9,66 contre +2,86 pour Stockfish, Bxf7+ +1,29 contre -0,22 [0,5 s, 1 passe].
Écart à Stockfish sur le % de gain : médiane 9,4 pts, > 10 pts sur 23/48 positions [0,5 s, 1 passe].
Son appétit dépend aussi du numéro de coup et de l'état de la partie (`sac_params_for`). Un fork qui retirerait
bonus, personnalité et livre, et ajouterait MultiPV, donnerait un moteur classique sans raison de préférer à Stockfish.

## 3. AggroChess en source de candidats (Stockfish et Maia jugent) : gain marginal

Banc : 50 positions tirées au hasard de 18 parties de `docs/sprint*/`, coups 5-35, % de gain 35-85, Elo 1500, les deux camps.
Pour chaque position : détecteur actuel, puis coup d'AggroChess passé aux mêmes `_deepen` / `_admissible`.

| [50 positions, 1 passe, dont 2 en livre] | 0,5 s | 5 s |
|---|---|---|
| Coup = meilleur coup de Stockfish | 25/48 | 24/48 |
| Perte > 15 pts (Stockfish 0,5 s) : refus d'office | 4/48 | 7/48 |
| Admissible par nos règles | 15/48 | 12/48 |
| Admissible là où le détecteur actuel (24/50 positions) ne trouve rien | 4 | 3 |
| Dont intéressant après lecture (hors meilleur coup, gain > 0) | 1 (Ng4) | 1 (Ng4) |
| Admissible et gain supérieur au coup du détecteur | 4 | 4 |

- Le seul nouveau coup utile, Ng4 (perte 12,7, gain +10,6), n'est pas un sacrifice. Les autres : Be6 et Kf8 sont
  le meilleur coup de Stockfish (écart dû au non-déterminisme, #108), Nxe5 a un gain de -18,1.
- Sur les 4 meilleurs coups à chaque budget, un seul sacrifice (f4, 1 pion, gain +2,3 contre -7,6).
- Ses sacrifices propres, ceux que le détecteur n'a pas : tous refusés, et aussi mauvais face à un humain d'après Maia
  (Bxf7+ gain -32,7, Nxf2 -30,3, Bxf2+ -33,9, Bxf7+ -25,9, Nxe4 -7,0, Nxf7 -2,7) [6 coups, 1 passe].
- Positions de référence du sprint 36 : Fxf7+ et Fxh7+ trouvés par Stockfish aussi ; Göring : AggroChess joue Bc4 de son livre, pas c3.

## 4. Les énigmes « impossibles » : vrai à 30 s, disparaît à nos budgets

| [6 énigmes du dépôt, 1 passe] | AggroChess | Stockfish |
|---|---|---|
| 0,5 s, 8 threads | 1/6 | 0/6 |
| 4 s, 8 threads | 0/6 | 1/6 |
| 30 s, 1 thread | 5/6 | 1/6 |

L'annonce de l'auteur tient donc globalement à 30 s (il annonce aussi Nf6+ que nous n'avons pas obtenu).
Mais nos appels durent 0,3 à 0,6 s, 4 s au mieux en live (×8). Le « regard de Tal » exige (`search.rs:2477-2484`)
≥ 4 000 ms, sans `searchmoves` ; `uci.rs` retire 50 ms à `movetime`, donc un appel de 4 s (3 950 ms) ne le déclenche pas.
30 s par position sur une partie entière : hors de portée (plusieurs dizaines de positions par partie).

## 5. L'idée à reprendre : chercher chaque sacrifice à part

Le « regard de Tal » part d'un constat : dans une recherche normale, un sacrifice est coupé par la fenêtre des autres coups.
Stockfish forcé sur la solution (`searchmoves`), contre Stockfish libre à 2 s :

| Énigme | Forcé 0,5 s | Forcé 2 s | Forcé 10 s | Libre 2 s |
|---|---|---|---|---|
| Bc2+ | +1,29 | +2,25 | +3,08 | -4,02 |
| Qf6+ | -2,30 | +0,37 | +4,33 | -0,37 |
| Rd6+ | 0,00 | +1,77 | +2,26 | +0,98 |
| Bh3 | +3,27 | +4,40 | +5,57 | +4,04 |
| Nf6+ | -3,24 | -3,42 | -4,01 | -2,42 |
| Ba4+ | -5,14 | -4,81 | -4,63 | -5,30 |

Or `_search_position` (`explosive.py:344-349`) partage 0,5 s entre **tous** les coups de forme via
`root_moves=shaped, multipv=len(shaped)` : un sacrifice profond y est probablement sous-évalué, puis écarté par la fenêtre.
Hypothèse non mesurée sur des parties réelles : les énigmes sont des études composées, pas des positions de club.
Mesure à faire : même banc, en réanalysant à part les sacrifices (pièce offerte, échec) écartés aujourd'hui. Coût à chiffrer ; #162 (82 % du temps d'analyse [n=8]) est déjà ouverte.

## 6. Limites de la mesure

Une seule passe, analyse non déterministe (#108). 50 positions de 18 parties, en partie des parties de test, pas seulement celles de Nico. Elo fixé à 1500.
Pas de mesure sur la qualité perçue au run live. Les chiffres en % de gain de Stockfish à 0,5 s sont eux-mêmes bruités.

## 7. Le détecteur trouve-t-il les sacrifices ? (question de Nico, mesure de rappel)

Référence indépendante du détecteur : tous les coups qui offrent du matériel à vue (≥ 1 pion), jugés par Stockfish à 10 s, 8 threads.
Sain = au plus 10 pts de % de gain sous le meilleur coup. Détecteur lancé 2 fois par position (mode live, Elo 1500). AggroChess à 5 s, témoin externe.

### Sacrifices connus [12 positions, 2 passes du détecteur, 1 passe d'AggroChess]

14 positions préparées, 2 écartées : 15.Txd4 de Kasparov-Topalov n'est pas un sacrifice (simple reprise, erreur de ma liste), et 17.Cf6+ d'Anderssen est jugé non sain (32,1 pts).

| Position | Détecteur (2 passes) | AggroChess |
|---|---|---|
| Göring 4.c3 | 2/2 | Bc4 (livre) |
| Göring accepté Fxf7+ | 2/2 | oui |
| Evans 4.b4 | 2/2 | oui |
| Opéra 10.Cxb5 | 2/2 | Bd5 |
| Opéra 13.Txd7 | 2/2 | oui |
| Byrne-Fischer 11...Ca4 | 2/2 | oui |
| Toujours-vert 20.Txe7+ | 2/2 | oui |
| Grec Fxh7+ | 1/2 (sinon Nb3) | oui |
| Énigme Qf6+ | 1/2 | Bd2 |
| Énigme Rd6+ | 1/2 | Ne7+ |
| Kasparov-Topalov 24.Txd4 | 0/2 (montre Nc6+) | oui |
| Byrne-Fischer 17...Fe6 | 0/2 | Nb1 |

Bilan : détecteur 10/12 au moins une fois, 7/12 aux deux passes ; AggroChess 7/12.

### Positions de parties [58 positions uniques, 2 passes]

- Sacrifices sains d'au moins 2 pions (pièce, qualité) : 13 coups dans 11 positions, 9 affichés au moins une fois.
- Les 4 non affichés : Qd5, Be7, Cxe5, Cxf7.
- Sains d'au moins 1 pion : 31 coups, 14 affichés. La plupart des manqués sont des poussées de pion à gain d'espérance négatif (b4, g4, b5, f4).
- Précision : parmi les 25 affichages qui offrent du matériel, 23 sains [59 affichages sur 116 passes].
- Stabilité : même coup aux 2 passes sur 23 positions, autre coup sur 3, une seule passe sur 7, aucune sur 25.
- AggroChess : 10 sacrifices, 6 sains, dont 3 non affichés (Qd5, Cxf7, d3).

Seule vraie perle manquée : **27.Qd5!!** (`1q3kr1/2r1b1pp/p2NPn2/1pQ3N1/8/5PP1/PPP4P/3R1RK1 w`), déviation du cavalier f6 : 27...Cxd5 28.Ch7# vérifié. Elle sort de la fenêtre à cause de la recherche partagée (67,4 contre 83,1, soit 15,7 pts pour une limite de 15) ; cherchée à part : 71,1, admissible, gain +9,1.

### Recherche à part : l'hypothèse ne tient presque pas sur des parties réelles

| [58 positions, 1 passe] | Valeur |
|---|---|
| Écart recherche à part / partagée, médiane | 0,2 pt |
| Écart > 5 pts | 18 coups sur 547 |
| Sacrifices rentrés dans la fenêtre | 4 sur 553, dont 1 utile (Qd5) |
| Coût si appliquée à tout coup offrant | 9,5 coups × 0,5 s, soit +4,8 s par position, pour 4,35 s aujourd'hui (médiane) |

Version ciblée sur les offres d'au moins 5 pions (tour, dame) : 3 coups par position en moyenne, soit +1,5 s, pour 172 coups testés, 1 sain, 1 admissible : Qd5 [58 positions, 1 passe].

Sur les énigmes composées l'effet est net (Qf6+ 33,8 → 66,0 ; Rd6+ 33,2 → 70,6) : elles passeraient de 1/2 à stables.

### Angles morts identifiés

1. **Pièce déjà attaquée laissée en prise** (17...Fe6, la dame reste sur b6) : ni `offered` ni `accepted` ne le voient, et ma référence non plus. Le rappel de l'échantillon ne couvre donc pas ce type de sacrifice.
2. **Un seul coup par position**, choisi au gain d'espérance : un sacrifice sain peut céder la place à un coup calme (Fxh7+ / Nb3).
3. **Non-déterminisme** (#108) : 3 des 12 sacrifices connus n'apparaissent qu'à une passe sur deux.

### Limites

Échantillon petit, 2 passes seulement, parties en partie de test et pas uniquement de Nico, Elo fixé à 1500. « Sain » à 10 s n'est pas une preuve (études très profondes hors de portée). Le rappel en partie envoyée n'a pas été mesuré : ici le mode live, où le meilleur coup est candidat ; en partie envoyée il est exclu.

## 8. Clôture

Étude close sans code par Nico le 2026-11-04. AggroChess écarté, pas de fork. Angles morts notés en dettes #176 à #178.
Tous les chiffres ci-dessus sont à Elo 1500 : la relance à 1737 (Elo de la dernière fiche, compte non confirmé) a été arrêtée avant tout résultat, à la clôture.
