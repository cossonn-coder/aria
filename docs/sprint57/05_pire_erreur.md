# Sprint 57 — Tronçon 05 : pire erreur garantie, paris explosifs hors « occasions manquées »

Correctif issu du run live du 2026-11-12 (partie 14:09, `docs/sprint57/partie_live_1409.pgn`) :
`critical=['d:10.O-O', 'd:13.axb6', 'd:18.Qxa7', 'd:40.Rcb6']`. Quatre explosifs ont pris tout
le budget ; la gaffe de Nico 41.Rc6 (−42 pts, tournant de la partie) n'a aucune miniature. Aux
coups 10, 13 et 18, Nico avait joué le meilleur coup du moteur, et plusieurs de ces explosifs
sont des « paris » (ARIA écrit elle-même que l'espérance n'est pas meilleure). Même motif sur la
partie 14:40 (4 × d).

## Décisions de Nico (2026-11-12)

1. **La pire erreur de Nico a toujours une miniature.** Pire erreur = la position de plus fort
   score parmi `_critical_errors(plies, nico_color, first_move)` (sortes a et b). Si cette liste
   est vide, rien ne change.
2. **Un explosif « pari » n'est pas une occasion manquée.** Pari = même critère que la mention
   existante `chess_router.py` (~l. 774) : `expected − best_expected < _GAIN_MIN` (explosive.py).
   - Choix des miniatures : seuls les explosifs **non-paris** gardent la priorité d (avant a).
     Les paris reprennent leur place d'avant le sprint 57 : **après a**.
   - Ligne 🔎 : les paris en sont exclus (les 3 plus forts sont pris parmi les non-paris).
     Ligne omise si plus rien à afficher (règle existante).

Ordre final du budget de 4 dans `select_critical` (analysis.py) :
**pire erreur → b → d non-pari → a → d pari → e → c**, chaque groupe par score décroissant,
position déjà prise sautée (mécanique existante), affichage chronologique inchangé.

## Points de code (hypothèses à vérifier)

- `select_critical` reçoit `explosive` = liste de `CriticalPosition(kind="d", …)` portant
  `.explosive` (ExplosiveMove avec `expected`, `best_expected`). Le prédicat « pari » doit être
  **un seul** helper partagé par analysis.py et chess_router.py (pas de seuil recopié) ;
  attention au sens d'import (explosive.py importe déjà analysis.py : ne pas créer de cycle —
  définir le helper côté analysis.py, ou passer par l'objet).
- `_explosive_skipped` : inchangé (toujours « b remplissent le budget »).
- Docstring de `select_critical` à mettre à jour.

## Tests (calibrage : cas nominal)

- `select_critical` : 4 explosifs non-paris + 1 erreur a → l'erreur a est retenue (pire erreur).
- `select_critical` : un explosif pari passe après une erreur a.
- `_missed_line` : un pari n'apparaît pas dans la ligne 🔎.

## Vérification VM (si Stockfish/Maia disponibles sur la VM, sinon le signaler)

Rejouer `docs/sprint57/partie_live_1409.pgn` via `chess_coach.analysis.analyze` (même appel que
chess_router) et noter dans le rapport la nouvelle liste `critical=[…]` : 41.Rc6 doit y figurer.

## Run live

Renvoyer la partie 14:09 n'est pas possible (doublon). Critère au prochain run : sur une partie
neuve avec une erreur de Nico, `critical=[…]` contient sa pire erreur ; la ligne 🔎 ne contient
aucun explosif « pari ».
