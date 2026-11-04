# Tronçon 02 — échiquier live : meilleur coup immédiat et sans limite, résultat gardé

## Objectif

Case « Meilleur coup » cochée = la flèche bleue s'affiche à chaque coup, presque tout de suite. Revenir sur une position redonne son résultat sans recalcul. Constat : `audit_analyse_stable.md` §6 à §8.

## Fichiers

- `interfaces/board_interface.py` (`BoardWorker`), `chess_coach/live.py` (`analyse_pass`).
- `interfaces/board/index.html`.
- `tests/chess_coach/test_live.py`, `tests/interfaces/test_board_interface.py`.

## Comportement attendu

**Résultat de tête publié tout de suite** : dès l'analyse de tête d'`analyse_pass` (0,5 s), `best` et `forced` arrivent dans l'état du worker, sans attendre la fin de la passe. Le mécanisme est libre. Les faux `run_pass` des tests ont la signature `(proxy, fen, elo, models_dir)` ; les garder valides ou les adapter simplement. Une passe périmée n'écrit rien dans l'état d'une autre position.

**Flèche immédiate (page)** : `state.best` si présent, sinon `evals.get(fen).best` (SAN, déjà reçu de `/eval` ou `/game`), converti en cases avec chess.js. `state` peut être `null` au début d'une position : `drawShapes` doit dessiner ce repli quand même. Redessiner quand `evals` reçoit la valeur de la position affichée (`evalLine` n'appelle aujourd'hui que `refreshGame`).

**Limites supprimées (page)** : retirer `blueAllowed`, `blueDrawn` et leurs usages (lignes 179, 265-272, 288-291, 906, 952), ainsi que `!shapes.length`. Case décochée = aucune flèche bleue.

**Couleur si même coup** : le bleu remplace la flèche du même coup (orange, cyan, rose). Exception : seul coup affiché (case « Seul coup » cochée) : vert, pas de bleu. Les autres flèches restent. Mettre à jour le commentaire au-dessus de `drawShapes`.

**Conservé** : case décochée au chargement d'un PGN et à « Nouvelle partie » (lignes 907, 944).

**Résultat gardé par position** (`BoardWorker`) : clé `(fen, elo)`, valeur = dernier résultat de passe terminée et numéro de cette passe. Au retour : l'état reprend aussitôt ce résultat, et le worker continue aux passes restantes (aucune si la dernière est finie). Pas de plafond ni de persistance disque.

## Tests (cas nominal)

- `best` visible avant la fin de la passe (faux `run_pass` ou faux moteur bloqué).
- Retour sur une position terminée : même résultat, `run_pass` non rappelé.
- Page : `/` ne contient plus `blueAllowed` (le JS n'a pas de banc de test ; le reste au run live).

## Hors périmètre

Interruption pendant un appel moteur ; nœuds fixes en live ; `/eval` ; rendu des miniatures ; une flèche qui change entre deux passes (approfondissement normal).

## Critère de fin

`pytest tests/ -q` vert. À valider au run live.
