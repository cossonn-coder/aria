# Sprint 38 — état de conception

**Phase** : B figée (2026-10-26, OK de Nico) — prêt pour `/sprint-auto sprint 38`.
**Branche** : `feat/sprint38-pgn`.
**Cible** : #94 — charger un PGN dans l'échiquier pour analyser une partie jouée,
avec courbe d'évaluation.

## Audit

`audit_pgn.md` : besoin couvert côté page (chess.js `loadPgn` + curseur +
`newPosition()` à chaque pas) ; le worker n'analyse que la position affichée ;
colonnes indexées par FEN (persistent en naviguant) ; pas d'outillage de test JS.
§4 : `analysis.analyze_game` évalue déjà toutes les positions (0,15 s/position) →
courbe sans code d'analyse nouveau.

## Décisions arrêtées

- Cible = #94 charger un PGN (Nico, 2026-10-26).

Lot 1 (Nico, 2026-10-26) :
- **Analyse position par position** : seule la position affichée est analysée (worker
  inchangé) ; les colonnes se remplissent en naviguant. Pas de pré-analyse des flèches.
- **Coup hors partie = variante** : la suite de la partie chargée est gardée ; un bouton
  « Revenir à la partie » ramène au coup de la partie où l'on était.
- **« joué : X »** dans chaque bloc de colonne dont la position appartient à la partie
  chargée (coup réellement joué à cette position).

Lot 2 (Nico, 2026-10-26) — graphe d'évaluation demandé par Nico :
- **Courbe du % de gain des blancs** (0-100, ligne des 50 %) sur toute la partie chargée,
  calculée d'avance côté serveur : `POST /game` {pgn} → `parse_pgn` + `analyze_game` →
  une valeur par position. ≈ 12 s pour 80 demi-coups [estimation 0,15 s × 80, non mesurée].
  L'analyse live reste position par position (lot 1 inchangé).
- **Clic sur la courbe = aller au coup** ; trait vertical sur le coup affiché.
- **Courbe seule**, pas de points d'erreur.

Recos de conception (Claude, acceptées avec l'OK de Nico) :
- Elo blancs / noirs pré-remplis depuis `WhiteElo` / `BlackElo` (inchangés si absents).
- Navigation : ⏮ ◀ ▶ ⏭ + flèches gauche/droite ; charger un PGN vide colonnes et bleu
  rationné comme « Nouvelle partie » et place au début.
- Coup joué à la main égal au coup suivant de la partie = on avance (pas de variante).
- PGN sans en-tête accepté (`parse_pgn` exige un `[` : réessai avec un en-tête minimal).
- Page + route `/game` ; `live.py`, worker et `analysis.py` inchangés ; SVG inline.

## Questions ouvertes

(aucune)

## Tronçons

- 01 route `POST /game` (`01_route_game.md`) ✅ (`game_wins` + `_Handler._game`, 370 tests verts)
- 02 page : PGN, navigation, variante, « joué : X », courbe (`02_page_pgn_graphe.md`) ✅ (`index.html` seul, 370 tests verts)
- 03 run live, Nico (`03_run_live.md`, parties : `run_live_parties.txt`) ⏳

## Run live (Nico, 2026-10-27)

OK : 1 (Elo pré-remplis, courbe), 2, 3, 4, 7, 8, 9, 10 (« PGN illisible »).
À éclaircir : 5 « joué : X » non vu. Clés FEN vérifiées hors page (chess.js 1.4.0,
partie 1 : 78 demi-coups, 0 position manquante, coup 7 → `Bxf7+`) : la ligne ne
s'affiche que dans un bloc de colonne, donc seulement si une flèche orange / cyan / rose
a été trouvée sur cette position. 6 : absence de « joué » en variante = attendu.
Correctif (Nico, 2026-10-27) : « joué : X » affiché en permanence sous l'échiquier sur une
position de la partie chargée (hors variante), et pièce du coup joué cerclée de blanc.
Reste à valider en live (mini-run, voir 03_run_live.md).
Suite : nouvelles demandes → `/conception sprint 39`.
Nouvelles demandes (hors tronçons, à concevoir) :
- courbe du meilleur coup à chaque position, en comparaison de la courbe jouée ;
- indication des chances de mat sur la courbe ;
- courbe visible en permanence, y compris en jeu libre ;
- partie enregistrée au fil des coups joués, export PGN.

## Dettes

#94 (rejeu PGN) : partiellement fermée par le sprint si le run live est OK.
Aucune nouvelle à ce stade.

## §REPRISE

Tronçons 01 et 02 faits (02 non commité par le sous-agent). Reste le run live (tronçon 03,
Nico) : lire `CLAUDE.md`, ce fichier, puis `03_run_live.md`.
Prochaine étape : `/sprint-auto sprint 38` (reprend au tronçon 03, run live).
