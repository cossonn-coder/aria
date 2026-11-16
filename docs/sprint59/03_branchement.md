# Sprint 59 — tronçon 03 : branchement dans le router image

## Objectif

Quand Nico envoie une image d'échiquier, Aria lit la position (Gemini, sinon lecteur local),
la résout avec Stockfish et répond par la **ligne principale + l'évaluation + le diagramme
de la position lue**, sans LLM (décision de Nico).

Prérequis livrés : tronçon 01 (`ImageRouter.read_board`, `chess_coach/board_reading.py` :
`grid_to_fen`, `position_problem`) et tronçon 02 (`chess_coach/board_local.read_board`).

## Contexte vérifié

- Chemin d'une photo : `telegram_interface._handle_photo` → event IMAGE → classifier :
  toujours `IMAGE_INPUT` (`cognition/cognitive_engine.py:86`) → `ImageExecutionRouter`
  (`execution/routers/image_router.py`), construit dans `core/kernel.py:92` avec
  `internal_router=InternalImageRouter()` (= `llm.image_router.ImageRouter`).
- `ImageExecutionRouter._handle_input` (l. 93) : description vision
  (`internal_router.handle_input`) → `write_image_artifact` → mode enrichi si légende
  interrogative, sinon description brute + deux tours `write_conversation_turn`
  (clé `str(metadata["chat_id"])`).
- Le classifier ne voit pas l'image : la décision « c'est un échiquier » se prend **dans
  le router**, comme le mode enrichi (règle 5 : le kernel ne décide rien).
- Contrat de sortie autorisé (règle 4) : `{"text": str, "images": [{"path", "caption"}]}`.
  `kernel._normalize` le transforme en `images_text` ; Telegram envoie les photos puis le texte.
- Diagramme : `chess_coach/render.py:115` `render_position(fen, orientation, best_uci,
  out_path, best_line_uci=…)`, `orientation="black"` retourne le plateau. Sortie dans
  `Path(config.image_output_dir) / "chess"` (comme `chess_router.py:1101`).
  `best_uci=None` plante aujourd'hui (`chess.Move.from_uci(None)`) : rendre la flèche
  facultative (`if best_uci and played_uci != best_uci`) pour le diagramme sans solution.
- Ligne numérotée : `_format_line(pv_san, move_number, color)` dans
  `execution/routers/chess_router.py:153` (« 1...dxc4 2.O-O Be7 »). Import permis
  (précédent : `board_interface` importe des privés de `chess_coach.analysis`).
- Stockfish : `config.stockfish_path`, `chess_coach.analysis.ENGINE_OPTIONS`,
  `ENGINE_TIMEOUT`. Mesure : position de référence, 3 s → 1…dxc4, +4,71 pour les noirs.

## À faire

1. **Détection** : `is_chess_image(description, caption) -> bool`, à côté de
   `is_interrogative_caption` dans `cognition/cognitive_classifier.py`. Vrai si la
   description vision contient « échiquier », « échecs » ou « chess », **ou** si la légende
   contient un mot d'échecs (« échecs », « échiquier », « mat », « trait », « résous »,
   « résoudre », « meilleur coup », « position »). Insensible à la casse.
2. **Résolution** : fonction `solve(fen) -> (score, pv)` dans `chess_coach/board_reading.py`
   (Stockfish, `Limit(time=3)`, une ligne). Score vu du camp au trait.
3. **Branche échecs** dans `_handle_input`, **avant** le mode enrichi, après
   `write_image_artifact` : si `is_chess_image(...)` :
   - grille = `internal_router.read_board(path)`, sinon `board_local.read_board(path)` ;
     journaliser lequel a servi (`[BOARD] gemini` / `[BOARD] local` / `[BOARD] illisible`).
   - Grille introuvable → `{"text": "Je n'arrive pas à lire l'échiquier : <description vision>"}`.
   - `fen, bottom = grid_to_fen(grille, caption)`. Position illégale (`position_problem`) →
     texte « Je lis une position impossible (<raison>). Voici ce que j'ai lu : renvoie une
     image plus nette. » + diagramme sans flèche + FEN lue.
   - Sinon : texte, par exemple
     ```
     Trait aux noirs. Position lue : <FEN>
     Ligne principale : 1...dxc4 2.O-O Be7 3.Re1 O-O 4.Bg5 h6
     Évaluation : +4,7 pour les noirs        (ou « mat en N pour … »)
     ```
     Ligne : 10 demi-coups au plus (la ligne de mat entière si elle est plus courte).
     Diagramme : `orientation=bottom`, flèches = 4 premiers demi-coups de la ligne.
   - Historique : deux `write_conversation_turn` (user : `[Position d'échecs lue sur image :
     <FEN>]` + légende éventuelle ; assistant : le texte de la réponse), pour qu'une relance
     (« et si 1...Qe7+ ? ») voie la position.
   - Retour `{"text": …, "images": [{"path": …, "caption": ""}]}`.
4. Image non échiquier : comportement **inchangé** (enrichi ou brut).

## Tests (cas nominal)

`tests/images/` (fakes à la manière de `test_interrogative_vision_pipeline.py`,
`write_image_artifact` et `write_conversation_turn` patchés) :
- Description « Un échiquier… », légende « trait aux noirs », `read_board` factice qui rend
  la grille de `docs/sprint59/ref/chesscom_vert.txt` → texte contenant `1...dxc4` et un
  chemin d'image existant (Stockfish réel, comme `tests/chess_coach/test_chess_coach.py`).
- `read_board` qui rend `None` → le lecteur local est appelé (monkeypatch).
- Description de jardin, légende « c'est quoi ? » → mode enrichi appelé, aucune lecture de grille.
- `is_chess_image` : un cas vrai par la description, un par la légende, un faux.

## Hors scope

- Pas de LLM dans la réponse échecs ; pas de lecture de FEN tapée en texte.
- Ne pas toucher le classifier ni le kernel ; ne pas toucher `chess_router` (import seul).
- Aucune écriture mémoire hors `write_image_artifact` / `write_conversation_turn` existants.

## Critère de fin

`pytest tests/ -q` vert ; tests ci-dessus passants. Validation réelle : tronçon 04 (Nico).
