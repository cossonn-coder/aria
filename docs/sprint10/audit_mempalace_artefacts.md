# Audit `~/.mempalace/` — sprint 10, tour 0

**Date** : 2026-05-19
**Branche prévue** : `feat/sprint10-mempalace-hygiene` (à brancher depuis
`main` après merge `feat/sprint9-drift-hnsw` + tag `sprint-9`, cf.
§ « Préalable git » en fin de doc)
**Mode** : lecture seule, aucune mutation
**Service au moment de l'audit** : `aria.service` → `inactive`
**Périmètre** : `/home/nico/.mempalace/` — 64 Mo, 135 fichiers, 31 dossiers

---

## 1. Arborescence complète (profondeur 3, tailles cumulées)

```
[ 64M]  /home/nico/.mempalace/
├── [1.3K]  config.json
├── [4.6K]  locks
│   ├── [   0]  008a908c53eefb9c.lock                      (× 30 lock vides, avril 2026)
│   ├── [ 108]  mine_palace_5992fc0c8387c008.lock           ┐
│   ├── [  14]  mine_palace_671ead2dd4f4da06.lock           │
│   ├── [ 113]  mine_palace_799baf6231d33173.lock           │ 6 locks non-vides,
│   ├── [ 118]  mine_palace_aadb297be8739c5c.lock           │ mai 2026
│   ├── [ 107]  mine_palace_b1feffe876cbb4c8.lock           │
│   └── [ 107]  mine_palace_e42d996fe9e352d2.lock           ┘
├── [4.3M]  mempalace_drawers_backup_20260513T105601Z.tar.gz   (snapshot avant migration mpnet)
├── [4.3M]  mempalace_drawers_backup_20260517T195620Z.tar.gz   (snapshot préprod #1)
├── [4.4M]  mempalace_drawers_backup_20260518T074809Z.tar.gz   (snapshot préprod #2)
├── [9.7M]  palace                                              ← PALACE ACTIF
│   ├── [168K]  3b1fb30f-…drift-20260513-180821                 orphelin .drift-*
│   ├── [168K]  3b1fb30f-…drift-20260517-221838                 orphelin .drift-*
│   ├── [168K]  3b1fb30f-…drift-20260518-101422                 orphelin .drift-*
│   ├── [318K]  4462953f-2f2e-4df1-90de-40565b4b340b            segment HNSW actif (drawers mpnet)
│   ├── [168K]  b28198b8-e30f-472a-82bb-d30898e5cc5b            ⚠ segment HNSW non référencé sqlite
│   ├── [2.2M]  b28198b8-…corrupt-20260513-180821               orphelin .corrupt-*
│   ├── [168K]  b28198b8-…drift-20260517-221838                 orphelin .drift-*
│   ├── [6.4M]  chroma.sqlite3
│   ├── [   0]  .blob_seq_ids_migrated
│   ├── [  64]  .embedder-migration-marker
│   └── [  86]  .mempalace-embedder.json
├── [ 13M]  palace_backup_2026-04-22                            ← snapshot pré-sprint 8
│   ├── 3b1fb30f-… (168K)
│   ├── b28198b8-… (1.0M)
│   ├── chroma.sqlite3 (6.1M)
│   └── palace/                                                 ⚠ doublon imbriqué
│       ├── 3b1fb30f-…
│       ├── b28198b8-…
│       └── chroma.sqlite3 (6.1M, identique parent)
├── [9.1M]  palace.backup-pre-live-20260518T100943              ← snapshot juste avant bascule mpnet
│   ├── 3b1fb30f-…           (segment clean)
│   ├── 3b1fb30f-…drift-20260513-180821
│   ├── 3b1fb30f-…drift-20260517-221838
│   ├── b28198b8-…           (segment clean, ancien drawers MiniLM)
│   ├── b28198b8-…corrupt-20260513-180821
│   ├── b28198b8-…drift-20260517-221838
│   └── chroma.sqlite3 (6.1M, mempalace_drawers dim 384)
├── [9.2M]  palace_preprod_20260513T124229                      ← préprod #1 sprint 8
│   ├── 3b1fb30f-…           (closets HNSW)
│   ├── a3fcf705-…           (drawers mpnet HNSW, UUID préprod)
│   ├── b28198b8-…           ⚠ orphelin résiduel
│   └── chroma.sqlite3 (6.5M, mempalace_drawers dim 768)
└── [9.2M]  palace.rollback-failed-20260513T131824              ← rollback raté sprint 8
    ├── 3b1fb30f-…drift-20260514-070800
    ├── b28198b8-…corrupt-20260514-070800
    ├── d45f5f83-…drift-20260514-070800                         (drawers UUID éphémère)
    └── chroma.sqlite3 (6.5M, mempalace_drawers dim 768)
```

> Source brute : `tree -L 3 --du -h /home/nico/.mempalace/`.

---

## 2. Inventaire structuré par catégorie

### 2.1 Palace actif `~/.mempalace/palace/`

| Métrique                | Valeur                                                     |
|-------------------------|------------------------------------------------------------|
| Taille totale           | 9,7 Mo                                                     |
| `chroma.sqlite3`        | 6,4 Mo                                                     |
| WAL / SHM               | **ABSENT** (`chroma.sqlite3-wal`, `-shm` introuvables)     |
| `journal_mode`          | `delete` (PAS de WAL au repos, cohérent service stoppé)    |
| Collections sqlite      | 2 — `mempalace_drawers` (dim 768) + `mempalace_closets` (dim 384) |
| Embeddings total        | 770 (738 drawers + 32 closets)                             |
| Database / Tenant       | `default_database` / (table tenants présente, vide ?)      |
| Markers cachés          | `.blob_seq_ids_migrated`, `.embedder-migration-marker`, `.mempalace-embedder.json` |

**Mapping UUID → segment (sqlite vivant) :**

| Collection         | Dim | UUID collection                          | Segment HNSW                             | Segment metadata                         | Rows |
|--------------------|-----|------------------------------------------|------------------------------------------|------------------------------------------|------|
| `mempalace_drawers`  | 768 | `0756d591-4159-4f97-b151-9200ee02931a`   | `4462953f-2f2e-4df1-90de-40565b4b340b`   | `e60429a8-94f5-4ec6-adff-a20323e2f711`   | 738  |
| `mempalace_closets`  | 384 | `64d7d455-9793-4dd7-91fe-c983f2c4da93`   | `3b1fb30f-7da4-43f1-969e-f0b180ca92e3`   | `77f2d20c-7500-4092-9f41-fd00aac777aa`   | 32   |

**Anomalies notables :**

- Le segment HNSW de `mempalace_closets` (`3b1fb30f-…`) **n'a aucun
  dossier en clair** sur le disque — uniquement trois `.drift-*`. Le
  sqlite le déclare pourtant comme segment vector actif. C'est
  cohérent avec l'audit dette #20 (sprint 9) : la couche HNSW Python
  est dead code, le Rust ne (re)crée pas systématiquement le dossier
  pour une collection peu/jamais écrite. À documenter explicitement
  dans la dette #21.
- Le dossier `b28198b8-…` (sans suffixe) est présent en clair mais
  n'est référencé par **aucun segment** dans le sqlite actif. C'est
  un orphelin de migration sprint 8 : ancien segment HNSW de
  `mempalace_drawers` MiniLM 384, conservé sur disque après bascule
  mpnet (cohérent avec snapshot `palace.backup-pre-live` qui
  contient le même `b28198b8` lié à `mempalace_drawers` dim 384).

**Contenu des markers :**

```
.blob_seq_ids_migrated         : (vide, 0 bytes) — sentinel migration MemPalace
.embedder-migration-marker     : d7cf70785199882d043d8fd07a105fede4316e40d1a6184778bcc92118de4db8
.mempalace-embedder.json       : {"model": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2", "version": 1}
```

Le sha256 du marker correspond probablement à l'identifiant du modèle
mpnet (à confirmer par recoupement avec MemPalace fork, hors scope).
Le `.mempalace-embedder.json` est aligné avec la migration sprint 8.

---

### 2.2 Orphelins `.drift-*`

Cible exacte de la dette #22.

| Fichier(s)                                                      | Hôte                                | Taille |
|-----------------------------------------------------------------|-------------------------------------|--------|
| `palace/3b1fb30f-…drift-20260513-180821/`                        | palace actif                        | 168K   |
| `palace/3b1fb30f-…drift-20260517-221838/`                        | palace actif                        | 168K   |
| `palace/3b1fb30f-…drift-20260518-101422/`                        | palace actif                        | 168K   |
| `palace/b28198b8-…drift-20260517-221838/`                        | palace actif                        | 168K   |
| `palace.backup-pre-live-…/3b1fb30f-…drift-20260513-180821/`      | snapshot 18 mai 10:09               | 168K   |
| `palace.backup-pre-live-…/3b1fb30f-…drift-20260517-221838/`      | snapshot 18 mai 10:09               | 168K   |
| `palace.backup-pre-live-…/b28198b8-…drift-20260517-221838/`      | snapshot 18 mai 10:09               | 168K   |
| `palace.rollback-failed-…/3b1fb30f-…drift-20260514-070800/`      | snapshot rollback 14 mai            | 168K   |
| `palace.rollback-failed-…/d45f5f83-…drift-20260514-070800/`      | snapshot rollback 14 mai            | 318K   |

**Total `.drift-*`** : 9 dossiers, ~1,7 Mo cumulés. **4 dans le palace
actif** (les seuls dans le périmètre direct de #22), le reste dans des
snapshots.

**Origine** : le fork MemPalace renomme un dossier HNSW en `.drift-<TS>`
quand il détecte au démarrage que le count HNSW diffère du count sqlite
pour ce segment. Comportement bénin documenté sprint 9 (replay WAL
garantit que sqlite reste autoritaire). Statut : **orphelin** — aucun
code prod ne les relit.

**Distribution dans le temps** :

- `2026-05-13 18:08` : drift initial pendant la migration mpnet
  (rollback test)
- `2026-05-14 07:08` : drift sur le rollback raté
- `2026-05-17 22:18` : drift après bascule préprod #1
- `2026-05-18 10:14` : drift après bascule prod finale

Aucun `.drift-*` créé depuis le 18 mai 2026, ce qui confirme la
stabilité post-fix sprint 9.

---

### 2.3 Orphelins `.corrupt-*`

| Fichier                                                       | Hôte                          | Taille | Particularité                     |
|---------------------------------------------------------------|-------------------------------|--------|-----------------------------------|
| `palace/b28198b8-…corrupt-20260513-180821/`                    | palace actif                  | 2,2M   | contient `index_metadata.pickle` 42K |
| `palace.backup-pre-live-…/b28198b8-…corrupt-20260513-180821/`  | snapshot pré-bascule          | 2,2M   | idem                              |
| `palace.rollback-failed-…/b28198b8-…corrupt-20260514-070800/`  | snapshot rollback             | 2,2M   | idem                              |

**Total `.corrupt-*`** : 3 dossiers, ~6,6 Mo cumulés (essentiellement
`data_level0.bin` à 2,2 Mo chacun). **1 dans le palace actif**.

**Origine** : le fork MemPalace renomme un dossier HNSW en
`.corrupt-<TS>` quand il rencontre une exception au chargement (lecture
ratée du pickle / des bin headers). Contrairement aux `.drift-*`, ces
dossiers contiennent encore l'`index_metadata.pickle` original — c'est
la trace d'un segment HNSW MiniLM 384 qui n'a pas pu être réouvert
après bascule. Statut : **orphelin**.

---

### 2.4 Backups archivés

| Artefact                                                | Taille | Type      | Origine probable                                  | Statut          |
|---------------------------------------------------------|--------|-----------|---------------------------------------------------|-----------------|
| `mempalace_drawers_backup_20260513T105601Z.tar.gz`      | 4,3M   | tar.gz    | snapshot scripté pré-migration mpnet (13 mai)     | archive         |
| `mempalace_drawers_backup_20260517T195620Z.tar.gz`      | 4,3M   | tar.gz    | snapshot scripté préprod #1 (17 mai 21:54)        | archive         |
| `mempalace_drawers_backup_20260518T074809Z.tar.gz`      | 4,4M   | tar.gz    | snapshot scripté préprod #2 (18 mai 07:42)        | archive         |
| `palace_backup_2026-04-22/`                              | 15M    | directory | snapshot manuel d'avant sprint 8 (état MiniLM 384) | archive (avec doublon imbriqué `palace/`) |
| `palace.backup-pre-live-20260518T100943/`                | 9,1M   | directory | snapshot juste avant le bascule mpnet final       | archive         |
| `palace_preprod_20260513T124229/`                        | 9,2M   | directory | préprod #1 mpnet (13 mai 12:42)                   | archive         |
| `palace.rollback-failed-20260513T131824/`                | 9,2M   | directory | tentative de rollback ratée (13 mai 13:18)        | archive         |

**Contenu des tar.gz (croisement avec les dossiers en clair) :**

- `…20260513T105601Z.tar.gz` → racine `palace/` (14 entrées, état
  MiniLM avec b28198b8 clean). Distinct de `palace_backup_2026-04-22`
  qui est antérieur.
- `…20260517T195620Z.tar.gz` → racine `palace.preprod-20260517T215402/`
  (29 entrées). **Distinct** de `palace_preprod_20260513T124229/` —
  c'est un autre point dans le temps qui n'est pas représenté en
  clair sur disque.
- `…20260518T074809Z.tar.gz` → racine `palace.preprod2-20260518T074203/`
  (34 entrées). **Distinct** de `palace.backup-pre-live-…/`.

Conclusion : les 3 tar.gz et les 4 dossiers de backup en clair sont
**complémentaires** (points de capture différents), pas redondants.

**Doublon imbriqué interne :** `palace_backup_2026-04-22/palace/` est
une copie quasi-littérale du parent (mêmes UUID, même `chroma.sqlite3`
de 6,1 Mo). Probablement un `cp -r` lancé deux fois, ou un backup de
backup. Coût ≈ 6,1 Mo récupérables sans risque.

---

### 2.5 Dossiers de migration / versions antérieures

Aucun dossier nommé `palace_old`, `palace_v*` détecté. Les variantes
historiques sont toutes dans la rubrique « Backups » ci-dessus.

---

### 2.6 Locks `~/.mempalace/locks/`

| Catégorie                  | Count | Taille | mtime                  | Statut                                  |
|----------------------------|-------|--------|------------------------|-----------------------------------------|
| `*.lock` vides (0 bytes)   | 30    | 0      | 15 avril 11:56-12:01   | fantômes (locks orphelins ChromaDB 1.x ?) |
| `mine_palace_*.lock`       | 6     | 14-118 | 18-19 mai              | PIDs morts, contenu instructif          |

Contenu des locks non-vides (tous des PIDs qui ne tournent plus,
service `inactive`) :

```
mine_palace_5992fc0c8387c008.lock  → PID 359034  repro_drift.py runner no-close          (sprint 9)
mine_palace_671ead2dd4f4da06.lock  → PID 339570  bot.py                                   (dernier run prod 18 mai 14:42)
mine_palace_799baf6231d33173.lock  → PID 359232  repro_drift.py runner backend-close      (sprint 9)
mine_palace_aadb297be8739c5c.lock  → PID 359890  repro_drift.py runner persist-then-close (sprint 9)
mine_palace_b1feffe876cbb4c8.lock  → PID 360093  repro_drift.py runner sigterm            (sprint 9)
mine_palace_e42d996fe9e352d2.lock  → PID 360294  repho_drift.py runner sigkill            (sprint 9)
```

Origine : MemPalace fork inscrit un lock par instance (single-writer).
Le service prod et le harness sprint 9 ont chacun crashé/quitté sans
nettoyer leur lock — comportement attendu mais pas géré.

---

### 2.7 Logs / dumps résiduels

Aucun fichier `*.log`, `*.dump`, `*.json` (hors marker mempalace) ou
trace `__pycache__` détecté. Le périmètre est propre côté logging.

---

### 2.8 Autres

- `~/.mempalace/config.json` (1,3 Ko) au top niveau : config legacy
  MemPalace (`palace_path`, `topic_wings`, `hall_keywords`). **Non
  utilisé par ARIA** — `config.py` code-en-dur `mempalace_path =
  "/home/nico/.mempalace/palace"` et n'ouvre pas ce JSON. C'est
  probablement un reliquat de bootstrapping initial du fork
  MemPalace 3.x. Hypothèse à valider avec Nico.

---

## 3. Croisement avec le service vivant

### Procédure d'observation

Service redémarré (PID 364146), capture exécutée via
`/proc/<pid>/fd` + `/proc/<pid>/maps` + `lsof -p <pid>` :

```
=== /proc/364146/fd entries pointant sur mempalace ===
(aucun FD ouvert sur .mempalace/)

=== /proc/364146/maps mmap mempalace ===
(aucun mmap)

=== Total FDs ouverts par le process ===
9

=== systemd-cgls (espace mount partagé?) ===
mnt:[4026531841]   ← process bot.py
mnt:[4026531841]   ← session shell nico
(identiques → même namespace, lsof voit bien tout)
```

`lsof -p 364146` retourne 50 lignes de mappings (cwd, txt python,
weights huggingface mpnet, .so de cryptography/triton/sklearn/pandas)
mais **aucune** ne pointe sur `.mempalace/` ni sur `chroma`.

### Interprétation

**ChromaDB 1.5.5 (backend Rust) n'ouvre AUCUN FD persistant sur
`chroma.sqlite3`** : il ouvre la base à chaque requête et referme
immédiatement après. Cela se vérifie indirectement par trois signaux
convergents :

1. `journal_mode = delete` (pas WAL → pas de FD persistant attendu)
2. `chroma.sqlite3-wal` et `-shm` absents au repos
3. zéro FD `.mempalace/` dans `/proc/<pid>/fd` au repos

**Conséquence pour l'audit** :

- la méthode lsof live est **structurellement inutile** pour ce
  backend : on ne verra jamais un FD persistant, même sous charge,
  sauf à intercepter la fenêtre courte d'une requête en vol
  (`strace -e openat` serait nécessaire pour cela).
- les 6 `mine_palace_*.lock` non-vides sont définitivement **tous
  stale** : aucun n'est tenu par le PID 364146 actuel.
- aucun fichier de backup n'est tenu en lecture/écriture par le
  process vivant → toute suppression de backup est filesystem-safe
  côté concurrence.
- le namespace mount partagé confirme qu'il n'y a pas d'isolation
  systemd cachée — l'inventaire fs est cohérent avec ce que voit
  ARIA au runtime.

Cette propriété est elle-même une **petite découverte annexe** :
toute observation runtime du palace doit passer par strace ou par
instrumentation Python, jamais par lsof. À acter dans la prochaine
mise à jour du contexte d'opération palace si jugé utile.

---

## 4. Hypothèses d'origine pour les artefacts non identifiés

| Artefact                                                | Hypothèse                                                              | Confiance |
|---------------------------------------------------------|------------------------------------------------------------------------|-----------|
| `palace/b28198b8-…` (sans suffixe)                       | ancien segment HNSW de `mempalace_drawers` MiniLM 384, non purgé après bascule mpnet sprint 8 | haute (croisement avec `palace.backup-pre-live` confirme dim 384) |
| `palace/3b1fb30f-…` (clean ABSENT en clair)              | Rust HNSW ne (re)crée pas le dossier pour `mempalace_closets` peu/jamais écrit ; cohérent dette #20 sprint 9 | haute |
| `~/.mempalace/config.json` top niveau                    | bootstrap legacy MemPalace 3.x, non lu par ARIA                        | moyenne   |
| 30 locks vides d'avril 2026                              | locks orphelins ChromaDB pré-fork ou pré-sprint 6                      | moyenne   |
| `palace_backup_2026-04-22/palace/` (doublon imbriqué)    | erreur d'opérateur (cp -r exécuté deux fois ou backup d'un backup)     | haute     |
| `palace_preprod_20260513T124229/`                        | préprod #1 mpnet sprint 8 (collection drawers UUID `845a3673`)         | haute     |
| `palace.rollback-failed-20260513T131824/`                | tentative de rollback ratée du 13/14 mai sprint 8 (drawers UUID `b20ce96a`) | haute |
| `palace.backup-pre-live-20260518T100943/`                | snapshot pris juste avant le bascule mpnet final du 18 mai 10:09       | haute     |
| tar.gz `…20260517T195620Z` et `…20260518T074809Z`        | snapshots scriptés à des points distincts des dossiers en clair        | haute     |
| Lock `mine_palace_*` PIDs morts                          | non-nettoyés à l'arrêt brutal du service ou des harness sprint 9       | haute     |

---

## 5. Recommandations préliminaires (sans action)

> Listes pour validation au tour suivant. **Aucune suppression
> effectuée à ce stade.**

### Supprimable sans risque (hygiène pure, gain immédiat)

| Item                                                    | Gain    | Justification                                              |
|---------------------------------------------------------|---------|------------------------------------------------------------|
| 30 `*.lock` vides d'avril 2026 dans `locks/`            | 0 Ko    | aucune référence active, nettoyage cosmétique              |
| 6 `mine_palace_*.lock` non-vides dans `locks/`          | < 1 Ko  | PIDs morts, service `inactive`                             |
| `palace_backup_2026-04-22/palace/` (doublon imbriqué)   | ~6,1 Mo | copie littérale du parent, vérifiable par diff             |
| 5 `.drift-*` dans `palace/` (cible #22)                 | 840 Ko  | comportement bénin documenté sprint 9, sqlite autoritaire  |
| 1 `.corrupt-*` dans `palace/` (cible #22)               | 2,2 Mo  | ancien HNSW MiniLM non rechargeable, plus pertinent        |

Total estimé : **~9 Mo récupérés sur 64 Mo (≈14 %)**, sans toucher au
contenu utile.

### À confirmer avec Nico

| Item                                                    | Question                                                              |
|---------------------------------------------------------|------------------------------------------------------------------------|
| `palace/b28198b8-…` (sans suffixe)                       | Orphelin de migration sprint 8 — purger ou conserver comme trace ?     |
| `palace_backup_2026-04-22/` (au-delà du doublon)        | Snapshot pré-sprint 8 ; conserver ou archiver hors `~/.mempalace/` ?   |
| `palace.backup-pre-live-20260518T100943/`                | Filet juste avant bascule prod ; date limite de conservation ?         |
| `palace_preprod_20260513T124229/`                        | Préprod #1 ; redondant maintenant que la prod tourne stable ?          |
| `palace.rollback-failed-20260513T131824/`                | Tentative ratée ; valeur de référence vs encombrement ?                |
| 3 tar.gz `mempalace_drawers_backup_*.tar.gz` top niveau | Conserver sur place, archiver ailleurs (Nextcloud, etc.), ou expirer ? |
| `~/.mempalace/config.json` top niveau                    | Encore utilisé quelque part ? Sinon purger ou archiver ?               |

### À conserver

| Item                                                    | Raison                                                                |
|---------------------------------------------------------|------------------------------------------------------------------------|
| `palace/chroma.sqlite3`                                  | source de vérité, palace actif                                         |
| `palace/4462953f-…/`                                     | segment HNSW actif `mempalace_drawers` mpnet                           |
| `palace/.blob_seq_ids_migrated`                          | sentinel migration, attendu par MemPalace fork                         |
| `palace/.embedder-migration-marker`                      | garde-fou anti-régression d'embedder (sprint 8)                        |
| `palace/.mempalace-embedder.json`                        | declaration du modèle actif, lu au démarrage                           |

---

## 6. Zones d'incertitude

À signaler explicitement plutôt qu'à combler par hypothèse :

1. **Segment `3b1fb30f-…` non matérialisé sur disque.** Le sqlite le
   déclare comme segment vector actif de `mempalace_closets`, mais
   aucun dossier en clair n'existe — seuls trois `.drift-*`. Deux
   lectures possibles :
   - lecture A : Rust HNSW ne crée le dossier qu'à la première écriture
     post-démarrage, et `mempalace_closets` n'est plus jamais écrit
     depuis sprint 4 ;
   - lecture B : le dossier a été renommé en `.drift-*` à chaque
     démarrage successif sans que le Rust ait recréé un dossier clean.

   Les deux convergent avec l'audit sprint 9 (dead code Python HNSW),
   mais le mécanisme exact n'est pas vérifié filesystem-only. À
   trancher par lecture du fork MemPalace si on veut une réponse
   ferme — pas nécessaire pour décider d'une suppression.

2. **Marker `.embedder-migration-marker` = sha256(...).** Le contenu
   `d7cf70785199882d…` est probablement un hash du nom de modèle ou
   du fichier de poids mpnet, mais ce n'est pas vérifié. Hors scope
   de ce tour.

3. **Origine des 3 tar.gz top niveau.** Aucun script de backup
   identifié dans la repo (à confirmer par `grep -r mempalace_drawers_backup
   /home/nico/Nextcloud/projects/aria/` si Nico veut tracer). Les
   timestamps correspondent à des moments de bascule sprint 8, donc
   très probablement des sauvegardes manuelles ad hoc de Nico.

4. **Locks vides d'avril 2026.** Pas de mapping disponible entre les
   ID hexadécimaux 16 caractères et un process passé. Hypothèse :
   convention de MemPalace fork antérieure au prefix `mine_palace_`,
   non confirmée. Sans risque puisque service stoppé / fichiers vides.

5. **`config.json` top niveau** : aucun `import` ou `open()` trouvé
   dans `config.py`. Pourrait être lu indirectement par le fork
   MemPalace ; à vérifier par `grep -r '\.mempalace/config' …/MemPalace/`
   si on veut une réponse ferme avant de purger.

---

## 7. Préalable git pour exécuter le sprint 10

État au moment de l'audit (réel, pas celui du kickoff) :

- branche courante : `feat/sprint9-drift-hnsw`
- **PAS** mergée dans `main` (le kickoff l'annonce comme close, mais le
  merge n'a pas été poussé en local)
- tag `sprint-9` : **ABSENT**

Avant de pousser ce fichier d'audit dans une branche dédiée, il faut
trancher avec Nico :

1. Mergér `feat/sprint9-drift-hnsw` dans `main`, poser `sprint-9` sur
   le commit de clôture documentaire, brancher
   `feat/sprint10-mempalace-hygiene` depuis `main`.
2. OU laisser ce fichier sur la branche courante en provisoire et
   gérer le merge sprint 9 → main séparément.

Le brief du tour 0 dit explicitement « branche depuis main à jour sur
sprint-9 », donc option 1 est l'attendu. **Pas de commit dans ce tour**,
le fichier reste local jusqu'à arbitrage.
