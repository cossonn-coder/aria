# Sprint 63 — audit : question de suivi sans moteur (dettes 61-1 + 62-2)

Date : 2026-11-20. HEAD `9308221`. Code lu : `cognition/cognitive_classifier.py`,
`execution/routers/llm_router.py`, `execution/routers/chess_router.py`,
`execution/routers/image_router.py` (relance sprint 59), `core/kernel.py`,
`chess_coach/board_reading.py` (`solve`), `chess_coach/analysis.py` (`missed_mate`),
`chess_coach/summary.py` (`plies_json`), `memory/mempalace_bridge.py` (`load_conversation_history`).

## 1. Cas réels

- **61-1** (sprint 61) : après l'analyse, « cette tactique… je veux trouver ce schéma » →
  ARIA répond « pièce clouée + échec disponible = prise gratuite » (schéma faux).
- **62-2** (sprint 62, partie Modern du 2026-11-20) : « j'avais mat en 2 » →
  « 9...Qh4+ 10.g3 Qxg3# » : mauvais camp, dame noire déjà échangée au coup 6.
  Le vrai mat : 10.Bb5+ c6 11.Nf6#.

## 2. Chemin actuel d'une question de suivi

1. `classify_operation` (`cognitive_classifier.py:385`) : pas de PGN (`detect_pgn` exige un
   en-tête `[White "`), pas d'image → règles suivantes → en pratique REASONING (ou autre op texte).
   Aucune règle ne connaît « question sur la dernière partie analysée ».
2. Kernel → `llm_router` (`core/kernel.py:55-70`). Aucun moteur.
3. `LLMExecutionRouter._run_pipeline` (`llm_router.py:198`) :
   - historique chargé via le bridge (`max_history_turns=10` → 20 messages), puis
     `_trim_history` : **chaque message coupé à 1 500 car.**, total 6 000 (`llm_router.py:54-55, 120`) ;
   - le tour `user` de l'analyse est le **message enrichi entier** (écrit par
     `write_conversation_turn(..., "user", message)`, `llm_router.py:404`) : ancre, en-têtes,
     compteurs, niveau, déroulé… Les blocs « Position N » arrivent bien après 1 500 car. → coupés ;
   - le tour `assistant` est le texte LLM (Pourquoi), lui aussi coupé à 1 500 car. ;
   - `ARIA_RULES` (`llm_router.py:61`) interdit déjà de calculer une variante sans moteur.
     Le LLM l'a ignorée en 62-2. **Une consigne ne suffit pas** : il faut lui donner la position.
   - si le message parle de parties (`mentions_chess_games`), les fiches résumées sont ajoutées
     (`games_context_section`) : statistiques, pas de position.

Conséquence : le LLM n'a ni échiquier, ni moteur, ni les faits de la position citée.

## 3. Ce qui existe déjà et peut servir

- **Le PGN complet est en historique, intact.** Le message enrichi se termine par
  `\n\n{message}` (`chess_router.py:1506`) = le PGN collé. La coupe à 1 500 car. n'a lieu qu'au
  chargement dans `llm_router` ; `load_conversation_history` rend le texte entier.
  → Un router de suivi peut relire le PGN par le bridge (règle 2), sans toucher aux fiches.
- **La numérotation « Position N » est en historique.** Le même tour porte
  `Position {i} (…) — coup {n} :` puis `  joué 10.Nxc7+, …` (`chess_router.py:1314-1316`).
  → « position 2 » se traduit en coup joué par simple lecture du tour.
- **Précédent sprint 59** : `CHESS_BOARD_MOVE` (relance « et si X ? » sur position lue en image).
  Détection = coup SAN dans le message + marqueur dans le dernier tour `user`
  (`detect_chess_board_move`, `cognitive_classifier.py:236`) ; router = FEN relue de
  l'historique, `solve` (Stockfish 3 s, `board_reading.py:131`), diagramme, texte écrit
  par le code, sans LLM (`image_router.py:342`). Même schéma de bout en bout.
- **Faits de position** réutilisables dans `chess_router.py` : `_move_facts`, `_pieces_line`,
  `_material_line`, `_attacked_line`, `structure_line`, `_format_line`, `_evaluation`.
- `missed_mate` (`analysis.py:213`) et `mate_line` (`analysis.py:662`) : mat ≤ 7 détecté et suivi.
- `detect_san_move` (`cognitive_classifier.py:230`) : premier coup SAN du message.

## 4. Écarts / limites constatés

- **E1 — repérage de la position.** Une question peut citer : « position 2 », « coup 10 »,
  « 10.Bb5+ », un SAN seul (« Bb5+ »), ou rien (« j'avais mat en 2 », « cette tactique »).
  Sans citation, il faut deviner : soit la dernière position commentée, soit un balayage.
- **E2 — coup proposé ≠ coup joué.** « j'avais mat avec Bb5+ » : Bb5+ n'a pas été joué. Il faut
  trouver la position où il est légal (au coup cité, sinon parmi les positions de Nico) et
  l'évaluer, comme la relance sprint 59.
- **E3 — portée de la recherche.** `detect_chess_board_move` ne regarde que le dernier tour
  `user`. Une question de suivi vient souvent 2-3 échanges après l'analyse : il faut remonter
  la fenêtre d'historique (≤ 20 messages déjà chargés par llm_router).
- **E4 — 62-2 aujourd'hui.** Depuis le sprint 62, ce mat raté serait une position commentée
  (« mat en 2 manqué »). Le cas reste instructif : sans citation, le suivi n'a aucun moyen de
  vérifier la revendication de Nico.
- **E5 — conflit avec CHESS_BOARD_MOVE.** Un SAN après une position lue en image doit rester
  CHESS_BOARD_MOVE (marqueur dans le dernier tour). Ordre des règles à tenir.

## 5. Règles d'architecture

- Lecture de l'historique par `mempalace_bridge.load_conversation_history` (règle 2) : OK.
- Écriture de l'échange : par `LLMExecutionRouter` si la réponse passe par le LLM, ou
  `write_conversation_turn` (`memory/writer.py`) comme le sprint 59 (règle 1) : OK.
- Router : retourne `{"text", "images"}`, jamais `status` (règle 4).
- Kernel : une entrée dans la table de routage, rien d'autre (règle 5).
- Classifieur : nouvelle règle heuristique, même forme que 1c (lecture d'historique via bridge
  déjà injecté).
- Palace prod : **lu seulement** (historique), aucune nouvelle écriture structurelle.

## 6. Coût

Stockfish `solve` 3 s par position évaluée (1 à 2 positions par question). Pas de Maia,
pas de Gemini. Un appel LLM si la réponse est rédigée par le LLM.
