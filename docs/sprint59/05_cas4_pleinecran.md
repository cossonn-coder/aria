# Sprint 59 — tronçon 05 : capture plein écran du cas 4 (déclenchement + lecteur local)

## Objectif

La capture du cas 4 du run live (chess.com plein écran, coordonnées dessinées dans les
cases, dernier coup surligné en jaune) avec la légende « les blancs jouent, que faire ? »
doit :
1. déclencher la résolution d'échiquier ;
2. être lue **exactement** par le lecteur local `chess_coach/board_local.py` (secours de
   Gemini).

Diagnostic complet et mesures : `docs/sprint59/audit_position_image.md`, §Audit 2, A et B.

## Contexte vérifié

- Capture : `docs/sprint59/ref/chesscom_pleinecran.jpg` (858×931). Grille exacte :
  `docs/sprint59/ref/chesscom_pleinecran.txt`.
- Déclenchement : `_CHESS_CAPTION_RE` dans `cognition/cognitive_classifier.py:127`.
- Lecteur local : `board_local.read_board` renvoie aujourd'hui `None` sur cette capture.
  Trois causes, mesurées une à une :
  1. **Repérage** (`_find_lines`) : x → (18, 103), y → (52, 103). La 1re ligne retenue est
     le **bord extérieur** du plateau, très contrasté contre le fond sombre. Deux fenêtres
     de 7 lignes ont le même score et `argmax` prend la première. Bonnes bornes des cases :
     xs = 19, 122, …, 843 et ys = 53, 156, …, 877.
  2. **Alternance** (`_alternates`) : elle reste refusée même avec les bonnes bornes. Les
     cases surlignées et les chiffres de coordonnées (coin haut-gauche des cases de la
     colonne de gauche, là où l'échantillon est pris) font sauter `spread < contrast / 2`,
     qui prend le maximum sur les 64 cases.
  3. **Reconnaissance** : avec les bonnes bornes et sans le contrôle d'alternance, la lecture
     fait 63 cases justes sur 64. Seule erreur : le roi noir sur e7 (case surlignée en
     jaune), lu `b`. La distance porte sur les pixels bruts, et le fond jaune n'existe dans
     aucune référence.

## À faire

1. Ajouter `blancs?` et `noirs?` à `_CHESS_CAPTION_RE`. Ne pas ajouter « jouent »,
   « plateau » ni « pièces » (décision de Nico : faux positifs).
2. Copier la capture et sa grille dans `tests/chess_coach/data/` (fixture de test).
   **Ne pas** la mettre dans `chess_coach/data/board_refs/` : le test se lirait lui-même.
3. Lecteur local, méthode libre (numpy/PIL, **pas d'OpenCV**, aucune nouvelle dépendance).
   Intentions :
   - repérage : quand le bord extérieur est pris pour une ligne intérieure, choisir la
     bonne fenêtre, par exemple en essayant aussi les fenêtres décalées d'une case et en
     gardant celle dont les cases alternent ;
   - alternance : tolérer quelques cases aberrantes (surlignage du dernier coup : 2 cases ;
     coordonnées) au lieu d'exiger que les 64 cases passent ;
   - reconnaissance : rendre la comparaison peu sensible à la couleur de fond de la case
     (par exemple en neutralisant les pixels proches du fond estimé de chaque case, des deux
     côtés : case lue et références), et peu sensible aux coordonnées dessinées dans les
     coins (par exemple en rognant une marge).

## Tests (cas nominal)

- `tests/chess_coach/test_board_local.py` : `read_board(<fixture chesscom_pleinecran.jpg>)`
  → la grille de `chesscom_pleinecran.txt`. Les 3 tests existants restent verts.
- `tests/images/test_chess_image.py`, dans `test_is_chess_image` : la légende
  « les blancs jouent, que faire ? » avec une description sans mot d'échecs → `True`.

## Hors scope

- Pas de photo d'échiquier physique, pas d'autre thème (lichess…).
- Pas de seuil de confiance, ni de changement de la sortie de `read_board`.
- Aucun changement dans `image_router.py` ni dans `board_reading.py`.

## Critère de fin

`pytest tests/ -q` vert, nouveaux tests compris.
