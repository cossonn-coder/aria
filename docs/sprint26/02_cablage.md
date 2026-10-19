# Sprint 26 — Tronçon 02 : câblage CHESS_ANALYSIS de bout en bout

Lire d'abord : `CLAUDE.md`, `docs/sprint26/00_etat.md`, puis le code de
`chess_coach/` livré au tronçon 01. Patron à imiter : `execution/routers/web_router.py`.

## Objectif

Un PGN collé dans Telegram → analyse moteur (tronçon 01) → ≤ 3 diagrammes PNG
+ une explication LLM fondée sur les faits moteur, envoyés à Nico.

## Fichiers à toucher (vérifiés au code)

### `cognition/cognitive_context.py`
- Ajouter `CHESS_ANALYSIS = "chess_analysis"` à `CognitiveOperation`.
- `MEMORY_TOP_K` / `LLM_ROLE_MAP` : rien à ajouter (le router délègue en REASONING).

### `cognition/cognitive_classifier.py`
- `detect_pgn(message: str) -> bool` : True si le message contient un en-tête
  `[White "` ou `[Black "` **et** un texte de coups commençant par `1.`
  (regex `\b1\.\s*\S`).
- Dans `classify_operation`, nouvelle règle **entre 1 (image) et 2 (URL)** :
  `if detect_pgn(message): return CognitiveOperation.CHESS_ANALYSIS`.
  Raison : l'export Chess.com contient `[Link "https://…"]`, sinon URL_READ.
- Mettre à jour le commentaire d'en-tête (liste des règles).

### `core/kernel.py`
- `_ROUTING_TABLE` : `CognitiveOperation.CHESS_ANALYSIS.value : "chess_router"`.
- `_build_dispatcher` : enregistrer `ChessExecutionRouter(llm_execution_router=llm_execution_router)`.
- `_normalize` : si `data` est un dict avec une clé `"images"` (liste non vide),
  retourner `{"type": "images_text", "images": data["images"], "text": data.get("text", "")}`.
  Placer ce test **avant** le test `path` existant. Ne pas toucher au `print()` (#71).

### `execution/routers/chess_router.py` (nouveau)
`ChessExecutionRouter(BaseRouter)`, `execute(payload)` :
1. `message = payload["content"]`, `metadata = payload["metadata"]`.
2. `analysis = chess_coach.analysis.analyze(message, message, config.chess_username, config.stockfish_path)`.
3. Si `None` (PGN illisible) : déléguer comme web_router avec
   `"[PGN illisible : dis-le à Nico en une phrase.]\n\n" + message`, retourner le résultat.
4. Pour chaque position critique `i` (1..k) : `render_position(fen_before, nico_color,
   best_uci, out_path)` avec `out_path = Path(config.image_output_dir) / "chess" /
   f"{uuid4().hex[:8]}_{i}.png"` (créer le dossier). Légende courte en notation
   française, ex. : `"Position 1 — coup 17 (noirs) : joué 17...Cg4+, meilleur 17...Fd7"`
   (pour kind "c" : `"Position 3 — coup 21 : 21...Fxe5, seul bon coup — bien joué"`).
5. Construire le message enrichi (en français, notation FR via `to_french`) :
   ```
   [Analyse Stockfish de la partie — Nico joue les <couleur> (<source>) :
   <en-têtes utiles : joueurs, Elo, date, ouverture/ECO si présents, résultat>
   Compteurs Nico : meilleurs N, corrects N, imprécisions N, erreurs N, gaffes N
   Position 1 (<sorte : erreur de Nico | occasion manquée après erreur adverse | coup unique trouvé>) — coup <n> :
     joué <coup>, perte <x> pts de % de gain (<win_before> % → <win_after> %)
     meilleur <coup>, ligne : <pv en FR>
     étiquettes : <tags>, phase : <phase>
   Position 2 …]
   [Consigne : explique à Nico, joueur d'environ <Elo> Elo, les IDÉES de chaque
   position (plans, menaces, pourquoi le meilleur coup est meilleur), dans l'ordre
   Position 1, 2, 3 — Nico voit les diagrammes du même numéro. Utilise uniquement
   les coups et lignes fournis ci-dessus ; n'invente aucun coup ni évaluation.
   Notation française (C, F, T, D, R). Termine par 1 à 3 axes de travail.]
   [Consigne si color_source == "default" : signale que tu as supposé les blancs
   faute de pseudo, et que Nico peut préciser « je joue les noirs ».]

   <message original>
   ```
6. `result = self.llm_execution_router.execute({"op_type": REASONING, "content":
   enriched, "metadata": metadata})` — **sans `skip_intent`** (décision Q4 :
   la partie doit aller en mémoire épisodique via l'intent).
7. Retourner `{"text": result["text"], "images": [{"path", "caption"}, …]}`.

Le router n'écrit **rien** en mémoire à ce tronçon (règle 1 ; la fiche arrive au 03).
Log : `log.info("chess_router OK critical=%d images=%d", …)`.

### `interfaces/telegram_interface.py` — `send()`
Nouveau cas en tête : `message.get("type") == "images_text"` → pour chaque image
`send_photo` (même helper `_send_with_retry`, fichier rouvert à chaque tentative,
légende ≤ 1024), puis le texte par le chemin texte existant (découpe 4096).
Image introuvable → l'ignorer avec `log.warning` et continuer.

### `CLAUDE.md` — règle inviolable 4
Remplacer par :
« 4. Les routers retournent {"text": str}, {"path": str, "caption": str} ou
{"text": str, "images": [{"path": str, "caption": str}, …]} — jamais
{"status": ...} (c'est le rôle du dispatcher). »

## Tests à ajouter (cas nominal)

- `tests/cognition/` : `detect_pgn` vrai sur un PGN Chess.com avec `[Link "https://…"]`
  et `classify_operation` → CHESS_ANALYSIS ; faux sur « après 1.e4 e5 2.Cf3 quelles idées ? ».
- `tests/execution/test_chess_router.py` : `analyze` et `render_position`
  monkeypatchés (pas de Stockfish), fake `llm_execution_router` → le résultat
  contient `text` + `images` (k éléments), le payload délégué est REASONING
  **sans** `skip_intent`, et le message enrichi contient « Position 1 ».
- `_normalize` : un `data` avec `images` → `type == "images_text"`.
- `tests/interfaces/test_telegram_interface.py` : `images_text` → N `send_photo`
  puis `send_message` (suivre les fakes existants du fichier).

## Hors scope (ne PAS faire)

- Pas de fiche mémoire / `write_chess_game` (tronçon 03).
- Pas de `send_media_group`, pas de réordonnancement des envois.
- Pas de relance moteur sur un coup cité en texte (dette #80).
- Ne pas corriger le `print()` de `_normalize` (#71) ni la découpe 4096 (#66).
- Ne pas toucher au prompt AnalystAgent.

## Critère de fin

- `pytest tests/ -q` vert.
- Sandbox : un appel direct `ChessExecutionRouter.execute` avec le vrai Stockfish
  et un faux LLM produit 1 à 3 PNG existants et un message enrichi lisible
  (montrer un extrait dans le rapport).
