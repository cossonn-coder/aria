# Sprint 61 — état du sprint

**Phase** : clos le 2026-11-19 (run live OK, critère 4 accepté partiel → dette 6). Tag `sprint-61`.
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

## Hors kickoff (Nico, 2026-11-19, après le run live)

- Miniatures dès le coup 1 : plancher coup 4 / coup 7 en Göring retiré (`first_shown_move`),
  seuil d'erreur unique perte ≥ 10 (fin de « ouverture assumée » ≥ 20 avant le coup 11).
  Règle du répertoire (coup joué dans ≥ 2 parties, mêmes coups) et Maia coupé jusqu'au coup 10 gardés.

## Carte des tronçons

| # | Tronçon | Kickoff | État |
|---|---|---|---|
| 01 | Calcul pointe + défenses (`chess_coach/combination.py`, `analysis.py`) | `01_calcul_pointe.md` | ✅ |
| 02 | Fait « cloue », ligne Pointe, données LLM, consigne (`chess_router.py`) | `02_texte_pointe.md` | ✅ |
| 03 | Run live (Nico) | `03_run_live.txt` | ✅ |

## Dettes

| # | Dette | Constat | Piste |
|---|---|---|---|
| 1 | Question de suivi sans moteur | Historique coupé à 1 500 car. : les faits de la position N n'y sont pas (audit §3) | Router de suivi qui relance l'analyse de la position citée |
| 2 | Motif « fourchette » trompeur | `assign_motifs` tague Qxe7+ fourchette, ni clouage ni élimination du défenseur (audit C5) | Revoir l'usage des motifs dans le Pourquoi |
| 3 | Clouage relatif et mat hors pointe | Pointe limitée au gain matériel et au clouage absolu | Étendre si un cas réel le demande |
| 4 | Échiquier ARIA centré sur le joueur du bas | Demande de Nico du 2026-11-19 (anticipation adverse, flèches numérotées) | Sprint 62, `/conception` |
| 5 | Répertoire connu d'ARIA | Nico : ARIA doit savoir ce qu'il joue et le prévenir quand il sort de la meilleure ligne de son répertoire | `/conception` |
| 6 | Phrase « négligé » du Pourquoi | Run live : « tu as négligé que Be7 était en prise directe par Qe2 » ; la phrase (2) commente encore le départ, pas la pointe 14.Ba3 (critère 4 partiel, accepté par Nico) | Quand une pointe existe, (2) porte sur la pointe |
| 7 | Progression fausse à la réanalyse | Réanalyse `reason=clock` de la partie miguel_tomazii : `chess_progression OK games=439`, bloc repris de la partie précédente (« victoire contre 1714 » sur une défaite) | Recompter la progression quand la fiche est remplacée |
| 8 | Bilan inverse le camp | VitalGas : « tournant décisif dès 5.d5 (−21 pts pour l'adversaire) », 5.d5 est le coup de Nico | Données du tournant plus explicites au LLM |
| 9 | Même ouverture, deux noms | 1.e4 c5 2.Nf3 … 3.b4 : « Portsmouth Gambit » (VitalGas) et « Wing Gambit Deferred » (miguel_tomazii) : stats d'ouverture éclatées | Regrouper dans `opening_group` |
| 10 | Coups de répertoire jamais jugés | VitalGas : pire coup 5.d5 (−21 pts) sans miniature car dans le répertoire (`first_move=8`) | Lié à la dette 5 |
| 11 | Texte LLM inventé | ColdSoMe : « ton pion d7 passé » ; SuperAmendment : « 10...Be7!? sacrifie 3 pions » | Faits plus contraints |

## Run live (Nico, 2026-11-19)

- Partie miguel_tomazii (horloges, `reason=clock`) : `critical=['b:12.Ba3', …]` (sorte b, pas a), aucun
  `maia_defenses FAILED`, `chess_caption_split OK images=5`. Ligne Pointe et ligne « Si 14...a5 (93 %) »
  conformes au mot près. Pourquoi : schéma nommé, mais phrase « négligé » encore sur Be7 (dette 6).
- 4 autres parties sans pointe attendue (vérifié en local : pas de gain après préparation).
- Hors kickoff `fc19c61` (miniatures dès le coup 1) : aucune des parties envoyées ne l'exerçait
  (`first_move` du répertoire ≥ 4, pas d'imprécision 10-19 avant le coup 11). À observer.

## §REPRISE

Sprint clos. Suite : `docs/sprint62/00_etat.md`.
