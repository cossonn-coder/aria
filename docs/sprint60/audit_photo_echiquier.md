# Sprint 60 — audit : photo d'échiquier physique fiable, quel que soit l'angle

Code audité sur `feat/sprint59-position-image` @ 2e32586 (2026-11-14).

## 1. Chemin actuel d'une image d'échiquier

1. `cognition/cognitive_classifier.py` règle 1 : image → `IMAGE_INPUT` → `image_router`.
2. `execution/routers/image_router.py` `_handle_input` : description vision (chaîne prod,
   deepseek-flash au run du 13/11), écriture épisodique, puis `is_chess_image(description,
   légende)` → `_handle_chess_board`.
3. `_handle_chess_board` :
   - `self.internal_router.read_board(path)` (`llm/image_router.py` `read_board`) : parcourt
     `BOARD_ROUTING_TABLE` (gemini-3.5-flash puis gemini-3.8-flash), **s'arrête à la
     première grille conforme**. Une seule lecture, aucune confrontation.
   - Secours `board_local.read_board(path)` : captures d'écran seulement (décision 59).
   - `grid_to_fen(grid, légende)` (`chess_coach/board_reading.py`) → FEN + camp du bas.
   - `position_problem(fen)` : légalité python-chess ; illégale → raison + diagramme lu,
     pas de résolution.
   - Sinon : Stockfish 3 s (`_solve_line`), texte + diagramme, marqueur de position écrit
     dans l'historique (`_write_position_history`).
4. Relance « et si X ? » : `detect_chess_board_move` (règle 1c) lit le dernier tour `user`
   (n=2) et cherche `CHESS_POSITION_MARKER` ; `_handle_board_move` rejoue sur la FEN du marqueur.

Prompt de lecture (`_BOARD_PROMPT`, `llm/image_router.py:127`) : « 8 rangées TELLES
QU'AFFICHÉES… 8 lignes de 8 caractères ». Aucune mention de perspective, de coordonnées
imprimées, ni de doute possible.

## 2. Constats

### 2.1 Aucune vérification de la lecture
Une lecture conforme et légale est résolue telle quelle. Le cas du 13/11 (fou c5 → cavalier)
est légal : rien ne pouvait l'arrêter. Stockfish a donné +2,3 pour les blancs sur une
position fausse, sans signal de doute.

### 2.2 Orientation : seulement haut/bas — photo prise de côté = FEN absurde
`_bottom_side` compare la rangée moyenne des pions (puis des rois). Si le plateau est
photographié de côté (rotation 90°), les pions sont en colonnes : la comparaison des rangées
moyennes choisit un camp au hasard et la grille est lue rangée par rangée.
Vérifié (grille vraie du 13/11 tournée de 90°) :
`grid_to_fen` → `RP4pr/NP4p1/1P2bppb/Q1P4q/K2P3k/BP3np1/1P2B1p1/RP4pr w - - 0 1`
(pions sur les 1re/8e rangées → `position_problem` répond « pion sur la première ou la
dernière rangée » : pas de résolution fausse, mais pas de résolution du tout).
Le prompt demandant la grille « telle qu'affichée », Gemini rend bien la vue tournée : la
correction se fait côté code (4 orientations, pas 2), en déduisant le sens des pions par
colonne aussi.

### 2.3 Double lecture : coût et disponibilité
- gemini-3.5-flash : ~10 s par appel [n=3, sprint 59].
- gemini-3.8-flash : 3 appels sur 4 en échec (503/timeout) [n=4, sprint 59].
- Variance mesurée sur la photo du 13/11 : voir §3.

### 2.4 Pas de mécanisme de correction
Rien ne permet de dire « c5 fou noir » : le seul message texte reconnu après une position
est un coup SAN (règle 1c). Le marqueur d'historique (FEN dans le dernier tour `user`) est
réutilisable tel quel pour une correction : même lecture (n=2), même réécriture.

### 2.5 Mesure : un seul cliché
63/64 [n=1 photo, prise de face, bonne lumière]. Aucune donnée sur les angles, la
lumière, les pièces couchées/masquées. « Quel que soit l'angle » n'est pas mesurable sans
un jeu de photos à positions connues.

## 3. Mesure de variance (2026-11-14)

Photo du 13/11, `_BOARD_PROMPT` tel quel, appels séquentiels.

| Appel | Durée | Lecture | Erreurs |
|---|---|---|---|
| 3.5-flash #1 | 65 s | c5 = cavalier | 1 (c5) → 63/64 |
| 3.5-flash #2 | 47 s | identique à #1 | 1 (c5) → 63/64 |
| 3.5-flash #3 | 52 s | c5 = fou ✓ ; c7 vide, d7 pion | 2 (c7, d7) → 62/64 |
| 3.8-flash ×3 | 90/90/7 s | timeout, timeout, 503 | aucune lecture |

Lectures :
- 3.5-flash : aucune juste [n=3] ; ~55 s par appel ce jour [n=3] (10 s au sprint 59).
- Deux lectures identiques peuvent être fausses ensemble (#1 = #2, même erreur c5).
- Les cases où les 3 lectures divergent (c5, c7, d7) contiennent toutes les erreurs
  [n=1 photo] : la divergence signale le doute, l'accord ne prouve rien.
- 3.8-flash indisponible [n=3 ce jour, n=4 au sprint 59] : une double lecture
  « 3.5 + 3.8 » n'est pas réaliste ; la seconde lecture doit être un second appel 3.5.
- Un second appel en parallèle ne rallonge pas l'attente ; en séquence, +~1 min.

## 4. Ce que le run live doit démontrer

- Photo de face, de biais, de côté : diagramme lu conforme, ou case douteuse signalée.
- Correction « c5 fou noir » : nouvelle position, Stockfish relancé, diagramme corrigé.
- Une relance « et si X ? » après correction part de la position corrigée.
