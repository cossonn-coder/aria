# Sprint 26 — Tronçon 01 : paquet `chess_coach/` (moteur + rendu)

Lire d'abord : `CLAUDE.md`, `docs/sprint26/00_etat.md` (décisions Q1-Q8).

## Objectif

Créer un paquet **pur** `chess_coach/` (aucun import de `memory/`, `llm/`,
`execution/` ; pas d'écriture mémoire, pas d'appel LLM) qui, à partir d'un
texte PGN :
1. parse la partie et détermine la couleur de Nico ;
2. analyse chaque position avec Stockfish ;
3. qualifie chaque demi-coup et sélectionne ≤ 3 positions critiques ;
4. dessine une position en PNG ;
5. traduit le SAN en notation française.

Aucun câblage dans le pipeline à ce tronçon (c'est le 02).

## Pré-requis environnement

- Stockfish 17.1 installé : `/usr/games/stockfish` (vérifié). N'est PAS dans le
  PATH systemd → chemin absolu.
- Ajouter `chess>=1.11` à `requirements.txt` (section CORE UTILS) et l'installer :
  `./venv/bin/pip install "chess>=1.11"`.
- `config.py` : ajouter `stockfish_path: str = "/usr/games/stockfish"` et
  `chess_username: str = "staroflexeur"` (champs du dataclass, style existant ;
  pas de variable d'environnement).

## Fichiers à créer

### `chess_coach/__init__.py` (vide ou exports simples)

### `chess_coach/notation.py`

- `to_french(san: str) -> str` : `str.translate` simultané N→C, B→F, R→T, Q→D, K→R
  (les colonnes sont en minuscules, donc sans collision ; `=Q` → `=D` ; `O-O` intact).

### `chess_coach/analysis.py`

Dataclasses (noms indicatifs) :

- `PlyAnalysis` : `ply` (index 0-based), `move_number`, `color` ("white"/"black"),
  `san`, `uci`, `fen_before`, `win_before`, `win_after` (tous deux en % de gain
  **du point de vue du joueur qui joue ce coup**), `loss` (= max(0, win_before − win_after)),
  `best_san`, `best_uci`, `pv_san` (liste ≤ 6 demi-coups depuis fen_before),
  `second_gap` (win% meilleur − win% 2e meilleur, None si un seul coup légal),
  `quality` ("best" | "correct" | "inaccuracy" | "mistake" | "blunder"),
  `phase` ("opening" | "middlegame" | "endgame"), `tags` (liste de str),
  `clock` (secondes restantes après le coup si `%clk` présent, sinon None),
  `eval_before_cp` (point de vue blanc, mate converti), `eval_after_cp`.
- `CriticalPosition` : `kind` ("a" | "b" | "c"), `ply` (le PlyAnalysis du coup de Nico
  concerné), `score` (pour le classement).
- `GameAnalysis` : `headers` (dict), `nico_color` ("white"/"black"),
  `color_source` ("header" | "message" | "default"), `plies` (liste PlyAnalysis),
  `critical` (liste CriticalPosition, ≤ 3, ordonnée).

Fonctions :

- `parse_pgn(text: str) -> chess.pgn.Game | None` : le message peut contenir du texte
  libre avant le PGN (« je joue les noirs ») → lire à partir de la première ligne
  commençant par `[` ; `chess.pgn.read_game(io.StringIO(...))` ; None si pas de
  partie, 0 coup, ou `game.errors` non vide (coup illégal).
- `detect_color(headers, message: str, username: str) -> tuple[str, str]` :
  1. `headers["White"]`/`["Black"]` == username (insensible à la casse) → "header" ;
  2. sinon regex sur le message : « je joue (avec )?(les )?(noirs|blancs) » → "message" ;
  3. sinon ("white", "default").
- `analyze_game(game, nico_color, engine_path, time_per_position=0.15) -> list[PlyAnalysis]` :
  `chess.engine.SimpleEngine.popen_uci(engine_path)`, **une** analyse par position
  (`multipv=2`, `Limit(time=time_per_position)`), positions 0..N (N+1 analyses),
  moteur fermé en `finally` / `with`. Conversion cp → win% (formule Lichess) :
  `cp` borné à ±1000 (mat → `score(mate_score=100000)` puis borne),
  `win = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)`.
  `win_after` du coup = win% de la position suivante vue du joueur qui a joué.
  Sur la dernière position (mat/pat/fin), utiliser le résultat de la position
  (`board.is_checkmate()` → 0/100) si le moteur ne rend pas de score.
- Qualité : `best` si coup joué == meilleur coup ; sinon perte ≥ 30 → `blunder`,
  ≥ 20 → `mistake`, ≥ 10 → `inaccuracy`, sinon `correct`.
- Phase : `opening` si `move_number <= 10` ; `endgame` si plus de dames sur
  l'échiquier OU matériel non-pion total (deux camps) ≤ 13 (C=F=3, T=5, D=9) ;
  sinon `middlegame`.
- Tags (coup joué) : `capture`, `check`, `pawn`, `king`, `castle`, `retreat`
  (pièce non-pion qui recule vers sa propre première rangée), `hanging`
  (après le coup, une pièce non-roi du joueur est attaquée par l'adversaire et
  non défendue par son camp).
- Pendule : `node.clock()` de python-chess (None si absent).
- `select_critical(plies, nico_color) -> list[CriticalPosition]` :
  - (a) coup de Nico avec `loss >= 10` → kind "a", score = loss ;
  - (b) si le coup adverse **précédent** a `loss >= 20` et que la réponse de Nico
    a `loss >= 10` → kind "b" (remplace "a" pour ce coup), score = loss ;
  - (c) coup de Nico `quality == "best"` avec `second_gap >= 20`, en excluant :
    position déjà jouée d'avance (win_before > 90 ou < 10), ≤ 2 coups légaux,
    reprise sur la case de la prise adverse précédente ; score = second_gap ;
  - retenir a/b par score décroissant, compléter avec c par score décroissant,
    ≤ 3 au total ; ordre final = ordre chronologique (ply croissant).
  - Si aucune : retenir le coup de Nico de plus grande `loss` (kind "a") s'il en existe.
- `analyze(text, message, username, engine_path) -> GameAnalysis | None` :
  enchaîne parse → couleur → analyse → sélection.

Logs : `log.info("chess_analysis OK plies=%d nico=%s source=%s critical=%s duration=%.1fs", …)`.

### `chess_coach/render.py`

- `render_position(fen, orientation, best_uci, out_path) -> str` : PNG ~480 px,
  Pillow seul, police `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`
  (glyphes U+2654-265F). Exigences : cases claires/foncées, pièces blanches et
  noires clairement distinguables (ex. glyphe plein rempli de blanc + contour noir
  pour les blancs), coordonnées a-h / 1-8 sur les bords, **échiquier retourné si
  orientation == "black"**, **une flèche** (vert) du meilleur coup de `best_uci`.
  Retourne le chemin écrit.
- Les images vont dans `Path(config.image_output_dir) / "chess"` — mais `render.py`
  reçoit `out_path` du caller (pas d'import config dans render).

## Tests à ajouter (`tests/chess_coach/`)

Cas nominaux, sans exhaustivité :
- `to_french("Nxe5")` == `"Cxe5"`, `to_french("e8=Q+")` == `"e8=D+"`, `to_french("Kf2")` == `"Rf2"`.
- `detect_color` : en-tête Black == "staroflexeur" → ("black","header") ;
  sans pseudo + « je joue les noirs » → ("black","message") ; rien → ("white","default").
- `analyze` sur une mini-partie connue avec gaffe évidente (ex. PGN avec en-têtes,
  Nico noir, `1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7#`) avec le vrai Stockfish
  (`pytest.mark.skipif(not Path("/usr/games/stockfish").exists())`) :
  le coup `3...Nf6` est `blunder`, et il figure dans `critical` (kind "a").
- `render_position` écrit un PNG lisible par Pillow, taille attendue, dans `tmp_path`.

## Hors scope (ne PAS faire)

- Aucun câblage classifier / router / kernel / Telegram (tronçon 02).
- Aucune écriture mémoire, aucune fiche de synthèse (tronçon 03).
- Pas de détection de motifs tactiques (fourchette, clouage…).
- Pas de lecture d'image / FEN depuis photo.

## Critère de fin

- `pytest tests/ -q` vert.
- `./venv/bin/python -c "from chess_coach.analysis import analyze; ..."` sur le PGN
  de la partie 2 de Nico (dans `docs/sprint26/04_run_live.md`, message B) renvoie
  `nico_color == "black"` et 1 à 3 positions critiques, en < 30 s.
