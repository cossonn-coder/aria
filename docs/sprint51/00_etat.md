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
| 04 | `04_pastilles.md` | pastilles = couleur des flèches, comptes des deux camps, courbe | ⏳ |
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

Fermées / touchées : #170 (cause trouvée) ; #161 (horloges relues : ligne Temps, coups longs) ;
#182 partielle (réanalyse sur apport d'horloges seulement).

## §REPRISE

Tronçons 01 (`89b7e4f`) et 02 (`20c7ba0`) commités. Tronçon 03 fait (non commité) :
`chess_coach/clock.py` (`move_times`, `long_thinks`, `verdict`, `lost_on_time`, `time_line`,
`long_thinks_text`) ; `chess_router` : ligne ⏱️ Temps sous Conversion (texte + `Temps (données)`),
consigne « aucune donnée de pendule » sans horloge (variante « perdu au temps, pendule non
fournie » si `Termination` le dit), coup long déjà critique → ligne `⏱️ réfléchi N s · verdict`
dans sa légende, autres coups longs → Position n+1… (miniature, légende code, bloc de données,
consigne « Pour jouer vite : »), avant `_split_entries` ; fiche : `long_thinks`.
Choix non tranchés par le kickoff : « Réflexions de 20 s ou plus » liste tous les coups ≥ 20 s
de Nico ; « puis toi X s par coup » = moyenne du début de la période à la fin de la partie ;
Elo de Nico lu dans l'en-tête (`WhiteElo`/`BlackElo`) avant le calcul de la fiche.
543 tests verts. Prochaine étape : tronçon 04 (`04_pastilles.md`), puis run live 05.
Diagnostic de référence : `audit_conversion.md`.
