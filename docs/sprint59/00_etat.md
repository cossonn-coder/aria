# Sprint 59 — état du sprint

**Phase** : conception des suites du run live figée (OK de Nico, 2026-11-13), prêt pour
`/sprint-auto sprint 59` (tronçons 05 et 06).
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
| 04 | Run live (Nico) | `04_run_live.txt` | ✅ (fait ; suites → 05-07) |
| 05 | Cas 4 : déclenchement « blancs »/« noirs » + lecteur local robuste (plein écran, surlignage, coordonnées) | `05_cas4_pleinecran.md` | ✅ |
| 06 | Relance « et si X ? » : coup joué, Stockfish, réponse + diagramme | `06_relance_coup.md` | ⏳ |
| 07 | Run live complémentaire (Nico) | `07_run_live.txt` | ⏳ |

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

## Suites du run live (conception rouverte, 2026-11-13)

Arbitrages tranchés (Nico) :
1. Déclenchement : on ajoute « blancs » et « noirs » à `_CHESS_CAPTION_RE`
   (`cognition/cognitive_classifier.py:127`). On n'ajoute pas « jouent », « plateau » ni
   « pièces » : ils déclencheraient sur des photos ordinaires.
2. Lecteur local robuste aux coordonnées dessinées et aux cases surlignées : traité dans ce sprint.
3. Relance « et si X ? » jouée puis évaluée par Stockfish : traitée dans ce sprint.
4. Relances enchaînées : chaque relance part de la position atteinte après le coup
   précédent. La nouvelle FEN est écrite dans l'historique avec le même marqueur.
5. Notation : anglaise seule (SAN : Qe7+, Nf3, exd5, O-O).
6. Réponse à une relance : même forme que pour l'image, sans LLM. Elle donne la ligne
   Stockfish après le coup, l'évaluation, et la compare au meilleur coup de la position
   de départ, avec le diagramme.

Audit : `audit_position_image.md` §Audit 2. Découpage figé (OK de Nico) :
- 05 : la capture du cas 4 est déclenchée (« blancs »/« noirs ») et lue par le lecteur local
  (bord extérieur, alternance tolérante, fond des cases surlignées).
- 06 : relance « et si X ? » : règle dans le classifieur (marqueur + coup SAN), nouvelle
  opération routée vers `image_router`, coup joué, double Stockfish, réponse et diagramme.
- 07 : run live complémentaire (cas 3 et 4 rejoués, relance enchaînée, coup illégal).

## §REPRISE

Tronçons 01-03 commités (6c0f101, 914cf95, d790bb3). Run live 04 fait ; ses suites sont
figées en 05 (cas 4) et 06 (relance « et si X ? »). Tronçon 05 fait : « blancs »/« noirs »
dans `_CHESS_CAPTION_RE` ; lecteur local : fenêtres décalées d'une case essayées, alternance
à ≤ 4 cases aberrantes (coin haut-droit, médiane), cases rognées de 3 px et fond (< 90 RGB)
mis à zéro. Capture du cas 4 lue 64/64 ; marge de reconnaissance mince (2e/1er voisin ≥ 1,11
[n=2 captures, seuils calés dessus]). Fixture : `tests/chess_coach/data/chesscom_pleinecran.*`. Capture du cas 4 et sa grille :
`docs/sprint59/ref/chesscom_pleinecran.{jpg,txt}`.
Lire `CLAUDE.md`, ce fichier, puis le kickoff du tronçon.
Prochaine étape : tronçon 06, puis run live 07 par Nico.
