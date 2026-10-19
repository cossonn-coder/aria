# Sprint 27 — état de conception

**Phase** : B figée (2026-10-19) — prêt pour `/sprint-auto sprint 27`
**Cible** : #87 coups conseillés « explosifs »
**Branche** : `feat/sprint27-coups-explosifs`
**Audit** : `docs/sprint27/audit_coups_explosifs.md`
**Palace prod touché** : NON (seule nouveauté : valeur `kind="d"` dans `plies_json`, structure inchangée) → calibrage faible

## Décisions arrêtées

- 2026-10-19 — Nico : cible = #87 (kickoff sprint 27).
- Q1 — Nouvelle sorte de position critique « d — occasion explosive » (Nico a joué un coup
  calme alors qu'un coup explosif tenait la fenêtre), dans le budget ≤ 3 après a/b ;
  2e flèche (orange) sur le diagramme.
- Q2 — Score v1 = les 4 composantes : sacrifice/déséquilibre, forçant, piège, volatilité.
- Q3 (réponse Nico = exemple) : Smith-Morra 1.e4 c5 2.d4 cxd4 3.c3 dxc3 4.Cxc3 Cc6 5.Cf3 Cf6
  6.Fc4 e6 7.O-O a6 8.Cd5!? doit être détecté. Mesures (audit §2 bis) : 8.Cd5 perd
  ≈ 12 pts (54,7 → 42,7, d22) et n'est PAS dans le MultiPV 6 → fenêtre fixe ≤ 5 et
  candidats MultiPV insuffisants.

- Q4 — #81 et rangement wing/room hors sprint (pas d'objection de Nico).
- Q5 — Fenêtre à deux niveaux : perte ≤ 5 pts de % de gain ; ≤ 15 si piège
  (la réponse naturelle fait perdre ≥ 10 pts à l'adversaire).
- Q6 — Réponse naturelle v1 = prise du matériel offert (sur la case d'arrivée) ;
  échec sans sacrifice → meilleure réponse. Maia en v2.
- Q7 — Budget ≤ 30 s d'analyse explosive ; Stockfish 8 threads ; recherche limitée aux
  positions de Nico non décidées (35-75 %) des 20 premiers coups ; arrêt au budget, log
  de couverture.
- Ordre de sélection : a/b, puis d, puis c (choix Claude, dans l'esprit de Q1).
- Synthèse validée par Nico (« ok », 2026-10-19) : candidats = MultiPV 5 ∪ coups par forme
  (échec, prise, pièce sur case attaquée), évalués à ≈ 0,5 s ; sacrifice mesuré sur la
  ligne (capte 2…Cf6) ; score = sacrifice + forçant + piège/5 + volatilité/10 ;
  Stockfish Threads=8 Hash=256 pour toute l'analyse ; branche créée.

## Tronçons

| # | Kickoff | Statut |
|---|---|---|
| 01 | `01_moteur_explosif.md` — `chess_coach/explosive.py`, sorte d, Threads=8, tests Morra / Dh5 | ✅ |
| 02 | `02_router_rendu.md` — flèche orange, légende, bloc enrichi, consigne | ⏳ |
| 03 | `03_run_live.md` — run live (Nico) : M1 Morra, M2 Dh5, M3 partie réelle | ⏳ |

## Dettes

- Visée : #87 (fermée si run live 03 OK).
- Hors sprint (décision Q4) : #81 bilan joueur, rangement wing `echecs` / room par ouverture.
- Maia (lc0) = v2 de #87.

## Questions ouvertes

Aucune.

## §REPRISE

Tronçon 01 fait (non commité) : `chess_coach/explosive.py` (`ExplosiveMove`, `find_explosive`),
`analysis.py` (`ENGINE_OPTIONS` Threads=8 Hash=256, champ `CriticalPosition.explosive`,
`select_critical(..., explosive=())` ordre a/b → d → c), 3 tests. pytest 297 verts.
Tests Morra / Dh5 verts sur 4 lancements [n=4] ; `analyze` Morra ≈ 21-24 s [n=2].

Écarts au kickoff (tronçon 01) :
- Import circulaire : `explosive.py` importe `analysis` ; `analyze()` importe
  `find_explosive` localement (commenté). `CriticalPosition.explosive` typé `object | None`.
- Q6 précisée : la prise sur la case d'arrivée n'est « naturelle » que si elle gagne du
  matériel à vue (pièce prise > preneuse, ou case non défendue). Sans ce filtre, a3/a6
  (pion défendu attaqué par un fou) sortaient avec un « piège » de 30-40 pts.
- Priorité d'approfondissement (≤ 3) : échec, prise ou matériel offert d'abord, puis
  perte croissante (au lieu de « pièce sur case attaquée »).
- Marge fragile : piège de 8.Cd5 mesuré 10,5 [n=1] pour un seuil de 10.
- Router : `_KIND_FR["d"]` absent → KeyError si une sorte d sort avant le tronçon 02.

Suite : tronçon 02 (`02_router_rendu.md`), puis run live 03 par Nico.
