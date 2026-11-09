# Sprint 55 — État

**Phase** : B figée (2026-11-09, OK de Nico). Branche `feat/sprint55-rang-precision`.
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
| 02 | `02_run_live.md` : run live (Nico) | ⏳ |

## Dettes
Le sprint n'en ferme ni n'en ouvre. #175 (jour UTC) et #204 (couplage) restent ouvertes.

## §REPRISE
Lire `CLAUDE.md`, ce fichier et `audit_rang_precision.md`. Tronçon 01 fait (`_rank_line(summary, games)`
+ `_day` recopié dans `chess_router.py`, légende 🟢). Prochaine étape : run live 02 par Nico.
