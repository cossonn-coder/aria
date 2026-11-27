# Sprint 69 — retour du run live (2026-11-27), entrée de /conception sprint 70

## Verdict du run live (partie BaguetteCopter – jaypril17, 2026-11-27, Philidor Bird Gambit)

- Ligne 📚 correcte : « 📚 Répertoire suivi jusqu'à 5...h6 (4 parties) ; tu en sors au coup 6 :
  6.O-O au lieu de 6.Qb3 (joué 3 fois) ». Dernier coup suivi, coup de sortie et camp corrects.
- Pas de ❗ : normal (6.O-O n'est pas habituel, 4.c3 = Bird Gambit nommé, exclu).
- journalctl : `chess_analysis OK plies=49 ... first_move=6`, aucun ERROR / Traceback.
- Non vu en live : la ligne ❗ (il faut rejouer un coup habituel mauvais) → dette.
- Clôture du sprint 69 (00_etat, merge, tag `sprint-69`, push) pas encore faite.

## Demande de Nico : le meilleur coup à la sortie du répertoire

Position après 5...h6 : Nico joue 6.O-O, la base a 6.Qb3, le meilleur coup est 6.Bxf7+!!
Ligne attendue : 6.Bxf7+ Kxf7 7.Ne5+ (d6xe5 impossible, Qd1xd8 derrière) Kf6 (sinon mat
rapide) 8.Qf3+ Kxe5 (sacrifie le cavalier) 9.Qf7, roi noir ramené au centre pour le mater.
Stockfish 3 s confirme : 6.Bxf7+ +2,06 (6.Nxc3 +0,89) ; après 6...Kxf7 : 7.Ne5+ Kf6 8.Qf3+
Kxe5 9.Qf7 Nf6 10.f4+ … +2,30.

Souhait de Nico : dans le bilan, juste le meilleur coup ; dans la fiche de la position
(miniature), l'explication complète avec la pointe.

### Diagnostic (audit fait, rien modifié)

1. **PV tronquée par Stockfish** : même à 3 s, la PV de la position s'arrête à « Bxf7+ Kxf7 ».
   Il faut rejouer la PV et relancer l'analyse pour obtenir 7.Ne5+ … À 0,3 s (budget de
   l'analyse de partie), Stockfish donne même 6.Qb3 premier.
2. **Fiche sorte d (explosif manqué)** : affiche l'explosif 6.Nxc3!? et seulement `p.pv_san`
   court comme « Variante du meilleur coup » (`execution/routers/chess_router.py:562`,
   `_variant_line`). `best_line_san` + pointe (`chess_coach/combination.py`, `_point_text`)
   ne sont calculés que pour les sortes a/b.
3. **Ligne 📚** : `_repertoire_lines` (`chess_router.py`) n'écrit pas le meilleur coup alors
   que `rep.exit.best_san` est disponible.

### Pistes à arbitrer en conception

- A : ligne 📚 « … au lieu de 6.Qb3 (joué 3 fois) ; meilleur 6.Bxf7+ » quand best ≠ joué
  (petit). Réserve : le best à faible temps peut être faux → lié à B.
- B : fiche de la position de sortie avec la ligne du meilleur coup prolongée là où la PV
  est tronquée, et sa pointe. Questions : quand prolonger (coût Stockfish), que faire si la
  sortie de répertoire n'est pas une position critique (pas de fiche), priorité entre
  l'explosif et le meilleur coup quand le meilleur est lui-même une combinaison.

## Hors sprint (pour /amelioration)

👎 de 09:51 sur la fiche 3 (« le cavalier a besoin de sécurité » pour Nd5+, un sacrifice).
La réponse d'ARIA aggrave : « Nd5+ n'est pas un sacrifice, défendu par e4 » (faux, pas de
pion e4, la ligne moteur joue 20...cxd5 21.Rxd5) et prétend ne pas avoir les analyses
moteur des positions 1, 2, 4. 4 👎 en attente au total.
