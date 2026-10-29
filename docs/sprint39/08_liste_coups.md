# Sprint 39 — tronçon 08 : zone PGN vidée et liste des coups sous la courbe

Page seule : `interfaces/board/index.html` (+ assertion de présence dans
`tests/interfaces/test_board_interface.py`). Arbitrages lot 5 (Nico, 2026-10-29) dans
`00_etat.md`.

## État du code (audit 2026-10-29)

- Handler `#new` (l. ~640) : remet échiquier, `game`, `variant`, `evals`, colonnes ; ne
  touche pas `#pgn`.
- Une seule variante vivante : `chess.history().slice(game.cursor)` depuis
  `game.fens[game.cursor]` (`variantFens`) ; `goTo(n)` la jette (rejoue la partie
  depuis `game.start`).
- Jeu libre : ligne = `chess.history()` ; partie chargée : `game.sans`, `game.cursor`.
- Numéro de coup tiré du FEN (champ 6 + trait), déjà fait pour `playedText`.
- Ordre des éléments sous l'échiquier : `#board`, `#played`, `#graph`, `#analysis`.

## Comportement attendu

1. **« Nouvelle partie » vide `#pgn`** (valeur `""`).
2. **Liste des coups** dans un nouvel élément placé juste sous `#graph`, mise à jour par
   `refreshGame()` :
   - partie chargée : coups de `game.sans` numérotés façon PGN (`1. e4 e5 2. Nf3 …`) ;
   - variante en cours : insérée **entre parenthèses juste après le coup de la partie
     qu'elle remplace** (le coup `game.sans[game.cursor]`), numérotée depuis sa position
     de départ, ex. `10. Qxc3 (10. Bd3 Nc6 11. O-O) 10… Bxc3` ; un coup noir en tête de
     parenthèse ou après la parenthèse porte `N…` ; variante démarrée en fin de partie →
     parenthèse en fin de liste ;
   - jeu libre : `chess.history()` numérotée.
   - Le coup menant à la position affichée est surligné (fond, comme `.move:hover`).
3. **Coups cliquables** (partie chargée seulement) : clic sur un coup de la partie →
   `goTo(index + 1)` ; clic sur le k-ième coup de la variante → `goTo(game.cursor)` puis
   rejoue les k premiers coups de la variante (variante conservée jusqu'à ce point,
   `variant = true` si k ≥ 1), puis `newPosition()`. En jeu libre : liste non cliquable.
4. Liste bornée en largeur à celle de la courbe (560 px), retour à la ligne automatique.

## Tests

`test_board_interface.py` : présence de l'élément de liste dans la page servie. Logique
vérifiable sous node (DOM simulé) comme au tronçon 05, sans test permanent exigé.

## Hors scope

- Arbre de plusieurs variantes (une seule, la variante en cours).
- Variantes dans l'export ou l'envoi à ARIA (`exportPgn` inchangé).
- Sauvegarde de la variante au rechargement (toujours perdue).
- Tout ce qui touche au pseudo (tronçon 07).

## Critère de fin

`./venv/bin/pytest tests/ -q` vert ; `00_etat.md` tronçon 08 ✅.
