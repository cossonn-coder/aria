# Sprint 51 — État (carnet de bord)

**Sujet** : convertir une position gagnante + analyse du temps d'un PGN (#161, #170),
plus pastilles alignées sur les flèches (demande de Nico du 2026-11-06).
**Phase** : B — conception figée (OK de Nico le 2026-11-06), prête pour `/sprint-auto sprint 51`.
**Branche** : `feat/sprint51-conversion` (depuis `main` @ `4d3b3d9`, tag `sprint-50`).
**Tests au départ** : 533 verts.

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_reanalyse.md` | PGN avec horloges → réanalyse d'une fiche sans horloge, date conservée | ✅ (535 verts) |
| 02 | `02_conversion.md` | période gagnante, idées répétées non jouées, ligne + miniature, fiche | ✅ (537 verts) |
| 03 | `03_temps.md` | ligne Temps, 3 coups longs analysés, consigne sans horloge, fiche | ✅ (543 verts) |
| 04 | `04_pastilles.md` | pastilles = couleur des flèches, comptes des deux camps, courbe | ✅ (544 verts) |
| 06 | (hors kickoff, demandé par Nico le 2026-11-06) | PGN collé découpé par Telegram (> 4 096 car.) : fragments recollés dans `_handle_message` | ✅ |
| 05 | `05_run_live.md` (+ `05_run_live.txt`) | run live par Nico | ⏳ |

Ordre imposé : 03 réutilise la période de conversion de 02 ; 04 recolore les légendes de 02-03.

## Décisions arrêtées

- Source des horloges : PGN collé avec horodatage chess.com (`%clk`), lu par `python-chess`.
  Cause de #170 : copie sans horodatage. API chess.com non utilisée (#83 reste ouverte).
- Forme conversion : ligne écrite par le code + 1 miniature hors budget (1er coup de l'idée
  principale) ; le LLM explique les concepts au bilan.
- Déclencheur conversion : issue défaite ou nulle (pas `unknown`), ≥ 10 coups consécutifs de
  Nico à `win_before` ≥ 80 %.
- Idée répétée : même meilleur coup non joué ≥ 3 fois dans une fenêtre de 6 coups de Nico ;
  concept nommé par le code ; 2 idées au plus.
- Mémoire : idées manquées et coups longs dans la fiche ; compteur entre parties → dette.
- PGN avec horloges = Nico a peiné à trouver ses coups dans le temps : les coups longs sont
  analysés, pas seulement listés.
- Temps : ligne écrite par le code ; sans horloge, consigne interdisant toute cause liée au
  temps (sauf « perdu au temps, pendule non fournie »).
- Coups longs : les 3 plus longs à ≥ 20 s, budget à part (pas de doublon avec une position
  critique), verdict écrit par le code + entrée LLM « Pour jouer vite : ».
- Réanalyse : fiche sans horloge + PGN avec horloges → réanalyse, `timestamp` d'origine
  conservé (paramètre structurel de `write_chess_game`, posé après `extra`).
- Pastilles : coup joué meilleur 🔵, meilleur coup du moteur 🟢, correct ⚪, 🟠 / 🩵 / 🩷 🔴 ⚫
  inchangés, 🟡 absent du message ; légende avec comptes toi / adversaire ; courbe : meilleur
  bleu, correct blanc.

## Palace prod
Le tronçon 01 permet de réécrire une fiche existante (upsert, même id) ; au run live, une
seule fiche réécrite (dusha28). Pas de migration.

## Dettes

Ouvertes par le sprint :
- Compteur inter-parties des idées de conversion manquées (« roi pas activé dans 3 parties »).
- Plan adverse répété non exploité (g5 proposé 9 fois à dusha28).
- Thème « Convertir l'avantage » du profil aveugle aux conversions lentes (`_is_trial` exige
  une perte ou un écart ≥ 10 et `win_before ≤ 90`).
- Échiquier web : palette de la liste des coups non alignée sur les nouvelles pastilles.
- **Candidat sprint 52 (accord de Nico)** : niveau joué estimé par Maia pour chaque camp, avec
  fourchette (vraisemblance des coups joués par tranche Elo), + Elo officiels affichés dans le
  bilan ; tendance multi-parties dans `/ouvertures` et `/parties`.
- Fiche tronquée en palace prod : partie BaguetteChaussette – luismota32 du 2026-11-06, collée
  avant le tronçon 06, analysée sur sa 1re moitié (`hash=2d5aed504532ea89`, 76 plies sur 107).
  Comptée dans la progression ; suppression à arbitrer.

Fermées / touchées : #170 (cause trouvée) ; #161 (horloges relues : ligne Temps, coups longs) ;
#182 partielle (réanalyse sur apport d'horloges seulement).

## §REPRISE

Tronçons 01 (`89b7e4f`), 02 (`20c7ba0`), 03 (`ed8923e`) commités. Tronçon 04 fait (non commité) :
`chess_router` : `_QUALITY_MARK` best 🔵 / correct ⚪, `_MARK_BEST` 🟢 réservé au coup du moteur ;
`_MARKS_KEY` devient la liste (qualité, libellé) et `_marks_key(summary, analysis)` écrit la clé avec
comptes toi / adversaire (🟠 = explosifs non piégeants + brillants de Nico, 🩵 = explosifs piégeants) ;
`_moves_line(summary, analysis)` ; `_point_colors` : best `CURVE_BEST` (= `PLAYED_ARROW[:3]`), correct
`CURVE_CORRECT` blanc (`render.py`). Mention « (toi / adversaire) » placée après 🟢 coup du moteur.
Tronçon 04 commité (`24fbbf2`). Tronçon 06 (recollage des fragments de PGN,
`interfaces/telegram_interface.py`, attente 10 s sans suite) : 545 tests verts.
Prochaine étape : run live 05 (`05_run_live.md`) par Nico.
Diagnostic de référence : `audit_conversion.md`.
