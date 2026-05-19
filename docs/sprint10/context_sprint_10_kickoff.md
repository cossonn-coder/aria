─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 10 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date** : 2026-05-19
**Branche de travail prévue** : à décider en ouverture de sprint
  selon l'item sélectionné en premier
**Tag de référence sortie sprint 9** : `sprint-9`
**État sprint 9** : CLOS. Audit complet dette #20 livré, requalifiée
  en comportement structurel chromadb-rust, drift bénin garanti par
  replay WAL. Pas de fix. Mergé dans main.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 9 (rappel synthétique)

- Cartographie complète du chemin de fermeture palace sur trois
  étages : fork MemPalace 3.3.5, chromadb 1.5.5 (Python ET Rust),
  ARIA. Documenté en `docs/sprint9/audit_drift_hnsw.md`.
- Instrumentation discriminante : métrique pickle.mtime + monkey-patch
  `_persist` + lecture `LocalSegmentManager._instances`. Trois preuves
  indépendantes convergent : la couche Python `local_persistent_hnsw`
  est dead code en chromadb 1.5.5, tous les writes routent vers
  `RustBindingsAPI`. Documenté en `docs/sprint9/audit_drift_hnsw_metric.md`.
- Repro reproductible : `docs/sprint9/repro_drift.py`, 7 méthodes
  de fermeture testées (no-close, backend-close, client-close,
  context-mgr, persist-then-close, SIGTERM, SIGKILL), aucune ne
  déclenche un flush HNSW Python (logique : il n'y en a pas à
  déclencher).
- Confirmation prod : zéro nouveau `drift-*` / `corrupt-*` apparu
  depuis le 18 mai 2026.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 19 mai 2026

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
| 20 | Drift sqlite/HNSW non flushé                           | **REQUALIFIÉE sprint 9** (comportement structurel chromadb-rust, drift bénin, replay WAL garantit count complet) |
| 21 | Collection closets legacy dim 384                      | ouvert, atténué par fork        |
| 22 | Orphelins `.drift-*` / `.corrupt-*` dans palace prod   | ouvert, hygiène                 |
| 23 | (legacy)                                               | ouvert                          |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet      |
| 25 | Heredoc smoke runbook trop strict sur pattern ST       | ouvert                          |
| 26 | Artefacts résiduels `~/.mempalace/` à auditer          | ouvert                          |
| 27 | `chroma-hnswlib` non pinné, traçabilité venv manquante | **NOUVEAU sprint 9**, mineure   |

─────────────────────────────────────────────────────────────────────────

## Cible sprint 10 : indéterminée à l'ouverture

Nico a explicitement renvoyé le choix au sprint 10 lui-même. Premier
travail de la nouvelle session : trancher l'item prioritaire parmi
les dettes ouvertes. Les candidats utiles à classer :

### Candidats opérationnels (impact direct, effort bas/moyen)

- **#22 — orphelins drift-* / corrupt-* dans palace prod**
  Nettoyage hygiène, ramasse-miettes sur le palace actuel. Effort bas,
  bénéfice marginal mais visible (réduction taille palace, log de
  démarrage plus propre). Test de non-régression trivial.

- **#25 — heredoc smoke runbook trop strict sur pattern ST**
  Hérité du sprint 8. Impact sur le confort de Nico quand il valide
  une fumée. Effort très bas, fix probablement à 2-3 lignes.

- **#26 — audit artefacts résiduels `~/.mempalace/`**
  Tour d'audit pur, sans fix. Cartographie ce qui traîne hors du
  palace actif (backups anciens, dossiers de migration, fichiers
  jetables). Sortie attendue : liste à trancher avec Nico.

### Candidats structurels (impact fort, effort élevé, sujets ouverts)

- **#17 — semantic wings non câblées**
  Sujet architectural, plusieurs sprints potentiels. Pertinent dans
  la vision long-terme (palace par utilisateur isolé). Pas adapté à
  un sprint exploratoire — nécessite cadrage préalable du contour.

### Candidats legacy (sans diagnostic préalable, effort inconnu)

- **#9, #10, #11, #13, #15, #16, #19, #23, #24** : dettes ouvertes
  héritées d'avant le sprint 6. Aucune n'a été touchée depuis. Audit
  préalable nécessaire avant de s'engager — risque que certaines soient
  obsolètes ou requalifiables.

- **#27 — chroma-hnswlib non pinné** : mineure, à traiter en bordure
  d'un sprint qui touche déjà au venv ou aux dépendances.

### Recommandation de premier message

> "Démarrage sprint 10 : choix de l'item prioritaire. Avant tout, peux-tu
> me proposer un classement des candidats listés au kickoff (opérationnels
> #22, #25, #26 / structurels #17 / legacy en bloc), et identifier celui
> que tu veux attaquer en premier ? Si l'arbitrage demande un audit
> préalable rapide sur une dette legacy pour la requalifier, on peut le
> programmer en tour 0 du sprint."

─────────────────────────────────────────────────────────────────────────

## Calibrage du niveau d'exigence (rappel)

Règle inchangée depuis sprint 8 : **fix qui marche + 1 test de
non-régression sur le cas nominal, rien de plus**. Pas de filets
spéculatifs, pas de mesure empirique sur dettes adjacentes en cours
de sprint, économies de soin par défaut.

Exception réactivée si l'item sélectionné touche au palace prod avec
contenu réel à préserver. À ce moment-là Nico le signale.

─────────────────────────────────────────────────────────────────────────

## Discipline acquise et à maintenir

Trois leçons opérationnelles du sprint 9 à préserver :

1. **Une métrique d'audit doit être discriminante.** Si elle peut
   donner le même résultat sous deux hypothèses contradictoires (ici
   "Python flush propre" vs "Python jamais appelé"), elle n'a pas
   tranché. Le tour T-Drift-HNSW-Metric a rattrapé ce trou — la
   prochaine fois, le détecter au tour d'audit initial.

2. **Une trace dans le `.pyi` ne signifie pas une couche active.**
   L'audit initial avait noté `chromadb_rust_bindings.pyi` comme
   "preuve d'une couche Rust" puis avait poursuivi la cartographie
   Python. Reflexe à instaurer : quand un `.pyi` Rust apparaît dans
   un produit Python, vérifier d'emblée quel chemin est actif en
   runtime, pas juste lequel est documenté.

3. **Pivot diagnostic en cours de sprint : OK si preuves
   convergentes.** Trois preuves indépendantes (pickle absent,
   monkey-patch silencieux, `_instances={}`) ont autorisé le pivot
   sans nouveau tour de validation. Si une seule preuve avait été
   présentée, on aurait demandé un tour court de re-validation.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel pour la nouvelle session

- Mettre à jour `main` si la fusion sprint 9 n'a pas encore été
  faite. Poser le tag `sprint-9`.
- Décider de la branche de travail en fonction de l'item retenu :
  - `feat/sprint10-cleanup-orphans` si #22
  - `feat/sprint10-smoke-runbook` si #25
  - `feat/sprint10-mempalace-audit` si #26
  - `feat/sprint10-semantic-wings` si #17 (cadrage)
  - `feat/sprint10-legacy-triage` si triage legacy

─────────────────────────────────────────────────────────────────────────