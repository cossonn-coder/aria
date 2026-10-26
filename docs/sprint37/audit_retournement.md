# Sprint 37 — audit : retourner une position perdante sur l'échiquier

Date : 2026-10-26. Code lu à `a67cb89` (main).

## 1. Pourquoi l'échiquier ne cherche plus rien en position perdante

`chess_coach/live.py` `analyse_pass` :

```python
head = proxy.analyse(board, chess.engine.Limit(time=_HEAD_TIME), multipv=2)
win_best = _win_of(head[0])
...
if not _WIN_MIN <= win_best <= _WIN_MAX:
    return {"result": "decided", "explosive": None, "forced": forced, "best": best_dict}
move = _search_position(proxy, board, "", "", elo, models_dir)
```

`chess_coach/explosive.py:36` : `_WIN_MIN, _WIN_MAX = 35, 85`. `win_best` = % de gain
(formule Lichess, `analysis._win`, centipions bornés à ±1000) **du camp au trait**.
Seuils équivalents en pions (calculés depuis la formule, pas mesurés) :
35 % ≈ −1,7 pion, 85 % ≈ +4,7 pions.

Effet : dès qu'un camp a ~1,7 pion d'avance, le camp en retard n'est plus analysé à son trait
(« position décidée ») ; au-delà de ~4,7 pions, plus personne.

Mêmes bornes côté PGN/Telegram : `find_explosive` (`explosive.py:405`) filtre
`_WIN_MIN <= p.win_before <= _WIN_MAX and p.loss < 10`.

## 2. Pourquoi `_search_position` ne convient pas tel quel en position perdante

`_search_position` → `_deepen` → `_admissible` (lus en entier) :

- **Voie sacrifice accepté** : déficit ≥ 1 pion vs ligne du meilleur coup, perte ≤ 10 pts,
  et (`evidence` non nul **ou** échec). Pensée pour « je donne du matériel en position saine ».
- **Voie avantage clair** : `evidence` = `clear_advantage(...)` sur la suite de la réponse humaine
  la plus probable (matériel +1, développement, activité, mat, « écrasant » ≥ 80 %). En position
  perdante, la réponse la plus probable ne mène presque jamais à un avantage pour le camp
  perdant → la voie est fermée.
- **Voie Maia** : perte ≤ 15 pts et espérance humaine ≥ meilleur coup + 5 pts, mais
  conditionnée à `evidence` non nul (ligne `if candidate.evidence is None: return False`).
- **Compression du % de gain** : à −5 pions ≈ 14 %, −10 pions ≈ 2 % ; tous les coups
  « perdants » sont à quelques points du meilleur. Les fenêtres de perte (5/10/15 pts)
  deviennent très permissives, les gains d'espérance (5 pts) très exigeants.
- Candidats : MultiPV 5 + coups « de forme » (échec, prise, case attaquée), 3 approfondis au plus.

Conclusion : il faut **une recherche dédiée** au camp perdant, pas un élargissement de la fenêtre.

## 3. Briques disponibles

- `difficulty.reply_distribution(fens, elo, models_dir)` : réponses Maia-2 (≤ 6, 90 % cumulés),
  une passe batchée.
- `explosive._human_replies(engine, after, distribution)` : % de gain après chaque réponse humaine
  (MultiPV restreint aux réponses) et `_expectation` (espérance humaine).
- **Tête de valeur Maia-2, inutilisée** : `maia2/main.py:424-426` rend
  `logits_maia, logits_side_info, logits_value` ; `maia2/inference.py:81` la convertit en
  probabilité de gain humaine (`logits_value / 2 + 0.5`, clamp [0, 1], retournée côté noirs).
  ARIA l'ignore (`difficulty.py` : `logits, _, _ = net(...)`). Coût : nul (même passe).
- `live.EngineProxy` / `FACTORS` : passes ×1 ×2 ×4 ×8, interruptibles. Latence actuelle de la
  passe ×1 « explosif » ≈ 4,2 s [journal 2026-10-23, n=6] (#122).

## 4. Page

`interfaces/board/index.html` : flèches `orange` (explosif), `green` (seul coup), `blue`
(meilleur coup), cases à cocher par calque, liste en marge droite (`saved`, clé FEN) avec
mini échiquier au survol. Thème : fond `#f4f1ec`, texte `#222`, échiquier chessground `brown`,
aucun mode sombre.

## 5. Mesures (prototype hors prod, `proto/games2.py` + `proto/measure_lib.py`)

16 positions tirées au hasard (graine 1) parmi les 54 positions des parties des runs live
(sprints 27-36, 6 parties distinctes) où le camp au trait est entre 3 et 35 % (SF 0,1 s),
coup ≥ 8. Candidats : MultiPV 8 (1 s) + coups de forme (`_by_shape`). Elo Maia 1300.
Deux exécutions (non-déterminisme Stockfish Threads=8, #108).

- **Pronostic Maia (rose)** : toujours plus haut que Stockfish en position perdante (calibré
  sur des humains : −3 ≈ 25-30 % au lieu de 10-13 %). Coup de pronostic max = meilleur coup SF
  dans 6/16 puis 9/16 [2 exécutions, n=16]. Écart sur le meilleur coup ≥ 3 pts dans 4/16
  [2 exécutions, n=16] ; sinon < 2 pts. Sature à 0 sous ~3 % SF.
- **Piège absolu (cyan, retour ≥ 35 %)** : proba ≥ 20 % dans 1/16 [2 exécutions, n=16].
- **Piège relatif (réponse ≥ meilleur coup + 15 pts)** : proba ≥ 20 % dans 3/16 [1 exécution,
  n=16], perte SF du coup 1,8 à 4,6 pts ; à +10 pts : 3/16 aussi.
- Corrélation pronostic Maia / SF entre coups d'une même position : 0,56 à 0,93 [6 positions
  construites, `proto` 1re version].

Coût : le pronostic sort de la passe Maia déjà faite (batch) ; le piège coûte une analyse
moteur par candidat (MultiPV restreint aux réponses Maia, comme `_human_replies`).

### 5.b Orange vs rose (`proto/orange_rose.py`, demandé par Nico)

30 positions (graine 2) parmi 83 des mêmes parties où le camp au trait est entre 35 et 85 %.
Orange = `_search_position` actuel (live : meilleur coup candidat) ; rose = pronostic Maia max
parmi MultiPV 8 à ≤ 15 pts du meilleur coup.

- Orange trouvé : 12/30 positions ; **orange = rose : 1/12** [1 exécution, n=12].
- Rose = meilleur coup Stockfish (donc masqué) : 15/30 [1 exécution, n=30].
