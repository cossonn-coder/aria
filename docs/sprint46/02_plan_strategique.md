# Sprint 46 — tronçon 02 : plan stratégique dans les miniatures

## Objectif

Chaque miniature explique le plan à suivre dans la position. Le LLM l'écrit à partir de faits structurels
calculés par le code : aujourd'hui, le bloc enrichi ne donne que des faits tactiques et le LLM invente le reste.

## Fichiers

- Nouveau `chess_coach/structure.py`, module pur (aucun import mémoire / LLM / exécution).
- `execution/routers/chess_router.py` : `_build_enriched` (ligne par position et consigne).
- Tests : nouveau `tests/chess_coach/test_structure.py`, `tests/execution/test_chess_router.py`.

## Comportement

**`structure_line(fen, nico_color) -> str`** : une ligne en français, du point de vue de Nico, avec :
- colonnes ouvertes et semi-ouvertes (de quel camp) ;
- pions isolés, doublés, passés, par camp, avec leurs cases ;
- rois : roqué ou au centre, et nombre de pions devant le roi ;
- pièces mineures encore sur leur case de départ, par camp.
Une catégorie vide n'apparaît pas. Utiliser `chess.Board` ; rien d'évaluatif (« bon », « faible »).

**Bloc enrichi** : dans la boucle des positions de `_build_enriched`, ajouter `  structure : …` près de la
ligne `matériel`. Toutes les sortes sont concernées.

**Consigne** : dans le `consigne` de `_build_enriched`, l'entrée de chaque position devient un plan :
après « Position N — », elle commence par « Plan : » et dit quoi viser dans cette position (pièce à améliorer,
colonne à occuper, pion ou roi à attaquer), d'après les lignes `structure`, `évaluation`, `motifs` et le but
du meilleur coup. Elle garde les limites actuelles (1 à 3 phrases, 400 caractères). Ne nommer une colonne, un
pion ou un roi que s'il figure dans ces lignes. Les autres règles de la consigne restent.
La consigne des occasions explosives (`d`) reste valable, le plan vient en premier.
`_split_entries` continue de couper sur « Position N — » : ne pas changer ce format.

Le prompt AnalystAgent n'est pas touché : tout se passe dans le message enrichi du router.

## Tests (cas nominal)

- `structure_line` sur une FEN choisie : colonne ouverte, pion isolé, pion passé, roi roqué, pièce non développée
  bien repérés, et du bon camp.
- `_build_enriched` : le bloc porte `structure :` et la consigne « Plan : ».
- Adapter les tests qui figent le texte de l'ancienne consigne.

## Hors scope

Stratégie rose et piège cyan (`chess_coach/live.py`), sélection, rendu, ouvertures, prompt AnalystAgent.

## Fin

`pytest tests/ -q` vert. La qualité du texte se juge au run live seulement (tronçon 05).
