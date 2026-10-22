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
| 01 | `01_attente_visible.md` — thread + « écrit… » + message unique (#103), photo en échec sautée (#104) | ✅ |
| 02 | `02_seuil_hnsw.md` — script ponctuel seuil HNSW + ménage `.drift-*` (#105) | ✅ |
| 03 | `03_run_live.md` — run live (Nico) | ⏳ |

## Dettes

- Fermées si le sprint passe : #103, #104, #105 (et #31 pour `mempalace_drawers`).

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_fiabilite_analyse.md`, puis le kickoff du premier tronçon ⏳.
Tronçon 01 fait (2026-10-22) : `core/kernel.py` (`asyncio.to_thread` sur classify/dispatch),
`interfaces/telegram_interface.py` (`_handle_with_waiting` : « écrit… » toutes les 4 s +
message d'attente unique à 10 s ; photo `images_text` en échec sautée). Tests : 351 verts.
Tronçon 02 fait (2026-10-22) : `scripts/mempalace_sync_threshold.py` (garde `aria.service` actif
si pas de chemin explicite, sauvegarde `chroma.sqlite3.bak-<horodatage>`, `modify` seuil/batch 100,
réouverture + requête dans un sous-process, contrôle du pickle, suppression des `.drift-*`) +
`tests/test_mempalace_sync_threshold.py` (palace tmp, 150 entrées : sans le script, pas de pickle
même après réouverture). **Non lancé sur le palace prod.** Tests : 352 verts.
Prochaine étape : tronçon 03 (run live Nico) : `sudo systemctl stop aria.service &&
./venv/bin/python scripts/mempalace_sync_threshold.py && sudo systemctl start aria.service`.
