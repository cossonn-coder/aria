─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 13 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date** : 2026-05-19
**Branche de travail prévue** : à décider en ouverture de sprint
  selon l'item sélectionné en premier
**Tag de référence sortie sprint 12** : `sprint-12`
**État sprint 12** : CLOS. #27 livré (pin
  `chroma-hnswlib==0.7.6` dans `requirements.txt`, commit
  `b32d39b`). #25 livré (audit `a0e8a34` + fix `0ebb00f` du
  pattern strict `"SentenceTransformer" in repr(ef)` → check
  `isinstance` sur `SentenceTransformerEmbeddingFunction`).
  Dettes #28 et #29 ouvertes (révélées par #27). Validation
  runtime du fix #25 due (#30 nouvelle).

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 12 (rappel synthétique)

- **#27 pin posé.** `chroma-hnswlib==0.7.6` ajouté dans
  `requirements.txt` section MEMORY LAYER, avec commentaire de
  traçabilité. La couche HNSW C++ critique du palace est
  désormais épinglée — une réinstallation du venv ne peut plus
  embarquer silencieusement une version différente. Source
  PyPI confirmée, version cohérente avec sprint 9
  `audit_drift_hnsw_metric.md`.
- **#25 audit + fix.** L'audit `docs/sprint12/audit_heredoc_smoke_pattern.md`
  a montré que le pattern strict `"SentenceTransformer" in repr(ef)`
  du smoke runbook (`docs/sprint7/runbook_t_mempalace_live.md`
  § 6) échouait à cause du subclass tactique `_MempalaceST`
  (`mempalace/embedding.py:145`) dont le `repr()` ne contient
  pas la sous-chaîne attendue. Le fix remplace par
  `isinstance(ef, SentenceTransformerEmbeddingFunction)` — check
  sémantique sur la lignée d'héritage, robuste à tout subclass
  présent ou futur. Le pattern était mauvais **dès le départ**,
  pas devenu obsolète : asymétrie d'information entre l'auteur
  du runbook et le fork qui subclass. **Run live du smoke
  runbook section 6 dû** par Nico pour confirmer le fix en
  conditions réelles (dette #30 ci-dessous).
- **Convention `docs/architecture/` inaugurée au sprint 11
  désormais en place.** Pas d'ajout sprint 12, mais le critère
  d'admission est consultable (sujet structurel stable,
  non lié à un sprint particulier, qui mérite d'être trouvé
  sans avoir à fouiller les sprints clos). Disponible pour
  les futures docs structurelles (couches mémoire logiques,
  dispatcher, etc.).

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-05-19 (post sprint 12)

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
| 21 | Doc structurelle chromadb palace closets               | RÉSOLUE sprint 11               |
| 22 | Orphelins `.drift-*` / `.corrupt-*` dans palace prod   | RÉSOLUE sprint 10               |
| 23 | (legacy)                                               | ouvert                          |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet      |
| 25 | Heredoc smoke runbook trop strict sur pattern ST       | **RÉSOLUE sprint 12 (validation runtime due — voir #30)** |
| 26 | Artefacts résiduels `~/.mempalace/` à auditer          | PARTIELLEMENT RÉSOLUE sprint 10 (backlog "à confirmer" à reprendre) |
| 27 | `chroma-hnswlib` non pinné, traçabilité venv manquante | **RÉSOLUE sprint 12**           |
| 28 | Pin `mempalace==3.3.0` (requirements.txt) désaligné du venv editable (3.3.5, fork `feat/configurable-embedder`) | **ouvert sprint 12, candidat sprint 13** |
| 29 | Path venv `/home/nico/projects/aria/venv/` versus repo `/home/nico/Nextcloud/projects/aria/` (probable symlink filesystem) | ouvert sprint 12, mineure       |
| 30 | Validation runtime du fix smoke pattern ST (#25)       | due, en attente Nico            |

─────────────────────────────────────────────────────────────────────────

## Backlog résiduel #26 (toujours en attente d'arbitrage Nico)

Inchangé par rapport au kickoff sprint 12 — items "à confirmer"
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

## Cible sprint 13 : indéterminée à l'ouverture

### Candidats opérationnels (impact direct, effort bas/moyen)

- **#28 — pin `mempalace` désaligné du venv editable**
  Le plus exposé : un `pip install -r requirements.txt` réel
  rétrograderait mempalace de 3.3.5 (fork editable) vers 3.3.0 et
  casserait le palace. Trois pistes d'arbitrage cf. note de
  clôture kickoff sprint 12. Piège silencieux, candidat évident.

- **#30 — validation runtime du fix smoke pattern ST (#25)**
  Exécuter le heredoc section 6 du runbook
  `docs/sprint7/runbook_t_mempalace_live.md` en conditions
  réelles (palace prod ou pré-prod snapshot) pour confirmer
  l'assert `isinstance` passe. Effort très bas si pré-prod
  disponible. À enchaîner avec #28 ou faire avant selon
  préférence.

- **#29 — path venv anormal**
  Mineur. `pip show` rapporte `/home/nico/projects/aria/venv/`
  alors que repo est `/home/nico/Nextcloud/projects/aria/`.
  Probable symlink filesystem. Investigation 5 minutes,
  documentation à acter si symlink confirmé.

- **#26 backlog résiduel — purge backups validés**
  Itérer sur la liste ci-dessus avec arbitrage Nico item par item.
  Gain attendu : ~12-15 Mo récupérables sans risque + arbitrage
  des snapshots de backup directorywise.

### Candidats structurels (impact fort, effort élevé)

- **#17 — semantic wings non câblées**
  Sujet architectural, plusieurs sprints potentiels. Nécessite
  cadrage préalable du contour. Pas adapté à un sprint
  exploratoire.

- **Doc additionnelle `docs/architecture/`** maintenant que la
  convention est posée. Candidats : couches mémoire logiques
  (wings/rooms), dispatcher, contrats memory/writer.py. Aucun
  n'est pressé.

### Candidats legacy (sans diagnostic préalable, effort inconnu)

- **#9, #10, #11, #13, #15, #16, #19, #23, #24** : dettes ouvertes
  héritées d'avant le sprint 6. Aucune n'a été touchée depuis.
  Possibilité de faire un tour de triage rapide pour requalifier
  ou fermer plusieurs en lot.

### Recommandation de premier message

> "Démarrage sprint 13 : choix de l'item prioritaire. Candidat
> évident #28 (pin mempalace désaligné, piège silencieux) ; #30
> (validation runtime du fix smoke #25) peut s'enchaîner ou se
> faire avant. Backlog #26 purge backups toujours ouvert. Tu me
> donnes ta préférence ?"

─────────────────────────────────────────────────────────────────────────

## Calibrage du niveau d'exigence (rappel)

Inchangé depuis sprint 8 : **fix qui marche + 1 test de non-régression
sur le cas nominal, rien de plus**. Pas de filets spéculatifs,
économies de soin par défaut.

Exception réactivée si l'item sélectionné touche au palace prod
avec contenu réel à préserver. À ce moment-là Nico le signale.

─────────────────────────────────────────────────────────────────────────

## Discipline acquise et à maintenir

Quatre leçons préservées des sprints 10-12 :

1. **Test discriminant before/after avec preuve causale** — pour
   tout fix qui touche un comportement systémique. Cf. sprint 10
   tour 2b (preuve causale orphelin → drift).
2. **Refus du mélange de scope malgré découverte adjacente** —
   sprint 11 tour 2 : verdict C émergent documenté en §5 sans
   dérouler l'investigation. À reproduire.
3. **Reconnaître l'outil structurellement inadéquat** — `lsof`
   sur chromadb-rust = vide-par-construction, pas verdict
   d'inactivité. Cf. `docs/architecture/chromadb_palace.md`
   § Propriété observable.
4. **Brief atomique = un objectif, un livrable.** Le tour pin
   #27 a déclenché la chaîne « merge + clôture sprint 11 + tag »
   alors que le brief ne portait que sur le pin. Bonne foi de
   Claude Code (il a signalé le séquençage avant d'agir), mais
   le kickoff sprint 12 a été créé sans validation préalable de
   son contenu — d'où l'amend nécessaire. À l'avenir : un brief
   « débloque le séquençage git » et un brief « rédige le
   kickoff » sont deux items distincts.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel pour la nouvelle session

- `main` à jour sur `sprint-12` (fait en clôture sprint 12 — ce
  commit).
- Décider de la branche de travail en fonction de l'item retenu :
  - `feat/sprint13-mempalace-pin-coherent` si #28
  - `feat/sprint13-smoke-validation-run` si #30
  - `feat/sprint13-venv-path` si #29
  - `feat/sprint13-mempalace-backup-cleanup` si purge backups #26
  - `feat/sprint13-legacy-triage` si triage legacy
  - `feat/sprint13-semantic-wings` si #17 (cadrage)

─────────────────────────────────────────────────────────────────────────
