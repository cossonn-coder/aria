# Sprint 38 — tronçon 02 : page — charger un PGN, naviguer, courbe d'évaluation

Lire d'abord : `CLAUDE.md`, `docs/sprint38/00_etat.md` (lots 1-2 et recos),
`docs/sprint38/audit_pgn.md`, puis `interfaces/board/index.html` en entier.
Prérequis : tronçon 01 (`POST /game` → `{"wins": [...]}`, 400 si PGN illisible).

## Objectif

Coller une partie jouée dans l'échiquier, la parcourir coup par coup avec les
flèches d'analyse live habituelles, essayer des variantes sans perdre la partie,
voir la courbe du % de gain des blancs et le coup réellement joué dans les colonnes.

## Fichiers à toucher

- `interfaces/board/index.html` (seul fichier de prod).
- `tests/interfaces/test_board_interface.py` : compléter
  `test_index_serves_chessboard_page`.

## Comportement attendu

1. **Chargement.** Dans `#controls` : une zone de texte `id="pgn"` et un bouton
   « Charger la partie ». Au clic : lecture par chess.js (`loadPgn` sur une instance
   à part ; PGN illisible → message dans `#status`, rien d'autre ne change). Puis,
   comme « Nouvelle partie » : colonnes `saved` et `blueDrawn` vidés. Elo blancs /
   noirs pré-remplis depuis les en-têtes `WhiteElo` / `BlackElo` s'ils existent
   (sinon inchangés). Position affichée = début de la partie, `newPosition()`.
   La partie chargée est gardée en mémoire de la page : liste de ses coups et un
   curseur (nombre de demi-coups joués depuis le début).
2. **Navigation.** Boutons ⏮ ◀ ▶ ⏭ (début, précédent, suivant, fin) et flèches
   gauche / droite du clavier (ignorées quand le focus est dans un champ de saisie).
   Chaque pas : rejouer la partie jusqu'au curseur dans `chess` puis `newPosition()`
   (l'analyse live et la flèche bleue rationnée fonctionnent alors sans changement,
   `chess.history()` étant la suite de la partie). Sans partie chargée, ces contrôles
   sont inactifs.
3. **Variante.** Un coup joué à la main sur l'échiquier :
   - égal au coup suivant de la partie (et pas en variante) → le curseur avance ;
   - sinon → mode variante : la partie chargée et son curseur sont gardés, un bouton
     « Revenir à la partie » (visible seulement en variante) ramène à la position du
     curseur. ⏮ ◀ ▶ ⏭ et les flèches du clavier quittent la variante et agissent sur
     la partie depuis le curseur.
   « Annuler le dernier coup » : en variante, annule le dernier coup de la variante
   (revenu au point de départ → fin de la variante) ; sur la partie, équivaut à ◀.
   « Nouvelle partie » : décharge la partie (courbe et contrôles masqués / inactifs).
4. **« joué : X » dans les colonnes.** Pour chaque position de la partie chargée,
   la page connaît le coup joué (Map FEN → SAN, mêmes clés FEN que `saved`).
   `renderSaved` ajoute « joué : X » au bloc dont la FEN est dans cette Map (rien
   pour une position de variante ou sans partie chargée).
5. **Courbe d'évaluation.** Sous l'échiquier (au-dessus de `#status`), un SVG inline
   `id="graph"` de la largeur de l'échiquier (560 px), ≈ 120 px de haut, sans
   bibliothèque :
   - au chargement, `POST /game` `{pgn}` ; en attente : texte « courbe en calcul… » ;
     erreur : texte court, la navigation reste possible ;
   - courbe des `wins` (0 en bas, 100 en haut, ligne médiane à 50 %), un point x par
     position de la partie ;
   - trait vertical sur la position du curseur (mis à jour à chaque navigation ; en
     variante, il reste sur le curseur) ;
   - clic sur le graphe → va à la position la plus proche (comme la navigation,
     quitte la variante).
   Couleurs lisibles sur le fond sombre (mode sombre permanent, sprint 37).

Ne pas changer : l'analyse live, les flèches, leurs priorités, le rationnement du
bleu, les colonnes existantes (hors ajout « joué : X »), le mini échiquier.

## Test (cas nominal)

Dans `test_index_serves_chessboard_page`, ajouter :
`assert 'id="pgn"' in page and 'id="graph"' in page`.
(Pas d'outillage JS dans le dépôt : la logique est validée au run live, tronçon 03.)

## Hors scope

- Pré-analyse des flèches sur toute la partie (lot 1 : position par position).
- Points d'erreur sur la courbe (lot 2), liste des coups cliquable, export PGN,
  retournement automatique selon le joueur, lien depuis Telegram.
- Toute modification serveur au-delà du tronçon 01.

## Critère de fin

`pytest tests/ -q` vert ; page chargée sans erreur JS évidente au relu du code
(le rendu est validé par Nico au tronçon 03).
