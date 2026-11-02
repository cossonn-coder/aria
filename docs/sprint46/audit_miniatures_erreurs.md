# Audit sprint 46 — miniatures du compte rendu centrées sur les coups manqués (#149)

Date : 2026-10-30. Code lu sur `main` (tag `sprint-45`).

## Demande (#149)

Le compte rendu d'une partie envoyée sur Telegram doit montrer **en priorité** des miniatures
sur les coups manqués de Nico (explosif, stratégique, piège, faute, gaffe) — « c'est en étudiant
mes mauvais coups que je vais le plus apprendre » ; garder une miniature pour un coup spectaculaire
s'il y en a un.

## Chemin de données (code réel)

1. `ChessExecutionRouter.execute` (`execution/routers/chess_router.py:560`) → `analyze(...)`
   (`chess_coach/analysis.py:459`).
2. `analyze` : `analyze_game` (Stockfish, une `PlyAnalysis` par demi-coup) → `assign_difficulty`
   (Maia) → `assign_motifs` → `find_explosive` (`chess_coach/explosive.py:386`, sorte d) →
   **`select_critical(plies, nico_color, explosive)`** (`analysis.py:406`) → `GameAnalysis.critical`.
3. `_execute_game` (`chess_router.py:601`) : **une miniature par position de `analysis.critical`**
   (`render_position`, flèche verte = meilleur coup, orange = coup explosif en sorte d), légende
   `_caption`, puis message enrichi `_build_enriched` (une entrée « Position i » par critique),
   LLM, `_split_entries` (entrée i → légende de l'image i).
4. Telegram (`interfaces/telegram_interface.py:513`) : un `send_photo` par image, puis le texte.

**Conclusion : le choix des miniatures tient entièrement dans `select_critical`.** Le router,
le rendu et l'envoi suivent la liste sans autre filtre. Seul caller prod : `analysis.py:488`
(tests : `tests/chess_coach/test_chess_coach.py:139-183`).

## Sortes de positions critiques (`_KIND_FR`, `chess_router.py:49`)

| Sorte | Sens | Coup de Nico |
|-------|------|--------------|
| a | erreur de Nico : perte ≥ 10 (≥ 20 jusqu'au coup 10) | **manqué** (imprécision / faute / gaffe) |
| b | idem juste après une erreur adverse ≥ 20 (occasion manquée) | **manqué** |
| d | occasion explosive : coup joué à perte < 10, mais un coup explosif existait (sacrifice ou piège, `explosive.py`) | **manqué** |
| e | tournant : erreur adverse ≥ 15 punie (perte de Nico < 10), avantage clair | **bon coup** |
| c | coup unique trouvé (meilleur coup, 2e à ≥ 15 pts), avantage clair | **bon coup** |

## Règle de sélection actuelle (`select_critical`, `analysis.py:406-456`)

- Budget de 3 : `(errors + turns + uniques)[:3]`, chaque liste triée par score décroissant
  (a/b par perte, e par perte adverse, c par écart au 2e coup).
- Bonus : jusqu'à 3 sortes d (meilleur score d'abord), sans évincer, positions déjà prises sautées.
- Affichage en ordre chronologique. Maximum 6 miniatures.

Écarts avec la demande :

1. **Les bons coups (c, e) remplissent le budget dès qu'il y a moins de 3 erreurs** : avec 1 erreur,
   2 miniatures sur 3 du budget peuvent être des bons coups. Pas de plafond « 1 spectaculaire ».
2. **Avec 3 erreurs ou plus, aucun bon coup n'est montré** : le « garder une miniature pour un coup
   spectaculaire » n'est pas garanti.
3. **« Stratégique » et « piège » n'existent pas dans le compte rendu Telegram.** Ce sont le rose
   (stratégie : coup au meilleur pronostic Maia-2) et le cyan (piège : coup dont les réponses
   humaines probables perdent) de l'échiquier live (`chess_coach/live.py:_human_moves`, sprint 37),
   calculés par position à la demande de la page, jamais sur une partie collée. Le piège recoupe
   en partie la sorte d (un coup explosif est admis sur sacrifice **ou piège ≥ 10 pts**,
   `explosive.py:314-323`) ; la stratégie (rose) n'a aucun équivalent.

## Observé au journal (2026-10-29/30, 11 analyses)

`chess_analysis OK … critical=[…]` : la sorte d domine (souvent 3 sur 4-6), y compris du bruit
d'ouverture (`d:2.Nf3`, `d:2.Bg2`, `d:2...Nc6`) ; `chess_explosive found=` 4 à 10 occasions pour
9 à 19 positions éligibles [n=4 analyses]. Durée totale de l'analyse 33-164 s [n=11].

## Coût d'un ajout « stratégique / piège » au compte rendu

`_human_moves` = MultiPV 8 + coups de forme + une passe Maia batchée + jusqu'à 6 candidats
approfondis avec réponses humaines. Une passe live ×1 complète (dont recherche explosive) mesure
4,8-7,9 s par position [n=8, journal 2026-10-30]. Sur 15-25 positions de Nico par partie, ajouter
`_human_moves` à chaque position ajouterait de l'ordre d'une minute [estimation non mesurée,
extrapolée des passes live] à une analyse de 33-164 s. Il faudrait aussi une règle « manqué »
(quel écart rose/cyan vs coup joué), des couleurs de flèche (cyan, rose) dans `render.py`, des
faits et une consigne LLM nouveaux.

## Points hors scope repérés

- #93 (légendes redondantes), #126 (code couleur absent de Telegram, recoupe le point 3), #108
  (non-déterminisme des d) : inchangés.

## Complément du 2026-11-02 — nouvelles demandes de Nico

### Détection d'ouverture

- **Ni Stockfish ni Maia ne nomment une ouverture** : le premier évalue, le second prédit des coups humains.
  `python-chess` n'embarque pas de table d'ouvertures non plus.
- Aujourd'hui, `summarize` (`chess_coach/summary.py:124`) lit seulement les en-têtes `Opening` / `ECOUrl`
  (slug Chess.com) : 46 fiches sur 66 sans ouverture [copie du palace, 2026-11-02], dont les parties de l'échiquier.
- `opening_family` (`player_model.py`) coupe au 1er mot de `_FAMILY_ENDS` : `Scotch-Game-Goring-…` → « Scotch Game »,
  `Caro-Kann-Defense-von-Hennig-Gambit` → « Caro-Kann Defense » : trop grossier pour le catalogue de Nico.
- Table publique `lichess-org/chess-openings` (5 TSV, `eco`, `name`, `pgn`) : 3 865 positions, 395 Ko.
  Prototype hors prod (recherche de la position la plus tardive connue, transpositions comprises) :
  **66 fiches sur 66 reconnues** [copie du palace], chargement 1,86 s [n=1].
- Catalogue de Nico, noms dans la table :

| Catalogue | Nom Lichess | Remarque |
|-----------|-------------|----------|
| Goring | Scotch Game: Göring Gambit… | y compris « Scotch Gambit, Göring Gambit Declined » |
| Rousseau | Italian Game: Rousseau Gambit | |
| Dutch | Dutch Defense… | 73 lignes |
| Benko | Benko Gambit… | |
| Icelandic | Scandinavian Defense: Icelandic-Palme Gambit | |
| Scotch Gambit | Scotch Game: Scotch Gambit… | |
| Portsmouth | Sicilian Defense: Portsmouth Gambit | |
| Delayed Wing | Sicilian Defense: Wing Gambit, Deferred Variation | nom différent |
| Alapin | French Defense: Alapin Gambit | seul « Alapin Gambit » de la table |
| von Popiel | Blackmar-Diemer Gambit: von Popiel Gambit | |
| von Hennig | Caro-Kann Defense: von Hennig Gambit + Tarrasch Defense: von Hennig Gambit | deux ouvertures distinctes |
| Hartlaub-Charlick | Englund Gambit: Hartlaub-Charlick Gambit | |

### Rooms du palace

- Une room est un champ de métadonnées d'une fiche, pas un espace séparé : tout est dans la collection
  `mempalace_drawers`, un filtre `room` isole les fiches.
- Aujourd'hui : `write_chess_game` pose `room="chess"` en dur (`memory/writer.py:155`), 66 fiches.
- Lecture : `load_chess_games` filtre wing + type (`mempalace_bridge.py:345`), donc insensible à la room.
  Le rappel exclut seulement `general` ; `context_builder` traite seulement `documents` à part. Aucun code
  ne lit `room == "chess"` en prod ; un test l'affirme (`tests/memory/test_writer.py:277`).
- Les statistiques n'ont pas besoin de la room : `outcome` est dans chaque fiche, le profil est recalculé.
- Issue inconnue (`Result *`) : 10 fiches sur 66, exclues des pourcentages ; #98 : fiches parasites comprises.
- Ranger les 66 fiches existantes touche le **palace prod** (exception au calibrage faible).

### Miniatures

- Flèche du coup joué : `render_position` a une flèche verte et une orange ; `PlyAnalysis.uci` donne le coup joué.
- Coup 4 : filtre à poser dans `select_critical` (retire le bruit `d:2.Nf3`, `d:3.Bc4`).
- Plan stratégique : la consigne demande déjà « l'idée générale (plan, pièce faible, roi exposé…) », mais le bloc
  enrichi ne donne que des faits tactiques (pièces, matériel, attaquées, ligne). Rien sur la structure de pions, les
  colonnes ouvertes, le roque. Le LLM invente ce qui manque (#92). La consigne est dans `chess_router`, le prompt
  AnalystAgent n'est pas concerné.

### Progression par phase

- `LABELS` a `opening` et `endgame`, pas de milieu de jeu ; un thème à variation nulle n'est pas affiché.
- Prototype d'un thème `middlegame` (`phase == "middlegame"`) : Milieu de jeu 1412 [131 épreuves, 53 fiches de saison] ;
  Global reste à 1420 avant et après [mêmes fiches] ; Ouverture 1652 [51 épreuves], Finale 1380 [46 épreuves].
