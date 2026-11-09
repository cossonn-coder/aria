# Sprint 55 — État

**Phase** : CLOS (2026-11-09, run live validé par Nico). Branche `feat/sprint55-rang-precision`.
**Sujet** : bilan d'une partie (Telegram). Rang de précision du jour et de l'ouverture, libellé
de la pastille 🟢. Audit : `audit_rang_precision.md`.

## Décisions arrêtées
- Cible du sprint 55 : demande de Nico du 2026-11-09, à la place des dettes proposées.

- Ligne 🏅 sur une seule ligne : `🏅 Précision 92 % : 52e sur 206 · 2e sur 5 aujourd'hui · 1re sur 4
  en Caro-Kann Defense (blancs)`. Un segment jour ou ouverture qui porte sur 1 partie est omis,
  parce qu'il n'apprend rien.
- Ouverture = groupe + couleur, comme la ligne 📖, pour que les deux lignes comptent les mêmes parties.
- Jour = même règle que `/parties` (`_game_day` : date PGN, sinon timestamp). #175 (UTC) est accepté.
- Légende 🟢 : libellé `🟢 meilleur coup du moteur`, sans « (toi / adversaire) » ni compte. Ce
  n'est pas un coup forcé, et le coup du moteur joué est déjà compté en 🔵.
- Telegram seulement : la ligne de l'échiquier web (`board_interface.game_history`) n'est pas
  touchée (choix par défaut annoncé à Nico).

- Le jour est recopié dans le routeur (une ligne, règle `_game_day`), sans import depuis
  `interfaces/`, pour ne pas aggraver #204.

## Tronçons
| # | Kickoff | Statut |
|---|---------|--------|
| 01 | `01_rang_precision.md` : ligne 🏅 à 3 rangs, légende 🟢 | ✅ |
| 02 | `02_run_live.md` : run live (Nico) | ✅ |

## Run live (2026-11-09)
- Ligne obtenue : `🏅 Précision 86 % : 98e sur 209 · 9e sur 24 aujourd'hui · 9e sur 10 en Portsmouth
  Gambit (blancs)` ; légende `🟢 meilleur coup du moteur`. ✅
- Écart : 10 parties classées contre 12 en 📖. Cause : 26 fiches importées du 19 au 22/10 sans
  champ `accuracy` (`accuracy_rank` les ignore). Décision de Nico : supprimer les fiches « Test »
  et poser la précision dans le palace.
- Rattrapage (`scripts/backfill_chess_accuracy.py --apply`, service arrêté) : précision recalculée
  depuis `plies_json` (contrôle : identique à ±0,1 sur les 210 fiches qui l'avaient), 24 posées,
  2 « Test » supprimées, 234 fiches toutes avec précision ; Portsmouth blancs 12/12.
  Sauvegarde `~/.mempalace/palace.pre-sprint55-20261109-153231`.

## Dettes
#98 résolue (« Test » ×2 puis « Ami » supprimées, sauvegarde `~/.mempalace/palace.pre-sprint55-20261109-160547`). #175 (jour UTC) et #204 (couplage)
restent ouvertes.

## §REPRISE
Sprint clos. Suite : `docs/sprint56/context_kickoff_sprint_56.md`, `/conception sprint 56`.
