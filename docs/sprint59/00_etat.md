# Sprint 59 — état du sprint

**Phase** : conception figée (OK de Nico, 2026-11-13), prêt pour `/sprint-auto sprint 59`.
**Sujet** : résoudre une position d'échecs envoyée en image (capture d'écran ou photo
d'échiquier physique) : lire la position, puis donner la ligne principale Stockfish.
**Branche** : `feat/sprint59-position-image`, partie de `feat/sprint58-detection-echecs`
(sprint 58 attend son run live ; merge 58 puis 59).
Audit : `docs/sprint59/audit_position_image.md`. Référence : `docs/sprint59/ref/`.

## Carte des tronçons

| # | Tronçon | Kickoff | État |
|---|---|---|---|
| 01 | Lecture Gemini → grille → FEN | `01_lecture_gemini.md` | ✅ |
| 02 | Lecteur local (repérage du plateau + cases de référence) | `02_lecteur_local.md` | ✅ |
| 03 | Branchement router image : détection, Stockfish, réponse + diagramme | `03_branchement.md` | ✅ |
| 04 | Run live (Nico) | `04_run_live.txt` | ⏳ |

## Décisions arrêtées

- Camp au trait : celui du bas, sauf « blancs » ou « noirs » dans la légende (Nico).
- Lecteur : Gemini 3.5-flash puis 3.8-flash ; lecteur local en secours si Gemini est
  indisponible (Nico). Jamais deepseek/qwen : lectures fausses à la mesure.
- Secours local : captures d'écran, plateau repéré même en plein écran, cases comparées à
  des références (plus proche voisin, numpy/PIL/scikit-learn, sans OpenCV). Pas de photo
  physique en local (Nico). Raison : aucun modèle pré-entraîné utilisable (YOLO
  ChessBoardDetector : code source disparu, aucune métrique, poids pickle « caution »).
- Déclenchement : la description vision parle d'échiquier OU la légende parle d'échecs (Nico).
- Réponse : ligne Stockfish (3 s) + éval + diagramme lu avec flèches, sans LLM (Nico).
- Orientation déduite des pions (repli : rois) ; roques si roi et tour sur leurs cases
  d'origine ; pas de prise en passant.
- Lecture illégale → raison + diagramme lu, pas de résolution. Grille illisible → le dire.
- Historique : deux tours conversation (FEN + réponse) pour les relances.
- Photo physique : mesurée au run live par Nico (cas 5).

## Dettes

- Ouvertes par le sprint : photo d'échiquier physique en local (chesscog réentraîné sur le
  jeu de Nico) ; FEN tapée en texte non lue ; `config.gemini_model = "gemini-2.0-flash"`
  obsolète (non utilisé par ce sprint).
- Sprint 58 : run live toujours en attente sur sa branche.

## §REPRISE

Tronçons 01 (6c0f101) et 02 (914cf95) commités. Tronçon 03 livré (non commité) :
`is_chess_image` (`cognition/cognitive_classifier.py`), `solve` (`chess_coach/board_reading.py`,
Stockfish 3 s), branche `_handle_chess_board` dans `execution/routers/image_router.py`
(avant le mode enrichi), flèche facultative dans `render_position` (`best_uci=None`),
`tests/images/test_chess_image.py`. Tests : 610 verts.
Historique conversation écrit seulement quand la position est résolue (pas pour une
grille illisible ni une position impossible).
Lire `CLAUDE.md`, ce fichier, puis `04_run_live.txt`.
Prochaine étape : run live par Nico (tronçon 04).
