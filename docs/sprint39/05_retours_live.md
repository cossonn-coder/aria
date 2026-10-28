# Sprint 39 — tronçon 05 : retours du run live (variante, numéros, lisibilité, noms)

Lire d'abord `CLAUDE.md`, `00_etat.md` (lot 4 et audit tronçon 05) et `03_page.md`
(comportement livré par le tronçon 03, à conserver hors des points ci-dessous).

## Fichiers

- `interfaces/board/index.html` (seul fichier de prod).
- `tests/interfaces/test_board_interface.py` : `test_index_serves_chessboard_page`.

Conventions de la page : `$`, `chess`, `game` (`{start, sans, fens, played, headers, pgn,
cursor, wins, message}`), `variant`, `evals` / `evalAsked` / `evalChain`, `curve()`,
`loss()`, `playedText()`, `evalLine()`, `drawGraph()`, `exportPgn()`, `saveState()` /
`restoreState()`, `loadGame()`, commentaires en français.

## Comportement attendu

1. **Variante superposée sur la courbe** (partie chargée + `variant`) :
   - la courbe de la partie reste entière, en blanc, avec son ombrage et ses mats ;
   - les positions de la variante (de la position du curseur `game.fens[game.cursor]`
     jusqu'à `chess.fen()`, soit `chess.history({verbose:true})` à partir de l'indice
     `game.cursor`) sont évaluées par `POST /eval` comme en jeu libre (`evalLine` ne
     doit plus sortir dès qu'une partie est chargée : il évalue les positions de la
     variante absentes de `evals`) ;
   - elles sont tracées en cyan (`#00e5ff`) à partir du x du curseur (indice
     `game.cursor + k`), avec ombrage (même règle ≥ 10 pts) et repères de mat ;
   - échelle horizontale = `max(nombre de positions de la partie, cursor + positions de
     la variante)` ; le clic sur la courbe utilise la même échelle et va toujours à une
     position de la partie (borné par `goTo`) ;
   - trait vertical sur la dernière position de la variante.
   Hors variante et en jeu libre : inchangé.
2. **Ligne « joué »** (`#played`) :
   - numéro de coup devant le SAN, tiré du FEN de la position avant le coup (champ 6,
     trait) : « joué : 12. Nf6 » (blancs), « joué : 12… Nf6 » (noirs) ;
   - en variante : décrit le **dernier coup de la variante** (comme le jeu libre) ;
   - « — meilleur : Y » **n'apparaît que si la case « Meilleur coup » (`show-best`) est
     cochée** (retour de Nico). Décochée : « joué : 12. Nf6 (−Z pts) » ou
     « (meilleur coup) », sans nommer Y. Cocher / décocher met la ligne à jour aussitôt
     (le listener de `show-best` appelle aussi `refreshGame`, ou équivalent).
   - mat de la position affichée : inchangé.
3. **Lisibilité de la courbe** :
   - `GRAPH_H = 200` et `<svg id="graph" height="200">` (largeur 560 inchangée) ;
   - ombrage rouge (`#ff4040` ou proche) opacité 0,5, plus un trait pointillé horizontal
     au niveau « si meilleur coup » (win de la position avant) sur la largeur du coup ;
   - repère de mat : « #N » 14 px gras sur une pastille sombre (petit `rect` arrondi
     derrière le texte), en haut si mat des blancs, en bas si mat des noirs.
4. **Noms des joueurs** :
   - deux champs texte `id="name-white"` / `id="name-black"` (libellés « Blancs » /
     « Noirs »), près de « Je joue » ;
   - `loadGame` les remplit avec les en-têtes `White` / `Black` du PGN (`"?"` ou absent →
     vide) ; « Nouvelle partie » ne les touche pas ;
   - « Je joue » blancs → pseudo (`CHESS_USERNAME`) dans `name-white`, et `name-black`
     vidé s'il valait le pseudo (symétrique pour noirs) ; « aucun » ne touche pas aux
     champs ;
   - `exportPgn` : `White` / `Black` = valeur des champs (rognée), `"?"` si vide ; ces
     en-têtes restent toujours présents (`detect_pgn`) ; le pseudo n'est plus posé
     directement par « Je joue » dans `exportPgn` (il passe par les champs) ;
   - nom du fichier téléchargé : `Blancs-Noirs-AAAA.MM.JJ.pgn` (caractères hors
     `[A-Za-z0-9_-]` → `_`, nom vide → `inconnu`, date = celle de l'en-tête `Date`) ;
   - conservés au rechargement (`saveState` / `restoreState`, appliqués après
     `loadGame` comme les Elo) et sauvés à chaque modification.

## Tests

Étendre `test_index_serves_chessboard_page` : présence de `id="name-white"` et
`id="name-black"`. Pas d'outillage JS : le reste est vérifié au run live (vérification
VM possible sous node avec DOM simulé, comme au tronçon 03).

## Hors scope

- Aucun changement serveur (`board_interface.py`, `/eval`, `/game`, `/send`).
- Pas d'évaluation serveur des variantes en lot, pas de cache.
- Ne pas toucher l'analyse live, les flèches, les colonnes, la navigation.

## Critère de fin

`pytest tests/ -q` vert ; page chargeable sans erreur de syntaxe (module JS).
