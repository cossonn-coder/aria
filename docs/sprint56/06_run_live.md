# Sprint 56 — Tronçon 06 : run live (Nico)

Messages à copier : `docs/sprint56/06_run_live.txt` (un bloc = un message, dans l'ordre).

## Préparation (service arrêté)

1. Nico : `sudo systemctl stop aria.service`
2. Claude Code : sauvegarde `cp -a ~/.mempalace/palace ~/.mempalace/palace.pre-sprint56-dedup`,
   puis `./venv/bin/python scripts/sprint56_dedup_games.py` (lecture : 2 paires attendues,
   Amateurspoeler 53/47 et UIALY 105/101), puis `--apply`.
3. Nico : `sudo systemctl start aria.service`, puis `sudo journalctl -u aria -f -o cat`.

## Critères de succès

| Msg | Attendu |
|---|---|
| 1 | « Cette partie contre Amateurspoeler a déjà été envoyée le 2026-11-11. » ; journal `chess_router duplicate … prefix_of=` |
| 2 | analyse complète ; journal `chess_router extend old=chess_game_abe4f57a080108d6 new=…`, `chess_game_write OK … plies=73` |
| 3 | `✅ Issue corrigée : contre Tailor4321 (2026-11-11) → victoire.` |
| 4 | parties du 11/11 : **une seule** Amateurspoeler (victoire), **une seule** Tailor4321 (victoire) ; pas de doublon UIALY sur `/parties all` |
| 5-6 | consigne enregistrée puis listée en 1. |
| 7 | le LLM cite les 3 vraies dernières parties (adversaires et issues = `/parties`) ; journal `chess_games_context n=3` |
| 8 | Aria ne prétend pas corriger ; elle indique `/issue` |
| 9 | Aria ne promet pas ; elle dit que l'alerte existe déjà (ou que c'est du code) — sans « noté » nu |
| 10-11 | consigne retirée, `Aucune consigne.` |
| bilan msg 2 | si la précision adverse ≥ 95 % sur ≥ 20 coups : ligne `⚠️ Précision adverse …` (sinon absente, normal) |

Journal : aucun `Error finding id`, aucun `Quarantined` sur le segment actif après les suppressions
(le correctif fork `252c96a5` est en jeu : redémarrer une 2e fois après le run et vérifier).

Les critères 8 et 9 dépendent du LLM : un écart se note [n=1] et ne bloque pas la clôture si les
règles sont bien dans le prompt (log ou test).
