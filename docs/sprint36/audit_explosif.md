# Sprint 36 — audit de la définition du coup explosif (#121)

Date : 2026-10-23. Code lu : `chess_coach/explosive.py` (intégral), `chess_coach/live.py`
(intégral), `chess_coach/analysis.py` (`clear_advantage`, `_clear_criterion`,
`assign_motifs`, `select_critical`), `chess_coach/motifs.py` (`tag_motifs`, `sacrifice`,
`exposed_king`, `attacking_f2_f7`), `execution/routers/chess_router.py`
(`_explosive_lines`, `_caption`, flèche `alt_uci`).

## 1. Chemin de données

```
Échiquier live : board_interface.BoardWorker → live.analyse_pass(proxy, fen, elo, models_dir)
   → fenêtre _WIN_MIN.._WIN_MAX sur le meilleur coup (sinon « decided »)
   → explosive._search_position(proxy, board, "", "", elo, models_dir)

Analyse PGN : analysis.analyze → explosive.find_explosive(plies, …)
   → coups de Nico avec 35 ≤ win_before ≤ 75 et loss < 10
   → _search_position(engine, board, p.uci, p.best_uci, elo, models_dir)
   → CriticalPosition(kind="d") → select_critical (≤ 3 en bonus)
   → chess_router : _caption, _explosive_lines (lit e.evidence via _EVIDENCE_FR), flèche orange
```

`_search_position` : référence MultiPV 5 (0,5 s) + coups « par forme » (échec / prise / case
attaquée, 0,5 s), candidats = perte ≤ 15, hors meilleur coup, hors coup joué et
`first_best_uci`, triés (prioritaire d'abord, puis perte), plafonnés à 3 ; passe Maia
batchée ; `_deepen` par candidat (PV 0,3 s, prise naturelle 0,3 s, réponses humaines 0,3 s,
éventuelle réanalyse 0,6 s) ; `_admissible` ; garde le meilleur gain d'espérance.

`_admissible` : `evidence` non nulle (avantage clair après la réponse humaine la plus
probable) **ET** [ (perte ≤ 5, ou ≤ 15 avec piège ≥ 10) et (sacrifice ≥ 1 ou piège ≥ 10) ]
**OU** [ perte ≤ 15 et espérance ≥ meilleur + 5 ].

Callers de `_search_position` : `find_explosive` et `live.analyse_pass` (seuls). Callers de
`_admissible` : `_search_position`, `tests/chess_coach/test_chess_coach.py`.
`_WIN_MIN` / `_WIN_MAX` importés aussi par `live.py`. `_GAIN_MIN` importé par `chess_router`.

## 2. Diagnostic du kickoff : confirmé au code

Les cinq points du kickoff (meilleur coup exclu, sacrifice net, fenêtres 5 / 15, fenêtre
35-75, aucun motif) sont exacts. Deux constats s'ajoutent :

- **Avantage clair obligatoire** (`candidate.evidence is None → False`) sur les deux voies.
  Un sacrifice correct à évaluation égale n'aboutit à aucun avantage clair après la réponse
  logique : le sacrifice grec mesuré ci-dessous est rejeté pour cette seule raison.
- **Non-déterminisme** : 4.c3 (cas A) était rejeté à la mesure du kickoff (perte 5,1) et
  admis par l'ancienne règle au prototype (perte 3,6) [n=1 par mesure, Threads=8].

## 3. Mesures

### 3.a Déficit naïf (rejeté)

« Matériel en moins, après chacun de nos coups sur la PV, par rapport à la ligne du meilleur
coup » (référence = max(matériel de départ, matériel en fin de ligne du meilleur coup)) :
signale tous les coups calmes qui ne reprennent pas un pion en prise. Cas A : 4.Cbd2, 4.Fe2,
4.a3, 4.Fd3 à 1 ; cas B : tous les coups sauf 6.Cxc3. Bruit inacceptable.

### 3.b Déficit d'offre acceptée (retenu pour le prototype)

Même mesure, comptée **seulement si la réponse adverse au candidat est une prise**, sur la
PV moteur ou sur la ligne de la réponse humaine la plus probable (max des deux). Règle
prototype : admis si avantage clair et [ (déficit ≥ 1 et perte ≤ 10) ou ancienne règle hors
meilleur coup ] ; meilleur coup candidat ; tri : déficit sur la PV de racine (gratuite)
d'abord.

Script : scratchpad `proto.py` (Stockfish ENGINE_OPTIONS, temps de `explosive.py`, Maia
Elo 1500) [n=1 par position, non déterministe].

| Position | Coup | perte | déficit | avantage clair | E / E meilleur | ancienne | prototype |
|---|---|---|---|---|---|---|---|
| A (3…exd4) | 4.Cxd4 (meilleur) | 0 | 0 | matériel | 56,7 / 57,5 | non | non |
| A | 4.Fc4 | 2,2 | 0 | activité | 54,8 / 57,5 | non | non |
| A | 4.c3 | 3,6 | 2 | activité | 49,3 / 57,5 | oui | **oui** |
| B (5…Fc5) | 6.Fxf7+ (meilleur) | 0 | 2 | activité | 59,8 / 59,2 | non | **oui** |
| B | 6.Cxc3 | 8,2 | 0 | matériel | 56,0 / 59,2 | non | non |
| B | 6.O-O | 1,3 | 0 | développement | 56,7 / 59,2 | non | non |
| Grec (Colle, 10…Cd7) | 11.Fxh7+ (meilleur) | 0 | 2 | **aucun** | 50,1 / 52,0 | non | **non** |
| Grec | 11.Cb3 | 4,1 | 1 | matériel | 55,1 / 52,0 | oui | oui |
| Grec | 11.Te1 | 10,7 | 3 | matériel | 39,0 / 52,0 | non | non |
| Morra (3.c3, noirs) | 3…a6 | 4,6 | 2 | aucun | 46,7 / 56,0 | non | non |
| Italienne calme (6…O-O) | 7.h3 / 7.Te1 / 7.Fd5 | 0-10,9 | 0 | — | — | non | non |
| Espagnole (9.h3, noirs) | 9…d5 | 7,8 | 1 | activité | 40,7 / 47,2 | non | **oui** |

Lecture :
- Göring et Fxf7+ passent. 4.Fc4 ne passe pas (il ne fait que laisser le pion d4 ; aucune
  prise adverse en réponse) : sur le cas A, une seule flèche est montrée, 4.c3 suffit.
- Le sacrifice grec est vu (déficit 2, perte 0) mais tombe sur l'avantage clair : après
  11…Rxh7 12.Cg5+, la position reste égale (51 %).
- Bruit : 3…a6 (Morra, rend le pion de gambit) a un déficit 2 car la référence est la ligne
  du meilleur coup ; filtré ici par l'avantage clair. 9…d5 (Espagnole, sacrifice de pion
  type Marshall, perte 7,8) passe : plausible, à juger au run live. 11.Te1 (perte 10,7)
  coupé par la fenêtre 10 : une tolérance de « deux pions d'évaluation » (≈ 18 pts autour de
  l'égalité) l'aurait admis.
- Durée par position : 6-7,5 s hors chargement Maia (A : 19,4 s, chargement compris), sous
  le budget 10 s de la passe ×1. L'implémentation réelle ne coûte aucun appel moteur de plus :
  la PV (`principal`) et la ligne humaine (`logical`) sont déjà calculées dans `_deepen`.

## 4. Motifs (`motifs.py`)

`tag_motifs(fen_before_opponent, opponent_uci, line_uci)` exige le coup adverse précédent
(format puzzle Lichess). En live, `analyse_pass` ne reçoit qu'un FEN : pas de coup
précédent. `cook.sacrifice` mesure aussi « ≥ 2 de moins que la position initiale » : il ne
voit pas le Göring (référence = départ). Le déficit d'offre acceptée couvre les trois cas de
Nico sans motifs.

## 5. Rendu PGN : point de fragilité

`_explosive_lines` écrit `_EVIDENCE_FR[e.evidence]` et `_material_line(e.trap_end_fen, …)` :
un candidat admis sans avantage clair (`evidence=None`, `trap_end_fen=None`) casserait le
rendu (KeyError / FEN None). Toute voie d'admission sans avantage clair impose d'adapter ces
lignes. En live, `_explosive_dict` transmet `trap_line_san` (vide dans ce cas) : rien ne casse.

## 6. Exclusions de `_search_position`

`move != best` est en dur. En PGN, `first_best_uci` (meilleur de la 1re passe, celui de la
légende) est aussi exclu ; en live il vaut `""`. Retirer `move != best` seul laisse donc le
meilleur coup exclu en PGN (dans le cas courant où les deux passes s'accordent) et le rend
candidat en live, sans nouveau paramètre.
