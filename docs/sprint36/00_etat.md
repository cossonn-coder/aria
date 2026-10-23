# Sprint 36 — état de conception

**Phase** : B figée (2026-10-23) — prête pour `/sprint-auto sprint 36`.
**Branche** : `feat/sprint36-explosif`.
**Cible** : #121, redéfinir le coup explosif.

## Objectif

Signaler les gambits (4.c3 Göring), les sacrifices sur le roi (6.Fxf7+, 11.Fxh7+) et le
meilleur coup quand c'est un sacrifice, sans bruit sur les coups calmes. Mesures et
prototype : `audit_explosif.md`.

## Décisions arrêtées

Données par Nico avant conception (kickoff) : meilleur coup montré s'il est un sacrifice ;
piège Maia reste un critère ; tolérance « deux pions » ; fenêtre élargie ; Göring, Fxf7+,
Fxh7+ doivent apparaître.

Lot 1, « on suit tes recos » (2026-10-23) :
- **Sacrifice = offre acceptée** : la réponse adverse (moteur ou humaine la plus probable)
  est une prise, puis ≥ 1 pion de moins, après un de nos coups, que sur la ligne du meilleur
  coup ; perte d'évaluation ≤ 10 pts. Les « deux pions » de Nico = matériel, pas
  évaluation : 18 pts admettraient de mauvais coups (11.Te1, audit §3.b).
- **Avantage clair levé pour cette voie**, sinon Fxh7+ ne sort jamais (égalité après Rxh7).
  Le piège Maia reste une 2e voie (OU), pas une condition : le Göring est moins bon que
  4.Cxd4 face à un 1500. Rendu PGN adapté à une variante absente.
- **Restriction ajoutée en figeant (Claude, à veto de Nico)** : sans avantage clair, le
  candidat doit donner échec. Raison : le bruit 3…a6 (Morra, déficit 2) passerait sinon ;
  Fxf7+ et Fxh7+ sont des échecs, le Göring passe par l'avantage clair.
- **Portée** : live et PGN. Meilleur coup candidat en live seulement (PGN : exclu via
  `first_best_uci`, la légende l'affiche déjà). Pas de `motifs.py` (coup adverse précédent
  absent en live). `_WIN_MAX` 75 → 85.

## Tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_definition_explosif.md` — `explosive.py` (déficit d'offre acceptée, `_admissible`, meilleur coup, tri, `_WIN_MAX`) + `chess_router._explosive_lines` | ✅ (368 tests verts, non commité) |
| 02 | `02_run_live.md` — run live (Nico), coups dans `run_live_coups.txt` | ⏳ |

## Dettes

- Ferme (si run live OK) : #121.
- À surveiller au run live : 9…d5 (Espagnole, perte 7,8) admis au prototype, fréquence
  générale des flèches ; non-déterminisme (#108).

## §REPRISE

Lire : `CLAUDE.md`, ce fichier, le kickoff du prochain tronçon ⏳. Tronçon 01 fait
(`explosive.py` : `_measure_point`, `_reference_material`, `_accepted_deficit`, champ
`accepted`, voie « sacrifice accepté » dans `_admissible`, tri, `_WIN_MAX` 85 ;
`_explosive_lines` sans variante si `evidence=None`). Prochaine étape : run live par Nico
(tronçon 02, `02_run_live.md`).
