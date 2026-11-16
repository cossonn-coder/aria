# Sprint 59 — tronçon 02 : lecteur local de secours (captures d'écran)

## Objectif

`chess_coach/board_local.py` : `read_board(path) -> list[str] | None`, avec **la même sortie
que `ImageRouter.read_board` (tronçon 01)** : 8 chaînes de 8 caractères telles qu'affichées
(`KQRBNP` blancs, `kqrbnp` noirs, `.` vide). Sans réseau. Il sert de secours quand Gemini
est indisponible (le branchement est fait au tronçon 03).

Périmètre (décision de Nico) : **captures d'écran** d'échiquier numérique, plateau qui
remplit l'image **ou** plateau au milieu d'une capture plein écran (appli mobile avec menus
autour). Pas de photo d'échiquier physique : sur une photo, retourner `None` est acceptable.

## Contexte vérifié

- Disponibles dans le venv : `numpy`, `pillow`, `scikit-learn`. **Pas d'OpenCV** : ne pas
  en ajouter (aucune nouvelle dépendance dans ce tronçon).
- Référence : `docs/sprint59/ref/chesscom_vert.jpg` (capture chess.com, thème vert/crème,
  250×250 px, plateau seul, vu côté noirs) et sa grille exacte `chesscom_vert.txt`. Les 12
  types de pièces y figurent, sur cases claires et foncées.

## À faire

1. Copier les deux fichiers de référence dans `chess_coach/data/board_refs/` (le module lit
   tous les couples `<nom>.jpg|png` + `<nom>.txt` de ce dossier : Nico pourra ajouter
   d'autres thèmes en y déposant une capture et sa grille).
2. **Repérage du plateau** : trouver dans l'image le carré qui contient une grille 8×8 de
   cases alternées (clair/foncé). Méthode libre (numpy/PIL), par exemple : profils des
   transitions de couleur par ligne et par colonne, ou recherche du plus grand carré dont
   les 64 sous-cases alternent. Plateau introuvable → `None`.
3. **Reconnaissance** : découper le plateau en 64 cases, les ramener à une taille fixe
   (ex. 32×32), et classer chaque case par plus proche voisin parmi les cases de référence
   (`.`, ou une lettre de pièce). Pas de seuil de confiance dans ce tronçon.

## Tests (cas nominal)

`tests/chess_coach/test_board_local.py` :
- `read_board("chess_coach/data/board_refs/chesscom_vert.jpg")` → la grille de
  `chesscom_vert.txt`.
- **Capture plein écran simulée** : la même capture agrandie à ~400 px, collée à un décalage
  quelconque sur un fond uni 1080×1920 avec un bandeau d'une autre couleur en haut et en bas
  (image construite dans le test avec PIL, fichier temporaire) → la même grille.
- Une image sans échiquier (ex. fond uni ou dégradé) → `None`.

## Hors scope

- Photo d'échiquier physique (dette : modèle local réentraîné sur le jeu de Nico).
- Aucun branchement dans le pipeline, aucun appel réseau, aucune écriture mémoire.
- Ne pas toucher `chess_coach/board_reading.py` (tronçon 01) au-delà d'un import si besoin.

## Critère de fin

`pytest tests/ -q` vert ; les trois tests ci-dessus passent.
