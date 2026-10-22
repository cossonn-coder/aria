# Sprint 30 — état de conception

**Phase** : CLOS (2026-10-22) — tronçon 01 validé live, tronçon 02 échoué et annulé.
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
| 02 | `02_seuil_hnsw.md` — script ponctuel seuil HNSW + ménage `.drift-*` (#105) | ❌ annulé (revert `4cbfcf4`) |
| 03 | `03_run_live.md` — run live (Nico) | ✅ fait (01 OK, 02 KO) |

## Run live (2026-10-22)

| Critère | Résultat |
|---|---|
| « ARIA écrit… » + un seul ⏳ pendant l'analyse | ✅ |
| `telegram_update` du `salut` envoyé pendant l'analyse : immédiat | ❌ 18:49:40, 1 s après la fin de l'analyse : PTB traite les updates en séquence (`concurrent_updates` absent). Ordre visible conforme au kickoff ; critère journalctl mal posé |
| `salut` seul sans ⏳ | ✅ hors démarrage ; ❌ au 1er message après redémarrage (12 s : chargement mpnet 6 s + 413 Groq) |
| Plus de quarantaine (#105) | ❌ régression, voir incident |

### Incident palace prod (tronçon 02)

1. Le script a écrit `index_metadata.pickle` via chromadb : `dimensionality: None`, 475 labels.
2. chromadb a purgé `embeddings_queue` (510 → 14 lignes).
3. Au 1er accès, mempalace a jugé le pickle invalide (« labels present but dimensionality is
   missing ») et renommé le segment en `.corrupt-20261022-184755` → index reconstruit sur
   14 entrées.
4. Le test du tronçon ne passait pas par l'ouverture mempalace (contrôle de présence du pickle seul).

Réparation (répétée sur copie avant le prod) :
- `mempalace repair --mode from-sqlite --archive-existing` → 490 entrées, mais marqueur
  `.mempalace-embedder.json` resté dans l'archive → MiniLM 384.
- `scripts/migrate_embedder.py` → 497 entrées en mpnet 768, marqueurs reposés. Live OK
  (23:32:09, modèle mpnet, aucune quarantaine).

Archives conservées : `~/.mempalace/palace.pre-rebuild-20261022-191228` (dont
`chroma.sqlite3.bak-20261022-184520` et `.corrupt-*`),
`~/.mempalace/mempalace_drawers_backup_20261022T211500Z.tar.gz`.

## Dettes

- Fermées : #103, #104.
- Reportées : #105 (constat révisé : la quarantaine `.drift-*` au démarrage est sans dommage
  tant que la file n'est pas purgée ; tout correctif doit être validé par une ouverture mempalace).
- Nouvelles : #111 ⏳ envoyé sur un message court (seuil 10 s franchi au démarrage / sur 413
  Groq) ; #112 traitement concurrent des messages Telegram (PTB séquentiel).

## §REPRISE

Sprint clos. Suite : `docs/sprint31/context_kickoff_sprint_31.md`, puis `/conception sprint 31`.
