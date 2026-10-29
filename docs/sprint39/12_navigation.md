# Sprint 39 — tronçon 12 : navigation dans la ligne aux flèches et à la molette

Page seule : `interfaces/board/index.html` (+ assertion de présence si utile dans
`tests/interfaces/test_board_interface.py`). Arbitrages lot 7 (Nico, 2026-10-29) dans
`00_etat.md`.

## État du code (audit 2026-10-29)

- Flèches existantes (l. ~775) : `keydown` ← / → → `goTo(game.cursor ∓ 1)`, partie chargée
  seulement, ignoré si la cible est `INPUT` / `TEXTAREA` (pas `SELECT`). En variante, ←
  jette la variante (comme ◀). Rien en jeu libre. Pas de molette.
- Modèle actuel : `game.cursor` sert à la fois de **position affichée dans la partie** et
  d'**ancrage de la variante** ; variante = `chess.history().slice(game.cursor)` ;
  `variant` = booléen. Utilisé par `variantFens`, `renderMoves`, `graphLength`, `curve`,
  `playedText`, `accuracy`, `exportPgn`, `playedOnBoard`, `goTo`, bouton `#back`.
- Jeu libre : ligne = `chess.history()` (courbe, liste, précision, export, `saveState`).
- `#undo` : `chess.undo()` (coup perdu). Éléments : `#board`, `#graph` (svg), `#moves`.

## Comportement attendu

### Modèle : une pile des coups « devant »

1. `ahead` : SAN des coups défaits par ← (sommet = coup suivant). **Ligne affichée** =
   `chess.history()` suivi de `ahead` (dans l'ordre de rejeu). Position affichée = fin de
   `chess.history()`.
2. **←** : si `chess.history()` n'est pas vide (et en partie chargée, au-dessus de
   `game.start`), `chess.undo()` et empile le coup sur `ahead`. **→** : si `ahead` n'est
   pas vide, rejoue le sommet ; sinon, en partie chargée sur la ligne de la partie, joue le
   coup suivant de la partie (comme ▶). Chaque pas : `refreshGame()` + `newPosition()`.
3. **Coup joué sur l'échiquier** : égal au sommet de `ahead` → le dépile (même effet que →) ;
   sinon `ahead` est vidé (la suite est coupée), puis la logique actuelle.
4. Toute autre action de navigation vide `ahead` : boutons ⏮ ◀ ▶ ⏭, « Revenir à la partie »,
   clic dans la liste ou sur la courbe (`goTo`), « Annuler », « Nouvelle partie »,
   chargement d'une partie. **Boutons ⏮ ◀ ▶ ⏭ inchangés** (reco Claude).

### Partie chargée : la variante n'est plus perdue par ←

5. Ancrage de la variante = premier indice où la ligne affichée s'écarte de `game.sans`
   (aucun écart → pas de variante). Position affichée avant ou à l'ancrage → on est **dans la
   partie** (`game.cursor` = position affichée, la variante reste visible dans la liste et sur
   la courbe, partant de l'ancrage) ; après → **dans la variante**. Liste (parenthèse après le
   coup de l'ancrage), courbe cyan, `variantFens`, `graphLength`, « joué », précision et
   export lisent l'ancrage et la ligne affichée, et non plus `game.cursor` comme ancrage.
   Ex. : variante de 3 coups au coup 10, ← × 5 → on est au coup 8 de la partie, la
   parenthèse est toujours là ; → × 5 → retour en fin de variante.
6. Le surlignage de la liste et le trait de la courbe suivent la position affichée (dans la
   partie ou dans la variante). « Revenir à la partie » visible tant qu'une variante existe.

### Jeu libre

7. Liste, courbe, précision, export et `saveState` portent sur la **ligne affichée** entière
   (coups devant compris) ; surlignage / trait / « joué » = position affichée. Au rechargement,
   la ligne entière est rejouée (position en fin de ligne).

### Entrées

8. Flèches ← / → partout (partie chargée et jeu libre), ignorées dans `INPUT`, `TEXTAREA`,
   `SELECT`.
9. Molette au-dessus de `#board`, `#graph` et `#moves` : vers le bas (`deltaY > 0`) = →, vers
   le haut = ← ; `preventDefault` (écouteur `{ passive: false }`) pour que la page ne défile
   pas ; ailleurs, défilement normal. Un pas par événement (pas d'anti-rebond ; à revoir au
   live si le pavé tactile va trop vite).

## Tests

Assertion de présence si un élément est ajouté (sinon aucune nouvelle). Logique vérifiable
sous node (DOM simulé) : jeu libre ← ← → ; variante puis ← au-delà de l'ancrage puis → ;
coup joué égal / différent du sommet de `ahead`.

## Hors scope

- ↑ / ↓, Début / Fin au clavier.
- Arbre de plusieurs variantes ; variante perdue au rechargement (inchangé).
- Boutons ◀ ▶ alignés sur les flèches.

## Critère de fin

`./venv/bin/pytest tests/ -q` vert ; `00_etat.md` tronçon 12 ✅.
