# Sprint 50, tronçon 01 — flèches et corrections

## Objectif
Sur les miniatures, la flèche d'une erreur jouée dit sa gravité et le piège est en cyan avec sa ligne écrite par le code. Deux faits faux disparaissent de la chaîne. À l'échiquier, la stratégie passe en blanc.

## À faire

### 1. Variante jusqu'au mat (`chess_coach/analysis.py::clear_advantage`)
Quand `mate` est vrai, ne pas s'arrêter sur un critère matériel/développement/activité/écrasant : la ligne continue jusqu'au mat ou à sa dernière entrée, comme l'annonce le commentaire existant. Défaut constaté : `(n=2, "development")` renvoyé avant 21.Qxd8#.

### 2. « roqué » → « à l'aile » (`chess_coach/structure.py::_king_text`)
Le FEN n'a pas l'historique : seul « à l'aile » est affirmable. Mettre à jour la docstring et `tests/chess_coach/test_structure.py`. Le tag `castle` (« roque » de `_TAG_FR`) vient du vrai coup : n'y pas toucher.

### 3. Dégradé d'erreur (`chess_coach/render.py`)
- Fonction pure : perte en pts → couleur RGBA, interpolation linéaire, 10 pts (255, 190, 205), 25 pts (215, 20, 35), 50 pts et plus (0, 0, 0), opacité 235. Sous 10 : couleur de 10.
- `render_position` reçoit la couleur de la flèche jouée et celle de la flèche `alt_uci` en paramètres facultatifs ; par défaut, `PLAYED_ARROW` et `ALT_ARROW` : les appelants existants ne changent pas.
- Ajouter `TRAP_ARROW` cyan (0, 229, 255, 190), teinte de l'échiquier.

### 4. Piège (`chess_coach/live.py`, `execution/routers/chess_router.py`)
- Dans `live.py`, fonction pure réutilisant `_TRAP_GAIN` et `_TRAP_P_MIN` : à partir des réponses d'un explosif (`p`, `win`) et de `win_best`, rendre les réponses piégeantes si leur somme de `p` atteint `_TRAP_P_MIN`, sinon liste vide. Sur une partie envoyée, `win_best` = `p.win_before` du coup analysé.
- Dans `_execute_game` : sortes a et b, flèche jouée au dégradé selon `p.loss` ; sorte d piégeante, `alt_uci` en cyan ; autres explosifs inchangés (orange).
- Légende (`_variant_line`) d'une sorte d piégeante : ajouter, après la variante, une ligne écrite par le code à partir de la réponse piégeante la plus probable :
  `Piège : 20.Bd8!? Si 20...Bxd8 (36 %), 21.Qxd8#. Sinon, pas de mat.`
  Le « Sinon, pas de mat. » n'apparaît que si la ligne de cette réponse finit par `#` et qu'aucune autre réponse connue n'en contient. Sans mat : « Si X (p %), suite, N % pour toi. »
- `_build_enriched` : pour une position d piégeante, ne plus donner `_explosive_lines` au LLM et lui dire de n'écrire que le plan, sans parler du piège ni de mat. Les explosifs non piégeants gardent le comportement actuel.

### 5. Échiquier (`interfaces/board/index.html`)
Stratégie en blanc au lieu de `#ff5fb0` : pastilles (lignes 113 et 151), appel ligne 276, commentaires lignes 270 et 472. Remplacer le pinceau `pink` (ligne 220) par un pinceau `strategy`, `color: "#ffffff"`, `lineWidth: 10`, touche `"s"` si elle est libre. Ne pas réutiliser `white` (ligne 223, `lineWidth: 6`) : il dessine le cercle du coup joué (ligne 285), qui ne change pas. Adapter `tests/interfaces/test_board_interface.py` si besoin.

## Tests (cas nominal)
- `clear_advantage` : position avant 20.Bd8 de la partie ci-dessous, ligne Bd8, Bxd8, Qxd8, `mate=True` → `(3, "mate")`.
  `1. e4 c5 2. Nf3 d6 3. b4 cxb4 4. a3 bxa3 5. Nxa3 Nf6 6. Bb5+ Nc6 7. d4 a6 8. Bxc6+ bxc6 9. e5 Ng4 10. h3 Nh6 11. Nc4 dxe5 12. O-O exd4 13. Bd2 e6 14. Ba5 Qf6 15. Nxd4 Bc5 16. Nb3 Be7 17. Nd6+ Kf8 18. Nc5 Nf5 19. Nde4 Qg6`
- Dégradé : 10, 25 et 60 pts donnent les trois couleurs de référence.
- Piège : réponses au-dessus et sous les seuils.
- Légende : ligne « Piège » avec et sans mat.
- `pytest tests/ -q` vert.

## Hors scope
- Calculer piège ou stratégie sur toute la partie (#157).
- Flèches des erreurs adverses, dégradé à l'échiquier.
- Bilan, consigne « Niveau », recherche web : tronçon 02.

## Critère de fin
Tests verts. Rendu d'une position d'erreur et d'une position piège contrôlé en image, en précisant le résultat dans le rapport.
