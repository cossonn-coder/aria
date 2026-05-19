─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 12 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date** : 2026-05-19
**Branche de travail prévue** : `feat/sprint12-chroma-hnswlib-pin`
  (item #27 retenu en ouverture)
**Tag de référence sortie sprint 11** : `sprint-11`
**État sprint 11** : CLOS. Item #21 résolu — doc d'architecture
  pérenne `docs/architecture/chromadb_palace.md` créée, cross-link
  posé depuis CLAUDE.md.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 11 (rappel synthétique)

- Inauguration du dossier `docs/architecture/` comme emplacement
  pour la doc structurelle pérenne (hors-sprint). Critère
  d'admission : sujet structurel stable, non lié à un sprint
  particulier, qui mérite d'être trouvé sans avoir à fouiller
  les sprints clos.
- `docs/architecture/chromadb_palace.md` (176 lignes) acte trois
  acquis :
  - layout filesystem du palace et statut dead-code du segment
    manager Python de chromadb 1.5.x (RustBindingsAPI = chemin
    réel) ;
  - propriété observable de premier ordre : pas de FD persistant
    sur `chroma.sqlite3` → `lsof` à proscrire pour conclure sur
    l'activité du palace, `strace` ou instrumentation Python
    obligatoire ;
  - lifecycle des segments + mécanismes de quarantine du fork
    (`quarantine_stale_hnsw` pour `.drift-*` ; `quarantine_invalid_hnsw_metadata`
    pour `.corrupt-*`), avec conditions de déclenchement exactes.
- Deux audits sprint 11 datés à conserver pour la traçabilité :
  `docs/sprint11/audit_doc_emplacements.md` (tour 1, choix
  d'emplacement) et `docs/sprint11/audit_fork_mempalace_segment_lifecycle.md`
  (tour 2, lecture du code fork — réfutation littérale des
  lectures A/B du §6.1 sprint 10, verdict C tranché par
  inférence).
- Note de croisement posée : sprint 10 §2.2 formule le déclencheur
  `.drift-*` comme « count HNSW ≠ count sqlite » — formulation
  imprécise, le vrai déclencheur est mtime gap + integrity check.
  La doc pérenne renvoie au sprint 11 §2 pour le mécanisme réel.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-05-19 (post sprint 11)

| #  | Sujet                                                  | Statut                          |
|----|--------------------------------------------------------|---------------------------------|
| 9  | (legacy sprint < 6)                                    | ouvert                          |
| 10 | (legacy)                                               | ouvert                          |
| 11 | (legacy)                                               | ouvert                          |
| 13 | (legacy)                                               | ouvert                          |
| 15 | (legacy)                                               | ouvert                          |
| 16 | (legacy)                                               | ouvert                          |
| 17 | Semantic wings non câblées                             | ouvert, sujet architectural     |
| 18 | Palace MiniLM anglais sur contenu français             | RÉSOLUE sprint 8                |
| 19 | (legacy)                                               | ouvert                          |
| 20 | Drift sqlite/HNSW non flushé                           | REQUALIFIÉE sprint 9            |
| 21 | Doc structurelle chromadb palace closets               | **RÉSOLUE sprint 11**           |
| 22 | Orphelins `.drift-*` / `.corrupt-*` dans palace prod   | RÉSOLUE sprint 10               |
| 23 | (legacy)                                               | ouvert                          |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet      |
| 25 | Heredoc smoke runbook trop strict sur pattern ST       | ouvert                          |
| 26 | Artefacts résiduels `~/.mempalace/` à auditer          | PARTIELLEMENT RÉSOLUE sprint 10 (backlog "à confirmer" à reprendre) |
| 27 | `chroma-hnswlib` non pinné, traçabilité venv manquante | **cible sprint 12**             |

─────────────────────────────────────────────────────────────────────────

## Cible sprint 12 : item #27 — pin chroma-hnswlib

Dette mineure ouverte sprint 9. `chroma-hnswlib` est la couche
HNSW C++ sur laquelle repose tout `data_level0.bin` du palace
(cf. `docs/architecture/chromadb_palace.md`). Non pinnée à ce
jour → une réinstallation du venv pourrait embarquer une version
différente sans qu'on le sache. Pour un outil mono-user et
redémarrable c'est acceptable, mais le coût du pin est nul.

Tour unique prévu : pinner à la version actuellement installée
dans le venv ARIA, documenter la traçabilité dans le fichier de
dépendances utilisé.

### Hors-scope sprint 12

- Aucun upgrade de chroma-hnswlib (on épingle la version installée,
  point).
- Aucun pin d'autres dépendances (chromadb, sentence-transformers,
  etc.) — dette à part éventuelle.
- Pas de création de venv neuf.

─────────────────────────────────────────────────────────────────────────

## Backlog résiduel #26 (toujours en attente d'arbitrage Nico)

Inchangé par rapport au kickoff sprint 11 — items "à confirmer"
non actionnés. Liste depuis `docs/sprint10/audit_mempalace_artefacts.md`
§ 5 colonne "à confirmer avec Nico" :

- 3 tar.gz top niveau dans `~/.mempalace/` (~13 Mo cumul).
- `palace_backup_2026-04-22/` (15 Mo) — état pré-sprint 8, doublon
  littéral imbriqué dedans.
- `palace_preprod_20260513T124229/` (9,2 Mo) — préprod #1 mpnet.
- `palace.backup-pre-live-20260518T100943/` (9,1 Mo) — snapshot
  juste avant bascule mpnet final.
- `palace.rollback-failed-20260513T131824/` (9,2 Mo) — rollback
  raté 14 mai.
- `~/.mempalace/config.json` legacy MemPalace 3.x non lu par ARIA.
- 36 locks dans `~/.mempalace/locks/` (30 vides avril 2026 + 6
  stale).
- Snapshots pré-tours sprint 10 : `palace_backup_pre_sprint10_*.tar.gz`
  (~9 Mo cumul).

À reprendre en bordure d'un sprint qui touche au palace.

─────────────────────────────────────────────────────────────────────────

## Calibrage du niveau d'exigence (rappel)

Inchangé depuis sprint 8 : **fix qui marche + 1 test de non-régression
sur le cas nominal, rien de plus**. Pas de filets spéculatifs.

Sprint 12 #27 est mineur — pin + validation à blanc, pas de
test discriminant requis (pas un comportement systémique).

─────────────────────────────────────────────────────────────────────────

## Discipline acquise et à maintenir

Trois leçons préservées des sprints 10-11 :

1. **Test discriminant before/after avec preuve causale** — pour
   tout fix qui touche un comportement systémique. Sprint 12 #27
   n'en relève pas.
2. **Refus du mélange de scope malgré découverte adjacente** —
   sprint 11 tour 2 : verdict C émergent documenté en §5 sans
   dérouler l'investigation. À reproduire.
3. **Reconnaître l'outil structurellement inadéquat** — `lsof`
   sur chromadb-rust = vide-par-construction, pas verdict
   d'inactivité. Cf. `docs/architecture/chromadb_palace.md`
   § Propriété observable.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel pour la nouvelle session

- `main` à jour sur `sprint-11` (fait en clôture sprint 11 — ce
  commit).
- Branche de travail prévue : `feat/sprint12-chroma-hnswlib-pin`
  depuis `main` @ `sprint-11`.

─────────────────────────────────────────────────────────────────────────
