# Sprint 63 — tronçon 01 : question de suivi avec moteur

## Objectif

Après une analyse de partie, une question de Nico qui **cite une position** (« position 2 »,
« coup 10 », « 10.Bb5+ », « Bb5+ ») ne part plus au LLM sans échiquier : ARIA rejoue la
partie jusqu'à cette position, la fait évaluer par Stockfish, envoie un diagramme et une ligne
écrite par le code, puis le LLM répond à la question **à partir des seuls faits de cette
position**.

Audit : `docs/sprint63/audit_suivi_moteur.md` (chemin actuel, ce qui est relisible en historique,
précédent sprint 59). Décisions : `00_etat.md` (1a, 2a, 3a).

## Fichiers (vérifiés au code, HEAD `9308221`)

- `cognition/cognitive_context.py` : enum `CognitiveOperation` (l. 21-25) → ajouter
  `CHESS_FOLLOWUP = "chess_followup"` ; à côté de `CHESS_POSITION_MARKER` (l. 40), une constante
  `CHESS_ANALYSIS_MARKER = "[Analyse Stockfish de la partie"` (texte déjà écrit par
  `chess_router._build_enriched`, l. ~1293 : la remplacer là par la constante, même texte).
- `cognition/cognitive_classifier.py` : nouvelle `detect_chess_followup(message, metadata, bridge)`
  sur le modèle de `detect_chess_board_move` (l. 236) ; nouvelle règle **1d** dans
  `classify_operation`, juste **après** la 1c (l. 413-414). En-tête de module (l. 9-10) : une ligne.
- `core/kernel.py` : table de routage (l. 70-71) → `CHESS_FOLLOWUP.value : "chess_router"`.
- `execution/routers/chess_router.py` : `ChessExecutionRouter.execute` (l. 1055) aiguille sur
  `payload["op_type"] == CHESS_FOLLOWUP` vers une nouvelle méthode `_execute_followup`.
- Tests : `tests/cognition/test_classifier_chess.py`, `tests/execution/test_chess_router.py`
  (fakes de bridge et de LLM déjà présents ; Stockfish réel avec
  `@pytest.mark.skipif(not STOCKFISH.exists(), …)` comme `tests/images/test_chess_image.py:52`).

## Comportement attendu

### Détection (classifieur, règle 1d)

`detect_chess_followup` vrai si **les deux** :
1. le message cite une position : « position N », « coup N » (insensible à la casse, accents
   tolérés), ou un coup SAN (`detect_san_move`, l. 230) ;
2. parmi les `config.max_history_turns * 2` derniers messages (lus par
   `bridge.load_conversation_history`), un tour `user` contient `CHESS_ANALYSIS_MARKER`.

Ordre : la 1c (`CHESS_BOARD_MOVE`, SAN après position lue en image) reste prioritaire. Le
classifieur ne lit l'historique que si la condition 1 est vraie (même économie que 1c).

### Router `_execute_followup`

1. **Partie** : dernier tour `user` de l'historique (même fenêtre) qui contient
   `CHESS_ANALYSIS_MARKER`. Le PGN est à la fin de ce tour (message original ajouté après les
   consignes, `chess_router.py:1506`) : prendre le texte à partir de la **première ligne qui
   matche `^\s*\[[A-Za-z]+ "`** (premier en-tête PGN ; les lignes `[Analyse …` / `[Consigne : …`
   n'ont pas de guillemet après un mot), puis `parse_pgn` (`chess_coach/analysis.py:150`).
   Couleur de Nico : `Nico joue les blancs|noirs` dans le même tour.
2. **Position citée** (premier cas qui s'applique) :
   - « position N » : dans le même tour, le bloc `Position N (…) — coup n :` suivi de
     `  joué <label>` (`chess_router.py:1314-1316`) → ce demi-coup ;
   - SAN numéroté (« 10.Bb5+ », « 10...Nf6 ») : coup n, camp donné par `.` / `...` ;
   - « coup N » : coup N de Nico ;
   - SAN seul : en remontant depuis la fin de la partie, la **première** position où c'est
     au tour de Nico **et** où ce SAN est légal (décision 3a).
   Le demi-coup visé définit la position **avant** le coup (`fen_before`) et le coup joué.
3. **Coup proposé** : si le message contient un SAN légal dans cette position et différent du
   coup joué, c'est le coup proposé (évalué en plus du coup joué).
4. **Moteur** : `chess_coach.board_reading.solve(fen)` (Stockfish 3 s, l. 131) sur la position
   avant le coup (meilleur coup + ligne), et sur la position après le coup joué, et après le
   coup proposé s'il existe. Mat : `score.is_mate()` → « mat en N » (N = `score.mate()`, vu du
   trait, converti en coups du camp concerné).
5. **Ligne écrite par le code** (en tête de la réponse, jamais réécrite par le LLM), ex. :
   `Coup 10 (blancs) : joué 10.Nxc7+ (+4,7) ; meilleur 10.Bb5+ c6 11.Nf6# (mat en 2) ;
   proposé 10.Bb5+ : mat en 2.` Réutiliser `_format_line` (l. 153). Évaluation en pions comme
   `image_router._solve_line` (l. 76), ou « mat en N ».
6. **Diagramme** : `render_position(fen_before, nico_color, best_uci, path, played_uci=…,
   best_line_uci=pv[:3])` (même appel que l. ~1170), dans `config.image_output_dir/chess`.
7. **LLM** : `self.llm_execution_router.execute` en `REASONING`, contenu = bloc de faits
   (pièces `_pieces_line`, `_material_line`, `_attacked_line`, `structure_line`, faits des lignes
   via `_move_facts` pour la ligne du meilleur coup, du coup joué et du coup proposé) + consigne
   courte + question de Nico. Consigne (intention) : réponds en 2-3 phrases à la question, à partir
   de ces faits uniquement ; n'invente aucun coup ; le mat n'existe que s'il est dans une ligne ;
   ne recopie pas la ligne du code. Le contenu **ne contient pas** `CHESS_ANALYSIS_MARKER`.
   Metadata : `{**metadata, "forced_intent_name": FORCED_INTENT_NAME, "skip_history": True}`
   (les faits suffisent ; l'échange reste écrit pour les suivis suivants).
8. **Retour** : `{"text": ligne_code + "\n" + texte_LLM, "images": [diagramme]}`.
9. **Position introuvable** (n hors partie, « position N » absente, SAN jamais légal) :
   `{"text": "Je ne trouve pas cette position dans la partie contre <adversaire>. Cite le coup, ex. « coup 10 »."}`
   sans moteur ni LLM. Log `chess_followup NOT_FOUND`.

Log `chess_followup OK move=<label> proposed=<san|-> mate=<N|->` à la réponse.

## Tests (cas nominal, Stockfish réel avec skipif)

PGN de référence (partie Modern du 2026-11-20, début réel) :
`[White "staroflexeur"] [Black "X"] 1.e4 g6 2.d4 Bg7 3.Nc3 d6 4.Bf4 Nf6 5.e5 dxe5 6.dxe5 Qxd1+
7.Rxd1 Nh5 8.Nd5 Kd7 9.e6+ fxe6 10.Nxc7+` (vérifier que `staroflexeur` est bien dans
`config.chess_usernames`, sinon prendre un pseudo qui y est). Historique factice : un tour
`user` = `CHESS_ANALYSIS_MARKER + " — Nico joue les blancs …]\nPosition 1 (erreur de Nico) — coup 10 :\n  joué 10.Nxc7+, …\n…\n\n" + PGN`.

1. Classifieur : « au coup 10 j'avais mat avec Bb5+ ? » + ce tour → `CHESS_FOLLOWUP` ;
   même message sans tour d'analyse → pas `CHESS_FOLLOWUP` ; « et si 1...e6 ? » avec le marqueur
   d'image dans le dernier tour → toujours `CHESS_BOARD_MOVE`.
2. Router : « au coup 10 j'avais mat avec Bb5+ ? » → texte qui commence par la ligne du code,
   contient `10.Bb5+` et `mat en 2`, une image ; le contenu envoyé au LLM factice contient la
   question et les faits, pas `CHESS_ANALYSIS_MARKER`.
3. Router : « position 1 » → même position (coup 10, joué `10.Nxc7+`).
4. Router : « coup 40 » → texte « Je ne trouve pas… », LLM non appelé.

`pytest tests/ -q` vert.

## Hors-scope (ne pas faire)

- Pas de balayage sans citation (« j'avais mat en 2 » seul → circuit actuel, décision 1b refusée).
- Ne pas toucher `_trim_history`, `HISTORY_MESSAGE_MAX_CHARS`, `ARIA_RULES`.
- Ne pas modifier `CHESS_BOARD_MOVE` / `image_router` (on ne fait que s'en inspirer ;
  ne pas factoriser `_solve_line`).
- Pas de nouvelle écriture mémoire, pas de lecture des fiches de parties.
- Pas de Maia, pas de `analyze()` complet sur la partie.
- Ne pas modifier le prompt AnalystAgent ni `soul.md`.

## Critère de fin

Tests ci-dessus verts, `pytest tests/ -q` vert, commit local
`feat(sprint63) tronçon 01: question de suivi avec moteur`.
