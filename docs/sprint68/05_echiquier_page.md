# Sprint 68 — tronçon 05 : échiquier, côté page (joueur du bas + anticipation)

Lire d'abord `CLAUDE.md`, `docs/sprint68/00_etat.md`, `audit_joueur_du_bas.md` §1-§3, puis le
kickoff 04 (contrat serveur : `bottom`, `result == "anticipation"`, `anticipated`).
Fichier : `interfaces/board/index.html` (un seul fichier, module ES, Chessground 9.2.1).

## Décisions de Nico (2026-11-25)

- Joueur du bas = orientation de l'échiquier (`ground.state.orientation`).
- Orientation automatique sur « Je joue » (`#playing`), fiche ouverte depuis `/parties` comprise ;
  ⟲ peut toujours retourner.
- Au tour adverse : jusqu'à 3 coups adverses, chacun avec sa pièce cerclée et une flèche grise
  semi-transparente numérotée 1, 2, 3 ; la réponse du joueur du bas en flèche bleue portant le
  même numéro. Les flèches gratuites déjà connues de la page restent (bleu tiré de `evals`,
  flèche d'erreur, cercle du coup joué).
- Case « Anticipation » dans le menu, cochée par défaut.

## À faire

1. **Orientation.** Une fonction qui pose `ground.set({orientation})` depuis `#playing` quand il
   vaut `white` / `black` (« aucun » : on ne touche pas) puis `drawEvalbar()`. Appelée : au
   changement de `#playing`, dans `openStored` (après `$("playing").value = stored.playing`),
   dans `restoreState`, et à la réponse de `/game` si elle porte `playing` (PGN reconnu comme
   fiche, tronçon 04 : poser aussi `$("playing").value`).
2. **Retourner = nouvelle analyse.** `#flip` appelle `newPosition()` après `toggleOrientation()`.
   `newPosition` envoie `bottom: ground.state.orientation` dans `POST /position`.
3. **Flèches.** Pinceau gris semi-transparent (ex. `{key: "a", color: "#cccccc", opacity: 0.45,
   lineWidth: 10}`) dans `drawable.brushes`. Dans `drawShapes`, si `state.anticipated` et la case
   cochée : pour chaque coup k (1 à 3) un cercle sur `uci[0:2]`, la flèche grise avec
   `label: {text: String(k)}`, et si `reply_uci` la flèche bleue avec le même `label`.
   Chessground 9.2.1 : `DrawShape.label = {text, fill?}` (vérifié dans `dist/draw.d.ts`).
4. **Texte.** `statusText` : cas `"anticipation"` (ex. « 🔮 coups adverses probables — passe x/y »).
   Panneau `#replies` (celui du coup explosif) : une ligne par coup anticipé,
   « k. san — p % — » puis `variation(positionFen, line_san)` (survol / tap = mini échiquier).
   `fillReplies` et l'ouverture du panneau (survol PC, tap téléphone) acceptent
   `state.anticipated` comme `state.explosive`.
5. **Miniatures d'un PGN reconnu.** Si la réponse de `/game` porte `minis`, les poser dans
   `game.minis` et appeler `renderMinis()` (aujourd'hui seules les fiches de `/stored` en ont).
6. Case `<label>Anticipation <input id="show-anticipation" type="checkbox" checked></label>`
   avec les autres calques, `change` → `drawShapes`.

## Tests

Page sans suite JS : vérifier que `tests/interfaces/test_board_interface.py` (page servie) reste
vert ; ajouter une assertion simple que la page contient `show-anticipation` et `bottom`.

## Hors scope

Serveur (tronçon 04), colonnes sauvegardées, courbe, exercice « 2e chance » (`drawShapes` ne
dessine toujours rien pendant l'exercice).

## Critère de fin

`pytest tests/ -q` vert. Rendu réel (flèches, orientation, téléphone) : run live (tronçon 06).
