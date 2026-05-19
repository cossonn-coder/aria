─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 11 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date** : 2026-05-19
**Branche de travail prévue** : à décider en ouverture de sprint
  selon l'item sélectionné en premier
**Tag de référence sortie sprint 10** : `sprint-10`
**État sprint 10** : CLOS. #22 close pour de vrai (purge en 2 temps
  avec preuve causale before/after au journal). #26 cartographie
  livrée + backlog d'items "à confirmer" non actionnés. 3,2 Mo
  récupérés sur palace prod (9,9 → 6,7 Mo).

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 10 (rappel synthétique)

- Cartographie complète de `~/.mempalace/` en 7 catégories
  (palace actif, orphelins .drift-*, orphelins .corrupt-*, backups,
  dossiers de migration, locks, autres). Documenté en
  `docs/sprint10/audit_mempalace_artefacts.md`, 449 lignes.
- Découverte structurelle chromadb-rust 1.5.5 : **aucun FD persistant
  sur `chroma.sqlite3`** au repos ni en service actif. `lsof` est
  structurellement aveugle pour ce backend ; toute observation
  runtime doit passer par `strace -e openat` ou instrumentation
  Python. Vérifié sur `/proc/<pid>/fd` et `/proc/<pid>/maps`.
- Mécanisme de régénération `.drift-*` prouvé puis résolu :
  un segment HNSW orphelin (dossier nommé `<UUID>` strict, non
  référencé par sqlite) déclenche un quarantine à chaque démarrage
  parce que le scan ChromaDB le trouve sans pouvoir le rattacher.
  Le purger arrête définitivement la régénération — vérifié par
  contraste tour 1 (segment laissé) → drift régénéré vs tour 2b
  (segment purgé) → silence radio.
- Pattern de fix validé : **audit léger → fix → test discriminant
  before/after**. La preuve causale impose que la même observation
  soit faite deux fois, une fois avec la source présente et une fois
  sans. Sans contre-exemple, on ne tranche pas.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-05-19

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
| 21 | Collection closets legacy dim 384                      | ouvert, atténué par fork — à acter sprint 11 (cf. backlog #26) |
| 22 | Orphelins `.drift-*` / `.corrupt-*` dans palace prod   | **RÉSOLUE sprint 10**           |
| 23 | (legacy)                                               | ouvert                          |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet      |
| 25 | Heredoc smoke runbook trop strict sur pattern ST       | ouvert                          |
| 26 | Artefacts résiduels `~/.mempalace/` à auditer          | **PARTIELLEMENT RÉSOLUE sprint 10** (cartographie OK, backlog "à confirmer" à reprendre) |
| 27 | `chroma-hnswlib` non pinné, traçabilité venv manquante | ouvert sprint 9, mineure        |

─────────────────────────────────────────────────────────────────────────

## Backlog résiduel #26 (items "à confirmer" non actionnés au sprint 10)

Liste depuis `docs/sprint10/audit_mempalace_artefacts.md` § 5
colonne "à confirmer avec Nico" :

- **3 tar.gz top niveau** dans `~/.mempalace/` (~13 Mo cumul) :
  `mempalace_drawers_backup_20260513T105601Z.tar.gz`,
  `…20260517T195620Z.tar.gz`, `…20260518T074809Z.tar.gz`. Snapshots
  scriptés à 3 points distincts de la migration sprint 8.
- **`palace_backup_2026-04-22/`** (15 Mo) — état pré-sprint 8
  MiniLM 384. Contient un doublon littéral imbriqué
  `palace_backup_2026-04-22/palace/` (6,1 Mo) classé "supprimable
  sans risque" au tour 0 mais hors-scope du tour 2b.
- **`palace_preprod_20260513T124229/`** (9,2 Mo) — préprod #1 mpnet
  sprint 8.
- **`palace.backup-pre-live-20260518T100943/`** (9,1 Mo) — snapshot
  juste avant le bascule mpnet final.
- **`palace.rollback-failed-20260513T131824/`** (9,2 Mo) — tentative
  de rollback ratée du 14 mai.
- **`~/.mempalace/config.json`** (1,3 Ko) — legacy MemPalace 3.x,
  non lu par ARIA.
- **36 locks dans `~/.mempalace/locks/`** : 30 `.lock` vides d'avril
  2026 + 6 `mine_palace_*.lock` stale (5 du repro_drift sprint 9 +
  1 de bot.py 18 mai). Classés "supprimable sans risque" au tour 0.
- **Segment closets HNSW `3b1fb30f-…`** absent en clair sur disque
  alors que référencé actif en sqlite — comportement structurel
  chromadb-rust à acter formellement dans la dette #21 documentation.

**Snapshots créés au sprint 10 et conservés** (à arbitrer en clôture
sprint 11 ou plus tard) :
- `palace_backup_pre_sprint10_20260519T052335Z.tar.gz` (5,2 Mo) —
  pré-tour 1
- `palace_backup_pre_sprint10_tour2b_20260519T085100Z.tar.gz`
  (3,7 Mo) — pré-tour 2b

─────────────────────────────────────────────────────────────────────────

## Cible sprint 11 : indéterminée à l'ouverture

### Candidats opérationnels (impact direct, effort bas/moyen)

- **#25 — heredoc smoke runbook trop strict sur pattern ST**
  Hérité du sprint 8. Fix probable à 2-3 lignes. Confort Nico
  sur les valides de fumée.

- **#26 backlog résiduel — purge backups validés**
  Itérer sur la liste ci-dessus avec arbitrage Nico item par item.
  Gain attendu : 12-15 Mo récupérables sans risque (doublon imbriqué
  + locks vides + tar.gz datés à expirer), plus arbitrage des
  snapshots de backup directorywise.

### Candidats structurels (impact fort, effort élevé)

- **#17 — semantic wings non câblées**
  Sujet architectural, plusieurs sprints potentiels. Nécessite
  cadrage préalable du contour. Pas adapté à un sprint exploratoire.

- **#21 — documentation du comportement chromadb-rust closets**
  Tour court de doc seule : acter dans le doc d'architecture (ou
  CLAUDE.md) que le segment HNSW d'une collection peu/jamais écrite
  n'a pas de dossier en clair sur disque, comportement structurel.
  Évite que le prochain audit redécouvre la même surprise.

### Candidats legacy (sans diagnostic préalable, effort inconnu)

- **#9, #10, #11, #13, #15, #16, #19, #23, #24** : dettes ouvertes
  héritées d'avant le sprint 6. Aucune n'a été touchée depuis.
  Possibilité de faire un tour de triage rapide pour requalifier
  ou fermer plusieurs en lot.
- **#27 — chroma-hnswlib non pinné** : mineure, à traiter en
  bordure d'un sprint qui touche déjà au venv ou aux dépendances.

### Recommandation de premier message

> "Démarrage sprint 11 : choix de l'item prioritaire. Avant tout,
> peux-tu me proposer un classement des candidats listés au kickoff
> (opérationnels #25 / backlog résiduel #26 / structurels #17, #21
> / legacy en bloc), et identifier celui que tu veux attaquer en
> premier ? Si la voie 'triage backlog #26 + #21 doc' te paraît
> bonne, on peut enchaîner les deux dans le même sprint."

─────────────────────────────────────────────────────────────────────────

## Calibrage du niveau d'exigence (rappel)

Règle inchangée depuis sprint 8 : **fix qui marche + 1 test de
non-régression sur le cas nominal, rien de plus**. Pas de filets
spéculatifs, économies de soin par défaut.

Exception réactivée si l'item sélectionné touche au palace prod avec
contenu réel à préserver. À ce moment-là Nico le signale.

─────────────────────────────────────────────────────────────────────────

## Discipline acquise et à maintenir

Trois leçons opérationnelles du sprint 10 à préserver :

1. **Test discriminant before/after avec preuve causale.** Le tour 1
   avait livré une purge "qui marche" (5 cibles supprimées, palace
   plus léger, service OK), mais le redémarrage immédiat a régénéré
   un nouveau `.drift-*`. Ce contre-exemple a forcé le tour 2b, qui
   a livré la preuve causale (drift régénéré = source présente ;
   drift absent = source purgée). Une validation positive seule
   n'aurait pas tranché. À reproduire pour tout fix qui touche un
   comportement systémique.

2. **Refus du mélange de scope malgré découverte adjacente.** Au
   milieu du tour 1, la régénération du drift a révélé un orphelin
   non prévu. Choix option A (commit immédiat de la purge prévue,
   second tour séparé pour la nouvelle découverte) plutôt que
   d'étendre le scope. Évite que deux problèmes se mélangent dans
   le même commit et garde le diagnostic lisible dans l'historique.

3. **Reconnaître l'outil structurellement inadéquat.** `lsof` était
   l'outil naturel pour répondre à "qu'est-ce qu'ARIA tient ouvert
   sur le palace", mais ChromaDB rust ne tient rien — l'outil
   répondait "rien" pour la mauvaise raison. Documenté dans l'audit
   pour ne pas répéter la tentative. Règle : quand un outil retourne
   un vide inattendu, vérifier d'abord s'il peut répondre à la
   question posée avant de conclure.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel pour la nouvelle session

- `main` à jour sur `sprint-10` (fait en clôture sprint 10).
- Décider de la branche de travail en fonction de l'item retenu :
  - `feat/sprint11-smoke-runbook` si #25
  - `feat/sprint11-mempalace-backup-cleanup` si purge backups #26
  - `feat/sprint11-closets-doc` si #21 doc seule
  - `feat/sprint11-legacy-triage` si triage legacy
  - `feat/sprint11-semantic-wings` si #17 (cadrage)

─────────────────────────────────────────────────────────────────────────
