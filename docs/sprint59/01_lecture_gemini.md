# Sprint 59 — tronçon 01 : lecture Gemini → grille → FEN

## Objectif

Deux briques indépendantes, sans branchement dans le pipeline (c'est le tronçon 03) :

1. **Lire une grille** : `ImageRouter.read_board(image)` (dans `llm/image_router.py`)
   envoie l'image à Gemini et retourne 8 chaînes de 8 caractères **telles qu'affichées**
   (rangée du haut d'abord, chaque rangée de gauche à droite ; `KQRBNP` blancs,
   `kqrbnp` noirs, `.` vide), ou `None` si aucun modèle Gemini n'a rendu une grille valide.
2. **Grille → FEN** : nouveau module `chess_coach/board_reading.py`, fonctions pures.

## Contexte vérifié (audit `docs/sprint59/audit_position_image.md`)

- La chaîne vision prod (deepseek-flash, qwen) lit faux : ne pas l'utiliser pour la grille.
- `gemini-3.5-flash` : 3 lectures justes sur 3 [n=3, une seule image], ~10 s par appel.
  `gemini-3.8-flash` : juste, mais souvent en 503. `gemini-2.5-*` : 404 (retirés).
- Appel **natif** mesuré OK :
  `POST https://generativelanguage.googleapis.com/v1beta/models/<modèle>:generateContent`,
  `params={"key": config.gemini_api_key}`, corps
  `{"contents": [{"parts": [{"text": consigne}, {"inline_data": {"mime_type": "image/jpeg", "data": <base64>}}]}]}`,
  réponse dans `candidates[0].content.parts[-1].text`. Timeout ≥ 90 s.
  Le point d'accès OpenAI-compatible (`…/v1beta/openai/chat/completions`) a dépassé les
  30 s de `GroqVisionClient` une fois [n=1] : ne pas compter dessus.
- Consigne mesurée (à reprendre telle quelle ou presque) : « Cette image montre un
  échiquier. Lis les 8 rangées TELLES QU'AFFICHÉES, de la rangée du haut à celle du bas,
  chaque rangée de gauche à droite. Pour chaque case : lettre de pièce (K Q R B N P pour
  les pièces blanches, k q r b n p pour les noires) ou '.' si vide. Réponds UNIQUEMENT par
  8 lignes de 8 caractères. » La réponse peut arriver entourée de ``` : à nettoyer.
- `ImageRouter._dispatch` (l. 225) instancie `entry["client"](base_url=, model=, models=,
  api_key=, output_dir=, extra=)` puis appelle la méthode demandée ; exception → entrée
  suivante. `GroqVisionClient.__init__` accepte `**_`.

## À faire

- `llm/vision/gemini_vision.py` : petit client `GeminiVisionClient` à l'interface de
  `GroqVisionClient` (`describe(image, prompt) -> str`, chemin local → base64), appel natif.
- `llm/image_router.py` : une table `BOARD_ROUTING_TABLE` (gemini-3.5-flash, puis
  gemini-3.8-flash), et `read_board(image) -> list[str] | None`. Une réponse qui n'est pas
  une grille 8×8 de caractères valides compte comme un échec : on passe au modèle suivant.
  Tout échoue → `None` (pas d'exception : le tronçon 03 bascule alors sur le lecteur local).
- `chess_coach/board_reading.py` :
  - `side_from_caption(caption) -> "white" | "black" | None` : « blanc(s) » seul → white,
    « noir(s) » seul → black, sinon None (insensible à la casse, mots entiers).
  - `grid_to_fen(rows, caption) -> tuple[str, str]` : retourne `(fen, bottom)` où `bottom`
    est la couleur du camp affiché en bas (`"white"`/`"black"`, c'est l'`orientation` de
    `render_position`).
    - Camp en bas : pions blancs plus bas à l'écran (indice de rangée moyen plus grand) que
      les pions noirs → blancs en bas. Pas de pions d'un des deux côtés : comparer les rois.
      Indécidable : le camp au trait s'il est donné, sinon blancs.
    - Blancs en bas : rangée affichée 0 = rang 8, colonnes a→h. Noirs en bas : rangée
      affichée 0 = rang 1, colonnes h→a.
    - Trait : `side_from_caption(caption)`, sinon le camp du bas (règle de Nico).
    - Roques : droit posé si roi et tour sont sur leurs cases d'origine (e1/h1 → K, e1/a1 → Q,
      idem e8/h8, e8/a8). Pas de prise en passant ; compteurs `0 1`.
  - `position_problem(fen) -> str | None` : `None` si `chess.Board(fen).is_valid()`, sinon une
    raison courte en français tirée de `board.status()` (ex. « deux rois blancs »,
    « pas de roi noir », « pion sur la première ou la dernière rangée », « le camp qui n'a pas
    le trait est en échec »). Une raison générique suffit pour les autres drapeaux.

## Tests (cas nominal, sans réseau)

`tests/chess_coach/test_board_reading.py` :
- La grille de `docs/sprint59/ref/chesscom_vert.txt` + légende « trait aux noirs » →
  `("r1bqkb1r/pp3ppp/2n2n2/2pp4/2B5/2NP1N2/PPP2PPP/R1BQK2R b KQkq - 0 1", "black")`.
- Même grille sans légende → même résultat (noirs en bas, donc trait aux noirs).
- Une grille avec deux rois blancs → `position_problem` non `None`.

`tests/images/` : `read_board` avec une table de deux faux clients, le premier rend du
texte non conforme, le second une grille entourée de ``` → la grille nettoyée.

## Hors scope

- Aucun branchement dans `ImageExecutionRouter`, aucun Stockfish, aucune écriture mémoire.
- Ne pas toucher `VISION_ROUTING_TABLE` ni `handle_input`.
- Pas de lecture de FEN tapée en texte.

## Critère de fin

`pytest tests/ -q` vert ; `read_board` et `grid_to_fen` livrés et testés comme ci-dessus.
