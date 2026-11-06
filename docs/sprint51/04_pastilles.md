# Sprint 51, tronçon 04 — pastilles alignées sur les flèches, comptes dans la légende

## Objectif
Demande de Nico après le run du 2026-11-06 : la couleur d'une pastille emoji est celle de la
flèche correspondante sur les miniatures, et la légende donne le nombre de coups de chaque
catégorie, pour les deux camps.

Flèches (`chess_coach/render.py`) : meilleur coup du moteur vert (`ARROW`), coup joué bleu
(`PLAYED_ARROW` ; coup joué = meilleur coup → seule la bleue reste), explosif orange,
piège cyan, erreurs en dégradé rose → rouge → noir.

## À faire (`execution/routers/chess_router.py`, `chess_coach/render.py`)

### 1. Pastilles
| Usage | Avant | Après |
|---|---|---|
| Coup joué de qualité `best` (`_QUALITY_MARK["best"]`) | 🟢 | 🔵 |
| Coup joué `correct` | 🔵 | ⚪ |
| Meilleur coup du moteur (« meilleur 🟢 X », « Meilleur coup : 🟢 … », idée Conversion) | 🟢 | 🟢 (inchangé) |
| imprécision / erreur / gaffe | 🩷 🔴 ⚫ | inchangés |
| explosif / brillant, piège | 🟠, 🩵 | inchangés |

Séparer la constante du meilleur coup du moteur (`_MARK_BEST`, utilisée dans `_caption`,
`_compared_lines`/`_told_moves`, les légendes des tronçons 02-03) de celle du coup joué
meilleur. 🟡 stratégique **n'apparaît pas** dans le message (jamais calculé sur une partie
envoyée, #157).

### 2. Légende avec comptes (remplace la constante `_MARKS_KEY` dans `_moves_line`)
Format (toi / adversaire) :
`🔵 meilleur 23 / 22 · ⚪ correct 31 / 32 · 🩷 imprécision 1 / 0 · 🔴 erreur 0 / 1 · ⚫ gaffe 0 / 0 · 🟠 explosif / brillant 3 · 🩵 piège 0 · 🟢 coup du moteur (toi / adversaire)`
- Qualités : `summary["nico_<q>"]` / `summary["opponent_<q>"]` (déjà calculés).
- 🟠 : occasions explosives non piégeantes de `analysis.explosive` + coups brillants de Nico ;
  🩵 : occasions de `analysis.explosive` dont `_trap_replies` n'est pas vide. Nico seul
  (non calculés pour l'adversaire) : un seul nombre. `_moves_line` reçoit ce qu'il faut
  (aujourd'hui elle ne reçoit que `summary`).
- La position exacte de la mention « toi / adversaire » est libre si elle reste sur la ligne.

### 3. Courbe (`_point_colors`, constantes de `render.py`)
Point d'un coup `best` : bleu (teinte RGB de `PLAYED_ARROW`) au lieu de `CURVE_BEST` vert ;
point d'un coup `correct` : blanc. Priorités existantes (erreur, piège, explosif/brillant)
inchangées ; les autres coups restent `CURVE_NEUTRAL`.

## Tests (cas nominal)
Mettre à jour les tests existants qui attendent les anciennes pastilles ; un test de la
légende avec comptes ; un test `_point_colors` (best bleu, correct blanc). `pytest tests/ -q` vert.

## Hors scope
- Échiquier web (`interfaces/board/index.html`) : palette et liste des coups inchangées (dette).
- Dégradé des erreurs, couleurs des flèches.

## Critère de fin
Tests verts ; aucune pastille 🟢 sur un coup joué, 🟢 seulement sur des coups du moteur.
