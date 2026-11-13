# Sprint 59 — tronçon 06 : relance « et si X ? » sur une position lue en image

## Objectif

Après une position résolue depuis une image, un message texte qui propose un coup
(« et si 1...Qe7+ ? ») joue ce coup sur la position, le fait évaluer par Stockfish, puis
répond sous la même forme que pour l'image : texte + diagramme, **sans LLM**.

Décisions de Nico :
- **Enchaînement** : chaque relance part de la position atteinte après le coup précédent.
  La nouvelle position est réécrite dans l'historique avec le même marqueur.
- **Notation** : anglaise seule (SAN : `Qe7+`, `Nf3`, `exd5`, `O-O`, `e8=Q`), avec ou
  sans numéro (`1...Qe7+`, `12.Nf3`).
- **Réponse** : la ligne Stockfish après le coup et l'évaluation, comparées au meilleur coup
  de la position de départ, avec le diagramme.

Audit : `docs/sprint59/audit_position_image.md`, §Audit 2, C.

## Contexte vérifié

- Marqueur posé par `ImageExecutionRouter._handle_chess_board`
  (`execution/routers/image_router.py:299-309`) dans le tour `user` de l'historique :
  `[Position d'échecs lue sur image : <FEN>]`, suivi éventuellement de la légende. Il n'est
  écrit que si la position est résolue.
- Précédent d'une règle de classifieur qui lit l'historique : `detect_url_resume`
  (`cognition/cognitive_classifier.py:198`), qui appelle
  `bridge.load_conversation_history(str(metadata.get("chat_id", "default")), n=2)` et
  cherche un marqueur dans le dernier tour `user`.
- Ordre des règles : `classify_operation` (`cognitive_classifier.py:348`). La règle 1b
  (PGN) est à la ligne 375.
- Enum des opérations : `cognition/cognitive_context.py` (`CognitiveOperation`). Table
  opération → router : `core/kernel.py:54` (`_ROUTING_TABLE`).
- `ImageExecutionRouter.execute` (`image_router.py:91`) aiguille selon `op_type`. Le router
  reçoit déjà `mempalace_bridge` (`self.mempalace_bridge`, inutilisé depuis le sprint 24).
  La lecture de l'historique par un router via le bridge a un précédent :
  `web_router.py:189`.
- Résolution réutilisable : `image_router.py:271-311` (`solve(fen)` → score + ligne,
  texte, `render_position`, écriture de l'historique). `solve` est dans
  `chess_coach/board_reading.py:131`. `_format_line` est importé de `chess_router`.

## À faire

1. `CognitiveOperation` : nouvelle valeur (ex. `CHESS_BOARD_MOVE = "chess_board_move"`),
   routée vers `"image_router"` dans `_ROUTING_TABLE`.
2. Classifieur : nouvelle règle **1c**, juste après le PGN, avec une fonction de détection
   sur le modèle de `detect_url_resume`. Elle est vraie si le message contient un coup SAN
   (regex) **et** si le dernier tour `user` de l'historique contient le marqueur. La
   lecture de l'historique ne se fait que si la regex matche. Sans bridge → faux.
3. `ImageExecutionRouter` : nouvelle branche pour cette opération.
   - Relire la FEN du marqueur (dernier tour `user`, via `self.mempalace_bridge`).
   - Interpréter le coup en SAN sur cette position (python-chess). Coup illégal ou
     introuvable → `{"text": "Le coup X n'est pas jouable dans la position : <FEN>"}`
     (forme libre), sans écrire l'historique.
   - Sinon : `solve` sur la position de départ (meilleur coup + éval), puis le coup est joué
     et `solve` est relancé sur la position obtenue (ligne + éval).
   - Texte, même forme que `_handle_chess_board` : « Après <coup> : trait aux <camp>. »,
     position, ligne principale, évaluation, et une ligne de comparaison au meilleur coup
     de départ (si le coup proposé **est** le meilleur, le dire).
   - Diagramme de la position après le coup, avec les flèches de la ligne. Orientation :
     le camp qui a joué le coup en bas.
   - Historique : réécrire le marqueur avec la **nouvelle** FEN (tour `user`, suivi du
     message), puis la réponse (tour `assistant`), comme à `image_router.py:299-309`.
   - Factoriser avec `_handle_chess_board` la partie commune « FEN → ligne, éval, texte,
     diagramme, historique » si cela évite de dupliquer : c'est permis dans ce tronçon,
     sans changer le comportement de l'image.

## Tests (cas nominal)

- Classifieur : avec un bridge factice dont le dernier tour `user` porte le marqueur,
  « et si 1...Qe7+ ? » → la nouvelle opération. Sans marqueur → pas la nouvelle opération.
- Router (Stockfish disponible, comme les tests existants de `tests/images/test_chess_image.py`) :
  bridge factice avec marqueur ; un coup légal → texte « Après … » + 1 image ; le marqueur
  réécrit dans l'historique porte la FEN d'après le coup. Un coup illégal → texte sans image.

## Hors scope

- Notation française, plusieurs coups dans un même message (seul le premier coup reconnu
  est joué), retour à la position de l'image.
- Aucun LLM dans la réponse. Pas de changement du chemin image (sauf factorisation neutre).
- Aucune écriture mémoire hors `write_conversation_turn` (`memory/writer.py`).

## Critère de fin

`pytest tests/ -q` vert, nouveaux tests compris.
