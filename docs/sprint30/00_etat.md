# Sprint 30 — état de conception

**Phase** : B figée (2026-10-22) — prêt pour `/sprint-auto sprint 30`.
**Branche** : `feat/sprint30-fiabilite-analyse`.

## Décisions arrêtées

- Q1 cible = fiabilité de l'analyse : #103 (boucle du bot bloquée pendant l'analyse) + #105 (quarantaine HNSW récurrente, recoupe #31). Raison : gain ressenti à chaque partie, peu de code. (2026-10-22)
- Q2 #103 : traitement déporté dans un thread + indicateur « ARIA écrit… » tenu jusqu'à la
  réponse. Raison : le déblocage seul n'a pas d'effet visible (audit).
- Q3 #105 : script ponctuel qui baisse `sync_threshold` / `batch_size` de `mempalace_drawers`
  (≈ 100) + ménage des `.drift-*`, sauvegarde de `chroma.sqlite3` avant. **Palace prod touché**.
- Q2 bis (Nico) : pas de spam → indicateur natif « écrit… » (pas un message) + **un seul**
  message « ⏳ Je travaille dessus, ça peut prendre jusqu'à 2 minutes. » si > 10 s.
- #105 : Nico délègue entièrement (« je te fais confiance »), découpage 01/02/03 OK.
- Q4 : #104 ajouté (photo en échec sautée, le texte part quand même).

## Questions ouvertes

(aucune)

## Tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_attente_visible.md` — thread + « écrit… » + message unique (#103), photo en échec sautée (#104) | ⏳ |
| 02 | `02_seuil_hnsw.md` — script ponctuel seuil HNSW + ménage `.drift-*` (#105) | ⏳ |
| 03 | `03_run_live.md` — run live (Nico) | ⏳ |

## Dettes

- Fermées si le sprint passe : #103, #104, #105 (et #31 pour `mempalace_drawers`).

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_fiabilite_analyse.md`, puis le kickoff du premier tronçon ⏳.
Prochaine étape : `/sprint-auto sprint 30`.
