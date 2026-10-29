# Sprint 41 — tronçon 01 : page d'échiquier mobile façon lichess

Lire d'abord `CLAUDE.md`, `docs/sprint41/00_etat.md`, `docs/sprint41/audit_board_mobile.md`
(§4 : ce qui casse sur téléphone, avec les lignes du code).

## Objectif

Sur un écran de téléphone (largeur ≤ 700 px), la page de l'échiquier prend une disposition
inspirée de l'échiquier d'analyse mobile de lichess, avec **toutes** nos fonctions, utilisables
au doigt, et s'affiche correctement comme Mini App Telegram. **Sur PC (> 700 px), la page reste
visuellement et fonctionnellement identique à aujourd'hui.**

## Fichiers à toucher

| Fichier | Changement |
|---|---|
| `interfaces/board/index.html` | seul fichier de prod touché : HTML, CSS (media query), JS |
| `tests/interfaces/test_board_interface.py` | étendre `test_index_serves_chessboard_page` |

Aucun changement Python côté serveur (`board_interface.py` inchangé).

## Disposition mobile attendue (≤ 700 px)

```
┌────────────────────────┐
│▐                       │  ▐ = barre d'évaluation verticale
│▐   échiquier pleine    │
│▐   largeur (carré)     │
├────────────────────────┤
│ statut d'analyse       │  #status (tap → réponses humaines #replies)
│ joué : … · précision   │  #played, #accuracy
├────────────────────────┤
│ Coups Courbe 🟠 ● ●     │  onglets : Coups / Courbe / explosifs / pièges / stratégie
│ (un seul panneau)      │
├────────────────────────┤
│ ☰   ⏮   ◀   ▶   ⏭    │  barre fixe en bas d'écran
└────────────────────────┘
```

1. **Viewport** : `<meta name="viewport" content="width=device-width, initial-scale=1">`.
2. **Échiquier** : carré, toute la largeur disponible moins la barre d'évaluation ; marges
   réduites. Chessground doit se redessiner au bon format (si besoin `ground.redrawAll()` sur
   `resize`).
3. **Barre d'évaluation** (`id="evalbar"`, nouvelle, mobile seulement) : fine barre verticale
   à gauche de l'échiquier, part blanche = % de gain des blancs de la position affichée
   (`evals.get(chess.fen()).win`), côté blanc en bas quand l'échiquier est à l'endroit,
   inversée quand il est retourné (`ground.state.orientation`). Mat (`mate`) → barre pleine du
   camp qui mate. Valeur inconnue → barre inchangée. Mise à jour là où l'affichage se rafraîchit
   déjà (`refreshGame`, appelé après chaque réponse `/eval` et `/game` et à chaque position).
   Aucun appel serveur en plus.
4. **Onglets** (`id="tabs"`) : Coups (`#moves`), Courbe (`#graph` + rien d'autre), puis les
   trois colonnes existantes `#saved-explosive`, `#saved-trap`, `#saved-strategy` (pastilles
   orange `#ff7f00`, cyan `#00e5ff`, rose `#ff5fb0`). Un seul panneau visible à la fois ; Coups
   par défaut. Pas de défilement horizontal de la page.
5. **Courbe** : pleine largeur, mise à l'échelle (`viewBox="0 0 560 200"` + largeur CSS
   100 %, ou équivalent). Le clic sur la courbe (`$("graph")` click, aujourd'hui
   `event.clientX - left` divisé par `GRAPH_W / …`) doit convertir la position du clic à
   l'échelle affichée (`× GRAPH_W / rect.width`) : sans effet sur PC où les deux valent 560.
6. **Barre du bas** (`id="bottombar"`, fixe, gros boutons) :
   - ◀ / ▶ = `stepBack()` / `stepForward()` (mêmes fonctions que les flèches du clavier :
     jeu libre, variante et partie chargée).
   - ⏮ / ⏭ = début / fin de la ligne : en partie chargée hors variante, `goTo(0)` /
     `goTo(game.sans.length)` ; sinon tous les coups défaits vers `ahead` / tous rejoués. **Un
     seul `newPosition()` à la fin**, pas un par coup (chaque appel fait un `POST /position`).
   - ☰ ouvre / ferme le menu.
7. **Menu ☰** : les contrôles actuels de `#controls` (Nouvelle partie, Annuler, Retourner,
   zone PGN + Charger, Revenir à la partie, Elo, Je joue, noms, Exporter, Envoyer à ARIA,
   `#pgn-status`, cases des calques) dans un panneau qui s'ouvre au-dessus de la page et se
   ferme par ☰ ou par un bouton/zone de fermeture. Les boutons ⏮◀▶⏭ de `#nav` peuvent y être
   masqués (doublons de la barre du bas).
8. **Doigt au lieu du survol** (écrans `(hover: none)`) :
   - tap sur un coup d'une variante (spans créés par `variation()`, colonnes et panneau des
     réponses) → mini échiquier `#mini` à côté du tap ; tap ailleurs → masqué ;
   - tap sur `#status` quand un coup explosif est affiché → ouvre / ferme `#replies` ;
   - liste `#moves` : le tap garde son comportement actuel (`goTo`), le mini ne reste pas
     affiché.
   Sur PC, le survol actuel est inchangé.
9. **Mini App Telegram** : `<script src="https://telegram.org/js/telegram-web-app.js"></script>`
   dans `<head>` (script classique, avant le module). Dans le module : si
   `window.Telegram?.WebApp?.initData` est non vide (on est dans Telegram) → `ready()`,
   `expand()`, `disableVerticalSwipes()`. Raison : sans `disableVerticalSwipes`, glisser une
   pièce vers le bas réduit / ferme la Mini App. Hors Telegram (PC, navigateur), rien.

## Contraintes

- **Un seul élément par `id`** : on réorganise / masque les éléments existants par CSS
  (media query `max-width: 700px`) et un peu de JS ; on ne duplique ni le DOM ni la logique.
  Les ids existants (`pgn`, `graph`, `export`, `send`, `playing`, `name-white`, `name-black`,
  `moves`, `accuracy`, `show-trap`, `show-strategy`…) restent : le test existant les vérifie.
- Les nouveaux éléments (barre d'évaluation, onglets, barre du bas, bouton ☰) sont masqués sur PC.
- Clavier, molette, `localStorage`, routes serveur : inchangés.
- Commentaires en français, style du fichier (un commentaire de tête par fonction / bloc).

## Tests (cas nominal)

Étendre `test_index_serves_chessboard_page` : la page servie contient
`name="viewport"`, `telegram-web-app.js`, `id="evalbar"`, `id="tabs"`, `id="bottombar"`.
`pytest tests/ -q` vert.

Pas de navigateur headless sur la VM : le rendu est validé au run live (tronçon 03). Vérifier
au moins à la main que le module JS n'a pas d'erreur de syntaxe évidente (ex. extraire le
`<script type="module">` dans un fichier temporaire du scratchpad et `node --check` s'il est
installé ; sinon relecture).

## Hors scope

- Refonte PC façon lichess (décision D7 : mobile seul).
- Nouvelles routes ou calculs serveur ; changement des analyses ou des flèches.
- `/board` et le bouton Mini App (tronçon 02) ; Tailscale (run live).
- Partage d'état PC ↔ téléphone, export PGN dans la webview (dettes notées dans `00_etat.md`).

## Critère de fin

Page mobile implémentée selon 1-9, PC inchangé à la relecture du CSS (règles nouvelles sous
media query ou sur éléments masqués sur PC), test étendu, `pytest tests/ -q` vert, commit local.
