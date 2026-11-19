# Sprint 61 — état du sprint

**Phase** : B figée le 2026-11-19 (OK de Nico). Prêt pour `/sprint-auto sprint 61`.
**Sujet** : explication tactique — trouver la pointe d'une combinaison (coup final qui gagne,
mécanisme, défenses naturelles réfutées) au lieu de commenter son point de départ.
**Branche** : `feat/sprint61-pointe-combinaison`, depuis `main` @ `52c0aab`.
Audit : `docs/sprint61/audit_pointe_combinaison.md`.

## Cas déclencheur (Nico, 2026-11-19)

Partie BaguetteChaussette – miguel_tomazii (0-1), position 1, après 11...Nxb4
(`r1b1k2r/1pq1bppp/p4n2/3p4/1n1P4/3B1N2/2P1QPPP/RNB1R1K1 w kq - 0 12`).
Meilleur 12.Qxe7+ Qxe7 13.Rxe7+ Kxe7 14.Ba3 (+3,3, Stockfish profondeur 22).
- ARIA (Pourquoi) : « Be7 était cloué et prenable : Qxe7+ gagnait une pièce entière ».
- ARIA (question de suivi) : « pièce clouée + échec disponible = prise gratuite ».
- Lecture de Nico, juste : la pointe est 14.Ba3, qui cloue Nb4 sur Ke7 ; ...a5 ne défend pas
  (15.Bxb4+ axb4 16.Rxa8, tour a8 non défendue) ; +4,3 après 14...a5 (vérifié Stockfish).

## Décisions arrêtées

- Sprint 61 sur ce sujet, le sujet 2 (échiquier ARIA centré sur le joueur du bas) au sprint
  suivant (Nico, 2026-11-19).

## Décisions arrêtées (lot 1, Nico, 2026-11-19)

- Périmètre : erreurs de Nico (sortes a / b, celles qui ont `best_line_san`). Suivi avec
  relance moteur = dette. Raison : un Pourquoi juste corrige déjà la base du suivi.
- Défenses réfutées : jusqu'à 3 (réponses Maia les plus probables après le coup préparatoire,
  hors coup de la ligne moteur), chacune avec sa réfutation et la reprise naturelle.
- Affichage : ligne « Pointe : » écrite par le code sous le diagramme ET Pourquoi du LLM qui
  s'en sert.

## Décisions arrêtées (lot 2, Nico, 2026-11-19)

- Quand la ligne Pointe existe, le Pourquoi garde (1) idée + (2) négligé, et (3) devient le
  schéma à retenir en une demi-phrase, entrée ≤ 250 car. Raison : budget légende 1 024 car.
- Découpage 01 calcul / 02 texte / 03 run live ; branche `feat/sprint61-pointe-combinaison`.

## Carte des tronçons

| # | Tronçon | Kickoff | État |
|---|---|---|---|
| 01 | Calcul pointe + défenses (`chess_coach/combination.py`, `analysis.py`) | `01_calcul_pointe.md` | ⏳ |
| 02 | Fait « cloue », ligne Pointe, données LLM, consigne (`chess_router.py`) | `02_texte_pointe.md` | ⏳ |
| 03 | Run live (Nico) | `03_run_live.txt` | ⏳ |

## Dettes

| # | Dette | Constat | Piste |
|---|---|---|---|
| 1 | Question de suivi sans moteur | Historique coupé à 1 500 car. : les faits de la position N n'y sont pas (audit §3) | Router de suivi qui relance l'analyse de la position citée |
| 2 | Motif « fourchette » trompeur | `assign_motifs` tague Qxe7+ fourchette, ni clouage ni élimination du défenseur (audit C5) | Revoir l'usage des motifs dans le Pourquoi |
| 3 | Clouage relatif et mat hors pointe | Pointe limitée au gain matériel et au clouage absolu | Étendre si un cas réel le demande |
| 4 | Échiquier ARIA centré sur le joueur du bas | Demande de Nico du 2026-11-19 (anticipation adverse, flèches numérotées) | Sprint 62, `/conception` |

## §REPRISE

Conception figée. Exécution : `/sprint-auto sprint 61` (tronçons 01 puis 02), puis run live
par Nico avec `03_run_live.txt`.
