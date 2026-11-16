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

## 5. Mesure du corpus P1 (2026-11-16)

Photos envoyées par Nico sur Telegram (compressées), légende « corpus p1 … ».
Lecture prod (`ImageRouter.read_board`, `_BOARD_PROMPT` inchangé, gemini-3.5-flash) →
`grid_to_fen`. Brut : `docs/sprint60/mesure_p1.txt`.

| Photo | Durée | Cases justes | Erreurs |
|---|---|---|---|
| face jour | 56 s | 48/64 | haut du plateau décalé d'une rangée |
| face soir | 33 s | 63/64 | c5 fou noir → pion |
| plongée jour | 14 s | 63/64 | c5 fou noir → pion |
| plongée soir | 31 s | 63/64 | c5 fou noir → pion |
| biais jour | 71 s | 37/64 | grille inutilisable |
| biais soir | 56 s | 17/64 | grille inutilisable |
| côté jour | 59 s | 23/64 (53/64 après bonne rotation) | orientation + lecture |
| côté soir | 48 s | 21/64 (54/64 après bonne rotation) | orientation + lecture |

Constats [n=1 position, 8 photos] :
- Face et plongée : 63/64 sur 3 photos sur 4, toujours la même erreur (fou noir c5 lu pion).
  La 4e (face jour) décale le haut du plateau d'une rangée : perspective, pièces hautes du fond.
- Biais : inutilisable. Côté : même tourné correctement, 53-54/64 → gérer 4 orientations
  dans le code ne suffit pas.
- Lumière : pas d'effet visible (le soir n'est pas pire).
- Pièces prises posées au bord du plateau sur toutes les photos (Nico : ce sera toujours le cas).
  Elles comptent : sur la photo du 13/11, 8 pions noirs lus sur le plateau + 1 pion noir pris
  à côté = 9 → l'erreur c5 aurait été détectée par le décompte.
- Le jeu de Nico semble avoir des dames de rechange posées à côté (à confirmer).

### 5.1 Prompt modifié (base de la pièce, hors plateau ignoré, ligne HORS:)

Script et prompt : `docs/sprint60/prompt_test.py`. Brut : `mesure_p1_prompt2.txt`.
4 lectures sur 8 : quota Gemini épuisé (429) après ~20 appels dans la matinée (ARIA + mesures).

| Photo | Prompt actuel | Prompt modifié | Ligne HORS lue | Vrai hors plateau (lu à l'œil) |
|---|---|---|---|---|
| face jour | 48/64 | 58/64 | n r R N p n n | q Q N p n |
| plongée soir | 63/64 | 61/64 | q Q N p n ✓ | q Q N p n |
| biais jour | 37/64 | 42/64 | N P n p q | q Q N p n |
| biais soir | 17/64 | grille non conforme | — | — |

- Pas de gain net sur la grille [n=3 lectures comparables] ; c5 toujours lu pion.
- Liste hors plateau exacte 1 fois sur 3 [n=3].
- Décompte sur plongée soir : 8 pions noirs lus sur le plateau + p hors plateau = 9 > 8 → doute
  détecté sur les pions noirs, c'est-à-dire sur l'erreur c5.
- Dames de rechange (q, Q) à côté du plateau : à exclure du décompte.
- La clé API Gemini apparaît en clair dans le texte de l'exception httpx (URL `?key=`) :
  elle peut donc figurer dans le journal ARIA. Dette, hors scope.

## 6. Pivot : captures chess.com d'abord (Nico, 2026-11-16)

Nico : « on va se contenter des impressions écran d'un échiquier digital chess.com pour le
moment car même ça ne fonctionne pas ». Cas : capture envoyée à 09:34 (thème vert, plateau seul),
`received_images/AgACAgQAAxkBAAIScmr6wC2G…ADPQQ.jpg`.

- Vraie : `2r3k1/3n1pbp/p3pnp1/1pp5/R7/1P1BP1Pq/1BPNQP1P/6K1 w`.
- Lue par ARIA : `2r3k1/3n1p1p/p3pnp1/1pp5/R7/1P1BP1Pr/1BPNQP1P/6K1 w` → fou g7 absent, dame h3
  lue tour ; Stockfish +6,6 sur une position fausse.
- Lecture faite par le **lecteur local** (même FEN reproduite hors ligne) : Gemini répondait 429,
  quota consommé par les mesures de conception en cours (09:2x-09:3x).
- Gemini rejoué sur la même capture à quota revenu : 64/64 en 6 s [n=1].

Causes dans `chess_coach/board_local.py` :
1. Une seule capture de référence (`chess_coach/data/board_refs/chesscom_vert`) : chaque pièce
   vue sur 1 ou 2 cases ; dame noire seulement sur case foncée.
2. g7 (fou noir, case foncée) : après mise à zéro du fond (`_cells`), la case vaut presque zéro →
   plus proche voisin = case vide (distance = norme du vecteur).
3. h3 (dame noire, case claire) : tour 5,62 M contre dame 5,75 M — marge ~2 %.

Positions de référence proposées (chaque pièce sur case claire ET foncée, légales, sans échec) :
- ref1 `r1b1k2r/ppq2pp1/2n1bn1p/3pp3/3PP3/2NB1N1P/PPQ1BPP1/R3K2R w - - 0 1`
- ref2 `1k1r3r/1pbqbppp/p1n2n2/4p3/4P3/P1N1BN2/1PBQ1PPP/1K1R3R w - - 0 1`
