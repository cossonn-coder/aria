# Sprint 36 — tronçon 01 : nouvelle définition du coup explosif (#121)

À lire avant : `CLAUDE.md`, `docs/sprint36/00_etat.md`, `docs/sprint36/audit_explosif.md`
(§1 chemin de données, §3.b mesures du prototype, §5 rendu PGN, §6 exclusions).

## Objectif

Le moteur doit signaler les gambits (4.c3 Göring), les sacrifices sur le roi (6.Fxf7+,
11.Fxh7+) et le meilleur coup quand c'est un sacrifice, sans faire apparaître les coups
calmes qui laissent simplement du matériel en prise. Usages : échiquier live
(`live.analyse_pass`) et analyse PGN (`find_explosive`), via `_search_position`.

## Fichiers à toucher

- `chess_coach/explosive.py`
- `execution/routers/chess_router.py` (`_explosive_lines` seulement)
- `tests/chess_coach/test_chess_coach.py`, `tests/execution/test_chess_router.py`

## Comportement attendu

1. **Déficit d'offre acceptée** : nouvelle fonction pure, par exemple
   `_accepted_deficit(board, line, reference) -> int`. Ici, `line` = [candidat, réponse, …]
   en `chess.Move`, et `reference` = matériel de référence du trait (pions,
   `_material`). Elle rend 0 si la ligne a moins de 3 demi-coups ou si la réponse
   (`line[1]`) n'est pas une prise. Sinon : le maximum, borné à 0, de
   `reference − _material(position, trait)` mesuré après chacun des coups suivants du trait
   (`line[2]`, `line[4]`, … dans la borne `_LINE_MAX` demi-coups).
2. **Matériel de référence** (calculé une fois par position dans `_search_position`) :
   max(matériel du trait au départ, matériel du trait au point de mesure de
   `_line_sacrifice` sur la PV du meilleur coup `reference[0]["pv"]`). Il faut le matériel
   réel au point de mesure, pas le `max(0, …)` que rend `_line_sacrifice` : adapter ou
   ajouter un petit helper, au choix.
3. **`ExplosiveMove`** : nouveau champ `accepted: int = 0`. `_deepen` reçoit le matériel
   de référence et calcule `accepted` = max du déficit sur la ligne moteur
   (`line = [move] + principal["pv"]`) et sur la ligne de la réponse humaine la plus
   probable (`[move] + logical["pv"]`, `logical` déjà calculé). Aucun appel moteur de plus.
4. **`_admissible`** : on ajoute une voie « sacrifice accepté », en OU avec la règle
   actuelle, qui reste inchangée (avantage clair exigé) :
   `accepted ≥ 1` et `loss ≤ 10` (nouvelle constante, ex. `_SACRIFICE_WINDOW = 10`) et
   (`evidence` non nulle **ou** `"check" in forcing`).
   L'échec permet de lever l'avantage clair (Fxh7+ à égalité après Rxh7, audit §3.b),
   sans laisser passer le bruit 3…a6 de la Morra (déficit 2, pas d'avantage clair,
   pas d'échec).
5. **`_search_position`** :
   - retirer `move != best` des exclusions, en gardant `played_uci` et `first_best_uci`.
     En PGN, le meilleur coup reste donc exclu via `first_best_uci` ; en live
     (`""`), il devient candidat (audit §6). Le garde `after(best).is_game_over()` reste.
   - Le filtre de perte des candidats reste `≤ _TRAP_WINDOW` (15).
   - Tri des candidats : d'abord ceux dont `_accepted_deficit` sur la PV de racine est ≥ 1.
     Cette PV est déjà rendue par l'analyse `reference` ou l'analyse des coups « par
     forme » : la conserver par coup. Ensuite viennent `_priority`, puis la perte
     croissante. `_MAX_DEEP` reste à 3.
   - Choix final inchangé : candidat admissible au plus fort `score`.
6. **Fenêtre de positions** : `_WIN_MAX` passe de 75 à 85 (`_WIN_MIN` reste 35). La
   constante est partagée par `live.py` et `find_explosive` : rien d'autre à toucher.
7. **Rendu PGN** (`chess_router._explosive_lines`) : un explosif admis sans avantage clair
   a `evidence=None`, `trap_end_fen=None`, `trap_line_san=[]`. Dans ce cas, ne pas écrire
   les lignes « variante : », « faits : » et les deux lignes « fin de variante », car
   `_EVIDENCE_FR[None]` et `_material_line(None, …)` casseraient. Les autres lignes
   restent (réponses humaines, espérance, pari). Fait matériel : si `offered` est nul et
   que `max(sacrifice, accepted)` ≥ 1, écrire « sacrifie N pion(s) sur la ligne » avec ce
   maximum. `_variant_line` gère déjà une `trap_line_san` vide : rien à y changer.

## Tests à ajouter (cas nominal, sans moteur)

- `_accepted_deficit` : position après 1.e4 e5 2.Nf3 Nc6 3.d4 exd4, ligne
  4.c3 dxc3 5.Nxc3, référence 0 → 1 ; ligne 4.Be2 Nf6 5.Nxd4, référence 0 → 0 (réponse
  sans prise).
- `_admissible` : `accepted=2`, `forcing=["check", "capture"]`, `evidence=None`, perte 0
  → vrai ; `accepted=2`, `forcing=[]`, `evidence=None`, perte 4 → faux.
- `chess_router` : un explosif `evidence=None` (sur le modèle de
  `test_explosive_position_caption_arrow_and_enriched`) se rend sans exception, et « variante : »
  est absent du contenu enrichi.

Les tests existants (`test_explosive_admissible_hybrid`, `test_live.py`, router) restent
verts sans modification.

## Hors-scope (ne pas faire)

- Pas de `motifs.py` dans la recherche (décision sprint 36).
- Ne pas toucher `live.py`, `board_interface.py`, `index.html`, `analysis.py`, ni les temps
  moteur (`_ROOT_TIME`, `_DEEP_TIME`, …), ni `_MAX_DEEP`, ni la règle Maia.
- Pas de nouveau paramètre à `_search_position` : sa signature reste la même.
- Ne pas modifier le prompt AnalystAgent ni la consigne d'occasion explosive du router.

## Critère de fin

`pytest tests/ -q` vert. Smoke facultatif hors tests : `_search_position` réel sur la
position B (après 5…Fc5) rend 6.Fxf7+ [n=1, non déterministe].
