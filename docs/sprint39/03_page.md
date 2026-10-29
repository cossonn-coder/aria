# Sprint 39 — tronçon 03 : page (écart ombré, mats, jeu libre, export, envoi)

Lire d'abord `CLAUDE.md`, `00_etat.md` (décisions lots 1-3) et `audit_courbe_pgn.md` §1
(structure de la page). Tronçons 01 et 02 faits : `/game` rend `wins`, `mates`, `best` ;
`POST /eval {fen}` → `{win, mate, best}` ; `POST /send {pgn}` → 200 / 503 ; `GET /`
remplace `__CHESS_USERNAME__` par le pseudo d'échecs de Nico.

## Fichiers

- `interfaces/board/index.html` (seul fichier de prod).
- `tests/interfaces/test_board_interface.py` : présence des nouveaux contrôles.

Conventions de la page : `$`, `chess` (chess.js 1.4.0), `ground`, `game`
(`{start, sans, played, cursor, wins, message}`), `variant`, `goTo`, `refreshGame`,
`drawGraph` (SVG inline, `GRAPH_W` × `GRAPH_H`), commentaires en français.

## Comportement attendu

1. **Valeurs par position** : une Map FEN → `{win, mate, best}` (% blancs, mat signé
   côté blancs, SAN du meilleur coup). Partie chargée : remplie depuis la réponse de
   `/game` (position i = FEN après i demi-coups de `game.sans` depuis `game.start`).
   Jeu libre : à chaque nouvelle position absente de la Map, `POST /eval` (réponse
   rangée par FEN, ordre d'arrivée indifférent, puis courbe redessinée). Vidée par
   « Nouvelle partie » et au chargement d'un PGN.
2. **Courbe toujours visible** (#129) :
   - partie chargée : positions de la partie, comme aujourd'hui ; en variante, la
     courbe reste celle de la partie (trait vertical sur le curseur) ;
   - jeu libre : positions de la ligne de l'échiquier (départ → position affichée),
     trait vertical sur la dernière ; points encore inconnus = courbe tracée jusqu'au
     dernier point connu.
   - clic sur la courbe : inchangé pour une partie chargée ; sans effet en jeu libre.
3. **Écart ombré** (#127) : pour chaque coup i → i+1 dont la perte du camp qui joue
   ≥ 10 pts (perte = win[i] − win[i+1] côté blancs, inversée pour les noirs), zone
   ombrée (une couleur translucide) entre le niveau « si meilleur coup » (win[i],
   valeur de la position avant le coup) et le segment de courbe du coup joué.
4. **Ligne sous l'échiquier** (`#played`) :
   - partie chargée hors variante : « joué : X — meilleur : Y (−Z pts) » pour le coup
     joué **depuis** la position affichée (X = coup de la partie, Y = best de la
     position, Z = perte arrondie) ; « (meilleur coup) » à la place de la parenthèse si
     X = Y ou perte < 1 ; « joué : X » seul tant que les valeurs manquent. Cercle blanc
     inchangé.
   - jeu libre : même format pour le **dernier coup joué** (celui qui mène à la position
     affichée), puisqu'il n'y a pas de coup suivant.
   - dans les deux cas, si la position affichée a un mat : « mat en N pour les
     blancs / noirs » sur la ligne (ou seule).
5. **Repères de mat** (#128) : pour chaque position à mat non nul, un petit repère
   « #N » en haut de la courbe (mat des blancs) ou en bas (mat des noirs), à son x.
6. **« Je joue »** : sélecteur blancs / noirs / aucun (défaut aucun).
7. **Export PGN** (bouton « Exporter PGN ») : copie dans le presse-papier **et**
   téléchargement d'un `.pgn` (Blob + lien). Contenu :
   - coups : partie chargée hors variante → **toute** la partie (`game.sans`) ; sinon
     la ligne de l'échiquier (`chess.history()`) ; départ `game.start` / position
     initiale ;
   - en-têtes : partie chargée hors variante → ceux du PGN chargé (les garder au
     chargement) ; sinon `Event "Échiquier ARIA"`. Puis, toujours : `Date` du jour
     (`AAAA.MM.JJ`), `WhiteElo` / `BlackElo` depuis les champs, et « Je joue » blancs /
     noirs → `White` / `Black` = `"__CHESS_USERNAME__"` (remplacé par le serveur). Les
     en-têtes `White` et `Black` sont **toujours présents** (`"?"` à défaut) : le
     classifier d'ARIA (`detect_pgn`) les exige. `Result` : celui du PGN chargé, sinon
     1-0 / 0-1 / 1/2-1/2 si la partie est finie sur l'échiquier, sinon `*`.
   - Construire sur un `new Chess(start)` rejoué, `setHeader`, `pgn()`.
8. **Envoyer à ARIA** (bouton) : `POST /send` avec le PGN de l'export ; état
   « envoyée à ARIA, réponse sur Telegram » (200) ou « ARIA pas prêt » (503) dans
   `#status` ou à côté du bouton. Permis même avec « Je joue : aucun » (lot 3).
9. **Conservation au rechargement** (`localStorage`, une clé) : texte PGN chargé (ou
   rien), curseur, ligne libre (coups SAN depuis le départ), Elo, « Je joue ». Au
   chargement de la page : partie chargée → rechargée (courbe redemandée) et curseur
   rétabli (une variante en cours est perdue, accepté) ; sinon ligne libre rejouée.
   « Nouvelle partie » efface l'état sauvé. Écriture à chaque changement de position.

Inchangés : analyse live (flèches, colonnes, bleu rationné), navigation, variante.

## Tests

Étendre `test_index_serves_chessboard_page` : présence des boutons d'export et d'envoi
et du sélecteur « Je joue » (ids au choix, ex. `export`, `send`, `playing`), et du
pseudo `config.chess_username` dans la page servie (le marqueur est remplacé). Pas
d'outillage JS : le reste est vérifié au run live.

## Hors scope

- Pas de changement serveur (tronçons 01-02), pas d'analyse des positions de variante
  pour la courbe, pas de liste des coups affichée.
- Ne pas toucher l'analyse live ni les colonnes.

## Critère de fin

`pytest tests/ -q` vert ; page chargeable sans erreur de syntaxe (module JS).
