# Sprint 51, tronçon 02 — conversion d'une position gagnante

## Objectif
Quand Nico ne gagne pas une partie où il a longtemps été gagnant, ARIA le dit avec des faits
écrits par le code : durée de la période gagnante, et **idées du moteur répétées que Nico n'a
pas jouées**, chacune nommée par son concept (activer le roi, pousser le pion passé…). Une
miniature montre l'idée principale ; le LLM explique les concepts dans le bilan.

Pourquoi : sur la partie de référence (dusha28), Nico est à ≥ 80 % pendant 47 coups sans
aucune perte ≥ 10, donc aucune position critique ne parle de conversion. Le signal est la
répétition : Kd3 proposé aux coups 31, 32, 33, 35 (joué au 37), b5 aux coups 43, 44, 45, 47,
48 (joué au 52). Détail : `docs/sprint51/audit_conversion.md` §1.b.

## À faire

### 1. Nouveau module `chess_coach/conversion.py` (fonctions pures sur `PlyAnalysis`)
- **Période** : seulement si l'issue (`summary["outcome"]`) est `loss` ou `draw` (pas `win`,
  pas `unknown`). Plus longue suite de coups **consécutifs de Nico** à `win_before ≥ 80` ;
  retenue si elle compte ≥ 10 coups. Rend les plies de Nico de la période, ou `None`.
- **Idées répétées** : dans la période, coups de Nico où `best_san != san`. Une idée = un
  même `best_san` présent **≥ 3 fois dans une fenêtre de 6 coups consécutifs de Nico** de la
  période. Pour chaque idée : le coup (SAN), les numéros de coup où il était proposé et non
  joué (dans la période), le 1er ply proposé, le numéro du coup où Nico l'a finalement joué
  (premier coup ultérieur de Nico avec ce SAN, sinon `None`), le concept. Au plus **2 idées**,
  par nombre d'occurrences décroissant puis ordre chronologique.
- **Concept** (depuis `fen_before` et `best_uci` du 1er ply proposé) :
  roi → « activer le roi » ; pion figurant dans `chess_coach.structure._passed(board, color)` →
  « pousser le pion passé » ; autre pion → « avancer le pion » ; prise → « prendre » + pièce
  prise (« prendre le pion a2 ») ; autre pièce → « améliorer le cavalier / le fou / la tour /
  la dame ».
- **Texte** (une ligne, écrite par le code), format :
  `🔄 Conversion : 47 coups à 80 % ou plus (coups 9 à 55) sans gagner. Idées du moteur non
  jouées : activer le roi (Kd3, proposé aux coups 31, 32, 33, 35, joué au 37) ; pousser le pion
  passé (b5, proposé aux coups 43, 44, 45, 47, 48, joué au 52).`
  Sans idée : la première phrase seule. Jamais joué : « jamais joué ».

### 2. `execution/routers/chess_router.py`
- `_execute_game` : calculer période et idées. Texte affiché : la ligne Conversion juste sous
  la ligne du déroulé (`story`), au-dessus du bilan du LLM.
- **Miniature** (hors budget des 4 positions) : idée principale (la 1re), position
  `fen_before` de son 1er ply proposé, `render_position` avec le meilleur coup (flèche verte),
  le coup joué et `best_line_uci=p.pv_uci[:3]`. Légende écrite par le code :
  `Conversion — coup 43 : idée répétée 🟢 43.b5 (pousser le pion passé), proposée 5 fois ; joué 🔵 43.Ka1`
  (pastilles via les constantes existantes ; le tronçon 04 les recolorera).
  Elle est ajoutée **après** `_split_entries` (le LLM n'a pas d'entrée « Position » pour elle),
  **avant** la courbe.
- `_build_enriched` : si période, ligne `Conversion (données) : …` (même texte) après la ligne
  `Déroulé (données)`, et une consigne : dans le Bilan, une phrase par idée nommée expliquant
  pourquoi ce concept fait progresser une position gagnante, sans autre coup que ceux fournis.

### 3. Fiche (`chess_coach/summary.py::summarize`)
Clés scalaires : `conversion_moves` (int, nombre de coups de la période, sinon `None`) et
`conversion_ideas` (str, ex. `"Kd3 activer le roi ×4 ; b5 pousser le pion passé ×5"`, sinon
`None`). `summarize` dispose de `analysis` et calcule déjà l'issue.

## Tests (cas nominal)
`tests/chess_coach/test_conversion.py` : plies synthétiques (période de 12 coups à 85 %, un
même `best_san` roi proposé 3 fois en 6 coups puis joué) → période, une idée « activer le
roi », texte attendu ; issue `win` → `None`. Router : la ligne Conversion apparaît dans le
texte et la miniature avant la courbe. `pytest tests/ -q` vert.

## Hors scope
- Compteur des idées manquées d'une partie à l'autre (dette).
- Plan adverse répété (g5 ×9 sur la référence) (dette).
- Thème « Convertir l'avantage » du profil (`player_model.py`) : ne pas toucher.
- Horloge, coups longs : tronçon 03. Couleurs des pastilles : tronçon 04.

## Critère de fin
Tests verts. Sur la partie de référence, la règle doit retenir Kd3 et b5, pas Nd5 (proposé
aux coups 34, 41, 42 : 2 fois seulement dans une fenêtre de 6) ni Nc2 (17, 37, 38, 50) : à
vérifier au run live, pas par fixture.
