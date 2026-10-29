# Sprint 39 — tronçon 10 : précision du coup et précision totale de chaque joueur

Serveur de page + page : `interfaces/board_interface.py`, `interfaces/board/index.html`,
tests dans `tests/interfaces/test_board_interface.py`. Arbitrages lot 6 (Nico, 2026-10-29)
dans `00_etat.md`.

## État du code (audit 2026-10-29)

- Formule Lichess déjà en place pour le bilan Telegram : `chess_coach/summary.py`,
  `_move_accuracy(loss)` (précision d'un coup) et `_game_accuracy(plies, color)` (précision
  de la partie : fenêtres glissantes + moyenne pondérée / harmonique) ; perte effective
  ramenée à 0 si `quality == "best"` (`_effective_loss`). `_game_accuracy` lit sur chaque
  ply `color`, `win_before` / `win_after` (point de vue du joueur au trait), `loss`, `quality`.
- `analysis.py:244` : `loss = max(0, win_before - win_after)` (point de vue du joueur qui joue).
- Page : `evals` = Map FEN → `{win, mate, best}`, `win` = % de gain **des blancs** ;
  remplie par `/game` (partie chargée) et `/eval` (jeu libre, variante).
- `playedText()` (l. ~498) : coup décrit = `game.sans[game.cursor]` en partie chargée hors
  variante, sinon dernier coup joué ; positions `fens[i]` → `fens[i + 1]`.
- `do_POST` (l. ~195) : routes `/position`, `/game`, `/eval`, `/send`.
- `board_interface.py` importe déjà un privé de `analysis` (`_win`).

## Comportement attendu

### Serveur

1. Fonction `line_accuracy(wins, best, first)` dans `board_interface.py` :
   - `wins` : N+1 % de gain des blancs (positions de la ligne), `best` : N booléens (coup
     joué = meilleur coup), `first` : `"white"` / `"black"` (camp du premier coup).
   - Construit N plies (couleurs alternées depuis `first`, `win_before` / `win_after` au
     point de vue du joueur, `loss = max(0, win_before - win_after)`, `quality = "best"` si
     `best[i]`, sinon autre chose) et réutilise `_move_accuracy(_effective_loss(p))` et
     `_game_accuracy(plies[:k + 1], color)` de `summary.py` (pas de seconde formule).
   - Rend `{"moves": [précision du coup k], "white": [précision totale des blancs après le
     coup k ou None], "black": [idem noirs]}`, arrondis comme `_game_accuracy` (1 décimale).
2. Route `POST /accuracy {wins, best, first}` → JSON ci-dessus (ajoutée à la liste de
   `do_POST`), pas de Stockfish, réponse immédiate.

### Page

3. Ligne de calcul :
   - partie chargée hors variante : `game.fens` ;
   - variante : `game.fens` jusqu'au curseur (exclu) + `variantFens()` ;
   - jeu libre : `curve().fens`.
   On n'envoie que le plus long préfixe de positions déjà évaluées (`evals`) ; `best[i]` =
   SAN du coup i égal à `evals.get(fens[i]).best` ; `first` tiré du trait du FEN de départ.
   Réponse gardée par ligne envoyée (pas de requête refaite pour la même ligne).
4. Affichage sous l'échiquier :
   - sur la ligne `#played`, après le reste : ` — précision 74 %` (précision du coup décrit
     par « joué : … »), si connue ;
   - nouvelle ligne juste sous `#played` : `Précision : blancs 88 % · noirs 81 %` = précision
     totale de chaque joueur sur les coups de la ligne **jusqu'au coup décrit par « joué »
     compris** ; s'il n'y a pas de coup décrit (curseur en fin de partie), sur tous les coups
     évalués ; un camp sans coup → `—` ; rien si aucune réponse encore.
   - Arrondi à l'entier à l'affichage.
5. Positions pas encore évaluées : la précision apparaît quand les `/eval` arrivent
   (`refreshGame` déjà rappelé à chaque réponse).

## Tests

- `line_accuracy` sur une petite série : un meilleur coup → 100 ; une perte → précision
  < 100 ; totaux par camp présents, `None` pour un camp sans coup.
- Route `/accuracy` servie (même style que les tests de route existants).
- Page : présence de l'élément de la ligne de précision. Logique de page vérifiable sous
  node (DOM simulé), sans test permanent exigé.

## Hors scope

- Bilan Telegram et `summary.py` inchangés (aucune modification de la formule).
- Précision dans la liste des coups ou dans l'export PGN.
- `/game` et `/eval` inchangés.

## Critère de fin

`./venv/bin/pytest tests/ -q` vert ; `00_etat.md` tronçon 10 ✅.
