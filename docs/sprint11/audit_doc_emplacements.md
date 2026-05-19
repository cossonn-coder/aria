# Sprint 11 — Item #21 — Tour 1 : audit des emplacements documentaires

**Date** : 2026-05-19
**Branche** : `feat/sprint11-closets-doc` (créée depuis `main` @ tag
`sprint-10`, HEAD `323f45b`)
**Mode** : lecture seule, aucune mutation de fichier hors ce livrable
**Objectif** : décider **où** placer la doc structurelle palace
ChromaDB-rust (closets / segments HNSW / `.drift-*` / `.corrupt-*`)
qui doit naître au tour 2.

---

## Section 1 — Inventaire des sources documentaires candidates

### 1.1 Méthodologie

Trois passes :

1. `find . -type f \( -name "*.md" -o -name "*.rst" \) -not -path "./.git/*"
   -not -path "./node_modules/*" -not -path "./venv*/*" | sort` →
   38 fichiers `.md`, 0 `.rst`. Aucun dossier `docs/architecture/`,
   `docs/reference/`, `docs/palace/` n'existe.
2. `tree -L 2 docs/` (équivalent `find docs -maxdepth 2 -type d`)
   confirme l'arborescence sprint-only : `docs/backlog/`,
   `docs/sprint4..11/`. Pas de dossier pérenne hors-sprint.
3. Filtrage par grep des mots-clés (`chromadb|chroma-rust|closets|
   wardrobes|segment|hnsw|.drift|.corrupt|mempalace`, casse insensible)
   → 32 fichiers `.md` retiennent au moins un hit, dont 30 dans
   `docs/`, plus `CLAUDE.md` et `README.md` à la racine.

L'inventaire ci-dessous ne retient que les fichiers qui *pourraient
crédiblement héberger* la doc visée — soit parce qu'ils sont pérennes
(non liés à un sprint terminé), soit parce qu'ils traitent
structurellement du sujet. Les fichiers sprint kickoff/decision/cleanup
qui mentionnent `mempalace` en passant sont écartés ici (revus en §2
si du contenu structurel y apparaît).

### 1.2 Candidats pérennes (hors-sprint)

| Chemin | Lignes | Dernière modif | Portée déclarée (citation) |
|---|---:|---|---|
| `CLAUDE.md` | 262 | 2026-05-13 17:41 | « ARIA — Contexte projet pour Claude Code. Vision : Kernel cognitif personnel local. Single-user (Nico). Pas un chatbot — un runtime cognitif avec mémoire persistante, intents, et routing dynamique vers des effecteurs spécialisés. » |
| `README.md` | 124 | 2026-04-22 16:19 | « ARIA — Cognitive Kernel Assistant. ARIA est un système d'agent cognitif personnel basé sur : un kernel central d'orchestration, un système d'intentions persistantes, une mémoire vectorielle (MemPalace)… » |
| `soul.md` | 28 | 2026-04-22 12:37 | (lecture seule, hors scope — interdit par CLAUDE.md) |
| `user.md` | 6 | 2026-04-22 12:37 | Métadonnées user, hors sujet structurel |

### 1.3 Candidats datés (sprint-scoped) avec contenu structurel

| Chemin | Lignes | Dernière modif | Portée déclarée (citation) |
|---|---:|---|---|
| `docs/sprint4/audit_memory_layer.md` | 200 | 2026-05-07 21:23 | « Audit couche mémoire — ARIA Sprint 4. Cartographie des points d'accès mémoire dans ARIA. » |
| `docs/sprint6/runbook_t_embedder3.md` | 324 | 2026-05-13 12:40 | « Runbook T-Embedder3 — Migration embedder live prod. Exécution prod : copie pré-prod, arrêt ARIA, migration `~/.mempalace/palace/`, bascule `EMBEDDING_MODEL`. » |
| `docs/sprint6/plan_migration_embedder.md` | 296 | 2026-05-10 14:48 | Plan détaillé migration embedder — sprint 6, archivé |
| `docs/sprint7/runbook_t_mempalace_live.md` | 749 | 2026-05-18 14:59 | « Runbook T-Mempalace-Live — Migration palace prod sous fork MemPalace. Sprint 7 / phase 2. Migration du palace ARIA de `all-MiniLM-L6-v2` (dim 384) vers `paraphrase-multilingual-mpnet-base-v2` (dim 768). » |
| `docs/sprint9/audit_drift_hnsw.md` | 725 | 2026-05-18 15:21 | « T-Drift-HNSW-Audit — Cartographie de la fermeture palace. Sprint 9 / cible dette #20. Statut : audit pur, aucun fix appliqué. » |
| `docs/sprint9/audit_drift_hnsw_metric.md` | 183 | 2026-05-19 06:01 | « T-Drift-HNSW-Metric — Instrumentation discriminante de la repro. Sprint 9 — complément de `audit_drift_hnsw.md`. » |
| `docs/sprint10/audit_mempalace_artefacts.md` | 449 | 2026-05-19 08:21 | « Audit `~/.mempalace/` — sprint 10, tour 0. Périmètre : `/home/nico/.mempalace/` — 64 Mo, 135 fichiers, 31 dossiers. » |
| `docs/sprint10/context_sprint_10_kickoff.md` | 156 | 2026-05-19 06:31 | Kickoff sprint 10 (hygiène palace) |
| `docs/sprint11/context_sprint_11_kickoff.md` | 199 | 2026-05-19 11:09 | Kickoff sprint 11 (item #21 inclus) |

### 1.4 Arborescence `docs/` (profondeur 2)

```
docs/
├── backlog/        (1 fichier brouillon — pas un emplacement pérenne)
├── sprint4/        artefacts sprint 4 close
├── sprint5/        artefacts sprint 5 close
├── sprint6/        artefacts sprint 6 close (T-Embedder3)
├── sprint7/        artefacts sprint 7 close (T-Mempalace-Live)
├── sprint8/        artefacts sprint 8 close
├── sprint9/        artefacts sprint 9 close (T-Drift-HNSW)
├── sprint10/       artefacts sprint 10 close (hygiène palace)
└── sprint11/       sprint courant
```

**Observation structurelle majeure** : la repo ne possède **aucun
dossier de doc pérenne hors-sprint** (pas de `docs/architecture/`,
pas de `docs/reference/`, pas de `docs/runbooks/`). Toute la doc
non-projet vit dans des silos sprint-scoped. La seule doc pérenne
hors `docs/` est `CLAUDE.md` (instructions Claude Code) et
`README.md` (overview projet). Ce constat conditionne directement
la recommandation de la §4.

---

## Section 2 — Doc préexistante sur le palace / ChromaDB / segments

### 2.1 Comptage par fichier (mots-clés thématiques)

Pour chaque candidat, deux comptes :
- `total` : hits sur l'union des mots-clés du brief
- `structurel` : hits sur le sous-ensemble pertinent pour #21
  (`closets|segment|HNSW|.drift|.corrupt`)

| Fichier | total | structurel |
|---|---:|---:|
| `CLAUDE.md` | 5 | 1 |
| `README.md` | 4 | 0 |
| `docs/sprint4/audit_memory_layer.md` | 46 | 4 |
| `docs/sprint6/plan_migration_embedder.md` | 28 | 0 |
| `docs/sprint6/runbook_t_embedder3.md` | 26 | 0 |
| `docs/sprint7/runbook_t_mempalace_live.md` | 94 | 3 |
| `docs/sprint9/audit_drift_hnsw.md` | 114 | **66** |
| `docs/sprint9/audit_drift_hnsw_metric.md` | 43 | **32** |
| `docs/sprint10/audit_mempalace_artefacts.md` | 100 | **49** |
| `docs/sprint10/context_sprint_10_kickoff.md` | 18 | 11 |
| `docs/sprint11/context_sprint_11_kickoff.md` | 28 | 15 |

**Lecture** : la doc structurelle réelle vit dans **trois fichiers
seulement** — les deux audits sprint 9 (mécanisme de close / persist
HNSW) et l'audit sprint 10 (artefacts filesystem). Les runbooks
sprint 6/7 mentionnent `mempalace` 90+ fois mais quasi-uniquement
dans un contexte procédural de migration (`~/.mempalace/palace/`
comme chemin de destination), sans description structurelle.

### 2.2 Extraits structurels par fichier

#### `CLAUDE.md` — unique hit structurel

```
53  - `aria` (legacy) : 0 entrée dans `mempalace_drawers`. 32 entrées
54    résiduelles dans `mempalace_closets` non migrées (hors scope
55    sprint 4, à arbitrer si un usage justifie leur migration).
```

Mention factuelle, alignée avec sprint 10 (32 closets). Ne décrit
ni le mécanisme HNSW, ni les artefacts `.drift-*` / `.corrupt-*`.
La section « Couches mémoire » de `CLAUDE.md` (lignes 30-58) est
**logique** (aria_episodic / aria_semantic / aria_classifier /
aria_intentual / aria legacy) et ne touche pas au layout
filesystem. Pas de conflit avec ce que #21 doit dire — mais pas
de point d'ancrage non plus.

#### `README.md` — 4 mentions, 0 structurel

```
7   - une mémoire vectorielle (MemPalace)
33  Memory Layer (MemPalace)
46  - ChromaDB (MemPalace)
93  MemPalace : mémoire vectorielle locale
```

Surface seule. README ne décrit ni la structure interne ni le
backend Rust.

#### `docs/sprint7/runbook_t_mempalace_live.md` — 3 hits structurels

```
304   1. Le palace s'ouvre **sans crash**, sans quarantine de segment
305      HNSW (le crash sprint 6 quarantained 3 segments, cf.
306      `docs/sprint7/context_sprint_7_T-Mempalace-Live_kickoff.md`).
...
431   - Crash chromadb / segment HNSW quarantained dans la stacktrace
432     → palace corrompu, le backup rsync de la section 3 est le
433     filet. **En prod : section R immédiatement.**
```

Le runbook **mentionne** le mécanisme de quarantine (=
`.corrupt-*`) mais comme un **événement à éviter** dans une
procédure, pas comme un comportement structurel à expliquer.
Aucune description du nommage `.corrupt-<TS>` ni du déclenchement.

#### `docs/sprint9/audit_drift_hnsw.md` — fort signal (66 structurels)

Section §2 « Cartographie ChromaDB upstream » lignes 177-353 :
dissection détaillée de `chromadb/segment/impl/vector/local_persistent_hnsw.py`
(méthodes `stop`, `_persist`, `_apply_batch`, seuil `sync_threshold`).

Extrait clé (lignes 246-260) :

```
246  #### `chromadb/segment/impl/vector/local_persistent_hnsw.py:536-543` — **POINT CRITIQUE**
...
260  🚨 **Le `stop()` du segment HNSW persistent ferme uniquement les
       file handles via `close_persistent_index()`, n'appelle PAS `_persist()`.**
```

⚠ **Doc partiellement obsolète** : ce passage décrit le chemin
Python du segment manager, **invalidé par le complément
`audit_drift_hnsw_metric.md`** qui démontre que ce code est mort
en chromadb 1.5.5 (api = `RustBindingsAPI`). Cf. §2.3 ci-dessous.

#### `docs/sprint9/audit_drift_hnsw_metric.md` — pivot Rust (32 structurels)

```
12   La métrique enrichie pivote le diagnostic. **`PersistentLocalHnswSegment._persist()`
13   (Python) n'est appelé par AUCUNE des 7 méthodes** — non pas parce qu'elles
14   oublient de le faire, mais parce que **le code Python est mort code en
15   chromadb 1.5.5**. L'API par défaut depuis 1.5.x est `RustBindingsAPI`
16   (`chromadb/config.py:120`), qui route tous les writes via
17   `chromadb_rust_bindings.Bindings.add/upsert/...` directement vers la couche
18   Rust native. Le segment manager Python `LocalSegmentManager` n'est jamais
19   exercé : `_instances` reste vide après 51 add() (mesuré).
```

C'est **la** référence pour comprendre que le palace tourne sur
chromadb-rust en pratique. Le fichier ne décrit pas les artefacts
filesystem (`.drift-*`, `.corrupt-*`, dossier segment absent) — ce
sera précisément l'apport de #21.

#### `docs/sprint10/audit_mempalace_artefacts.md` — source primaire (49 structurels)

Voir §3 ci-dessous pour la lecture intégrale et les trois extraits
textuels.

#### Autres : `sprint10/context_sprint_10_kickoff.md` & `sprint11/context_sprint_11_kickoff.md`

Mentions de `.drift-*` / `.corrupt-*` dans le contexte de la dette
#22 (purge orphelins) et de l'item #21 lui-même. Pas de description
structurelle — ce sont des kickoffs qui *pointent vers* la doc à
écrire.

### 2.3 Inconsistance interne signalée (point de vigilance brief)

`docs/sprint9/audit_drift_hnsw.md` §2 décrit le segment manager
Python comme path actif ; `docs/sprint9/audit_drift_hnsw_metric.md`
§TL;DR le marque comme dead code. Le second fichier est explicite
sur l'invalidation (« `audit_drift_hnsw.md` §2 a disséqué un chemin
obsolète »). Cette inconsistance est **intra-sprint 9, déjà
documentée par les auteurs**, pas une contradiction avec le
sprint 10. La doc #21 (tour 2) devra référencer le `_metric` comme
source d'autorité, pas le premier audit.

Aucune autre contradiction avec ce que le sprint 10 a observé
(notamment : pas de doc affirmant que chromadb tiendrait un FD
persistant sur `chroma.sqlite3` — l'absence de FD n'est tout
simplement **jamais mentionnée** ailleurs que dans le sprint 10).

---

## Section 3 — Lecture intégrale de `docs/sprint10/audit_mempalace_artefacts.md`

### 3.1 Présence et taille

Fichier présent : `docs/sprint10/audit_mempalace_artefacts.md`
**449 lignes** (cohérent avec annonce `wc -l`).
Dernière modif git : 2026-05-19 08:21:37 +0200.

### 3.2 Table des sections

| Plage   | Titre |
|---------|-------|
| L1-11   | en-tête (date, branche, mode, périmètre) |
| L13-71  | `## 1. Arborescence complète (profondeur 3, tailles cumulées)` |
| L73-265 | `## 2. Inventaire structuré par catégorie` |
| L75-122 | `### 2.1 Palace actif ~/.mempalace/palace/` |
| L125-160| `### 2.2 Orphelins .drift-*` |
| L164-180| `### 2.3 Orphelins .corrupt-*` |
| L184-214| `### 2.4 Backups archivés` |
| L218-221| `### 2.5 Dossiers de migration / versions antérieures` |
| L225-246| `### 2.6 Locks ~/.mempalace/locks/` |
| L250-253| `### 2.7 Logs / dumps résiduels` |
| L257-264| `### 2.8 Autres` |
| L268-325| `## 3. Croisement avec le service vivant` |
| L270-293| `### Procédure d'observation` |
| L295-325| `### Interprétation` |
| L328-342| `## 4. Hypothèses d'origine pour les artefacts non identifiés` |
| L345-384| `## 5. Recommandations préliminaires (sans action)` |
| L387-426| `## 6. Zones d'incertitude` |
| L429-449| `## 7. Préalable git pour exécuter le sprint 10` |

### 3.3 Extraits textuels (matière première pour #21)

#### a) Mécanisme de régénération `.drift-*` lié au segment orphelin

§2.2 lignes 145-149 — **origine du nommage** :

> **Origine** : le fork MemPalace renomme un dossier HNSW en
> `.drift-<TS>` quand il détecte au démarrage que le count HNSW
> diffère du count sqlite pour ce segment. Comportement bénin
> documenté sprint 9 (replay WAL garantit que sqlite reste
> autoritaire). Statut : **orphelin** — aucun code prod ne les relit.

§6.1 lignes 391-404 — **les deux lectures possibles du mécanisme** :

> 1. **Segment `3b1fb30f-…` non matérialisé sur disque.** Le sqlite le
>    déclare comme segment vector actif de `mempalace_closets`, mais
>    aucun dossier en clair n'existe — seuls trois `.drift-*`. Deux
>    lectures possibles :
>    - lecture A : Rust HNSW ne crée le dossier qu'à la première écriture
>      post-démarrage, et `mempalace_closets` n'est plus jamais écrit
>      depuis sprint 4 ;
>    - lecture B : le dossier a été renommé en `.drift-*` à chaque
>      démarrage successif sans que le Rust ait recréé un dossier clean.
>
>    Les deux convergent avec l'audit sprint 9 (dead code Python HNSW),
>    mais le mécanisme exact n'est pas vérifié filesystem-only. À
>    trancher par lecture du fork MemPalace si on veut une réponse
>    ferme — pas nécessaire pour décider d'une suppression.

§2.3 lignes 175-180 — **origine `.corrupt-*` (parallèle structurel)** :

> **Origine** : le fork MemPalace renomme un dossier HNSW en
> `.corrupt-<TS>` quand il rencontre une exception au chargement (lecture
> ratée du pickle / des bin headers). Contrairement aux `.drift-*`, ces
> dossiers contiennent encore l'`index_metadata.pickle` original — c'est
> la trace d'un segment HNSW MiniLM 384 qui n'a pas pu être réouvert
> après bascule.

#### b) Absence de FD persistant sur `chroma.sqlite3` (lsof aveugle)

§3 « Croisement avec le service vivant », interprétation lignes
295-324 — **passage central** :

> **ChromaDB 1.5.5 (backend Rust) n'ouvre AUCUN FD persistant sur
> `chroma.sqlite3`** : il ouvre la base à chaque requête et referme
> immédiatement après. Cela se vérifie indirectement par trois signaux
> convergents :
>
> 1. `journal_mode = delete` (pas WAL → pas de FD persistant attendu)
> 2. `chroma.sqlite3-wal` et `-shm` absents au repos
> 3. zéro FD `.mempalace/` dans `/proc/<pid>/fd` au repos
>
> **Conséquence pour l'audit** :
>
> - la méthode lsof live est **structurellement inutile** pour ce
>   backend : on ne verra jamais un FD persistant, même sous charge,
>   sauf à intercepter la fenêtre courte d'une requête en vol
>   (`strace -e openat` serait nécessaire pour cela).
> [...]
>
> Cette propriété est elle-même une **petite découverte annexe** :
> toute observation runtime du palace doit passer par strace ou par
> instrumentation Python, jamais par lsof. À acter dans la prochaine
> mise à jour du contexte d'opération palace si jugé utile.

La dernière phrase est un appel explicite à doc pérenne — cette
propriété est l'un des trois acquis qui doivent migrer vers #21.

#### c) Absence de dossier en clair pour `3b1fb30f-…` malgré référence sqlite active

§2.1 lignes 97-103 — **constat brut** :

> - Le segment HNSW de `mempalace_closets` (`3b1fb30f-…`) **n'a aucun
>   dossier en clair** sur le disque — uniquement trois `.drift-*`. Le
>   sqlite le déclare pourtant comme segment vector actif. C'est
>   cohérent avec l'audit dette #20 (sprint 9) : la couche HNSW Python
>   est dead code, le Rust ne (re)crée pas systématiquement le dossier
>   pour une collection peu/jamais écrite. À documenter explicitement
>   dans la dette #21.

§4 ligne 333 — **hypothèse haute confiance** :

> | `palace/3b1fb30f-…` (clean ABSENT en clair) | Rust HNSW ne (re)crée pas le dossier pour `mempalace_closets` peu/jamais écrit ; cohérent dette #20 sprint 9 | haute |

Ces trois extraits forment le triptyque structurel à documenter au
tour 2. L'audit sprint 10 a explicitement « renvoyé vers #21 » la
charge documentaire (cf. citation §2.1 : « À documenter explicitement
dans la dette #21 »).

---

## Section 4 — Recommandation de placement

### 4.1 Options évaluées

#### Option A — Nouveau fichier `docs/architecture/chromadb_palace.md`

- **Pour** :
  - Le sujet (layout filesystem stable, comportement chromadb-rust
    upstream, mécanismes `.drift-*`/`.corrupt-*`) est *structurel et
    pérenne*. Il ne se périme pas au merge d'un sprint — au contraire,
    il deviendra le point de référence cité par les futurs audits.
  - Crée un dossier `docs/architecture/` qui **manque** (cf. §1.4).
    Ce dossier deviendra une convention saine pour les futures docs
    structurelles (couches mémoire, dispatcher, etc.) qui aujourd'hui
    n'ont pas de foyer.
  - Aucun conflit avec doc existante. Le fichier est neuf.
  - Permet un cross-link clair depuis :
    `CLAUDE.md` (section « Couches mémoire ») → ancrage
    `docs/sprint9/audit_drift_hnsw_metric.md` → référence canonique
    `docs/sprint10/audit_mempalace_artefacts.md` § 2.1, 2.2, 3, 6.1 →
    « pour le mécanisme structurel pérenne, voir … »
- **Contre** :
  - Inaugure un dossier (`docs/architecture/`) — coût zéro mais
    convention nouvelle à respecter ensuite.
- **Conflit éventuel** : aucun.

#### Option B — Section ajoutée à `CLAUDE.md`

- **Pour** :
  - `CLAUDE.md` est pérenne et déjà chargé dans le contexte Claude
    Code à chaque session. La section « Couches mémoire » mentionne
    déjà drawers/closets/classifier/intentual/legacy.
- **Contre** :
  - `CLAUDE.md` a un rôle **d'instructions Claude** (règles
    inviolables, protocole DeepSeek, conventions de tagging) — pas
    de description technique profonde de backend. Ajouter 80-150
    lignes sur le comportement chromadb-rust étoufferait la
    densité d'instructions du fichier (déjà 262 lignes).
  - La section « Couches mémoire » actuelle décrit la
    **taxinomie logique** (wings), pas le **layout filesystem**.
    Mélanger les deux brouille l'utilité de la section.
- **Conflit éventuel** : pas frontal, mais désalignement de
  registre (instructions vs description structurelle).

#### Option C — Section ajoutée à `README.md`

- **Pour** : pérenne, visible.
- **Contre** : `README.md` est un *overview projet* (philosophie,
  arborescence, intentions). Ses 124 lignes actuelles décrivent
  ARIA, pas son backend. Le sujet #21 est trop technique et
  trop interne pour le README.
- **Conflit éventuel** : aucun, mais ton inadapté.

#### Option D — Section dans `docs/sprint7/runbook_t_mempalace_live.md`

- **Pour** : doc palace existante (749 lignes), opérationnelle.
- **Contre** : c'est un **runbook de migration** sprint-7 (procédure
  pas-à-pas pour passer de MiniLM à mpnet). Le sujet #21 est
  descriptif et pérenne, pas procédural ni sprint-scoped.
  L'enfouir dans un runbook archivé l'invisibilise.
- **Conflit éventuel** : aucun, mais désalignement de format
  (description vs procédure step-by-step).

#### Option E — Compléter `docs/sprint9/audit_drift_hnsw_metric.md`

- **Pour** : fichier déjà sur le sujet ChromaDB-Rust, le plus
  thématiquement proche.
- **Contre** : c'est un **audit posé à un instant T**, sprint 9
  close, tag `sprint-9` posé. Réécrire un audit clos n'est pas
  une pratique de la repo (cf. ton règlementaire du brief sur
  les audits = lecture seule post-clôture). De plus, l'audit
  `_metric` est focalisé sur la **fermeture/persistance** (chemin
  Rust vs Python), pas sur les artefacts filesystem.
- **Conflit éventuel** : brouille le statut « artefact daté » de
  l'audit.

### 4.2 Recommandation

**Option A** — créer `docs/architecture/chromadb_palace.md`.

Trois raisons décisives :

1. **Le sujet est pérenne**. Le comportement chromadb-rust (pas de
   FD persistant, `RustBindingsAPI` par défaut depuis 1.5.x, segments
   matérialisés tardivement, renommage `.drift-*`/`.corrupt-*`)
   appartient à la couche backend stable. Il ne se périme pas avec
   les sprints. Le loger dans un fichier daté (options D, E) ou
   sprint-scoped équivaut à le perdre.

2. **La repo manque structurellement d'un emplacement pérenne pour
   ce type de doc** (cf. §1.4). Toute la doc non-projet est aujourd'hui
   sprint-scoped. Inaugurer `docs/architecture/` règle ce manque, sans
   préjuger des conventions futures (le dossier peut rester un
   one-shot si besoin).

3. **Aucun conflit avec doc existante** : ni `CLAUDE.md` (qui décrit
   la taxinomie logique), ni les audits sprint 9/10 (qui sont datés)
   ne décrivent le **layout filesystem** ni la **propriété lsof-aveugle**.
   Le tour 2 a un terrain vierge.

Pour le tour 2, le fichier pourra :

- citer textuellement les trois extraits de §3.3 ci-dessus
  (`.drift-*` mecanism, lsof blind, segment 3b1fb30f) avec
  référence stable vers `audit_mempalace_artefacts.md` ;
- pointer vers `audit_drift_hnsw_metric.md` comme source d'autorité
  pour le pivot RustBindingsAPI (et signaler en note de bas que
  `audit_drift_hnsw.md` §2 est obsolète sur ce point) ;
- ajouter un cross-link rétro depuis la section « Couches mémoire »
  de `CLAUDE.md` (édition mineure, 1-2 lignes, hors charge
  documentaire principale).

---

## Annexe — Observations imprévues

1. **Inconsistance interne sprint 9 déjà signalée par ses auteurs**
   (§2.3) : `audit_drift_hnsw.md` §2 décrit un chemin Python que
   `audit_drift_hnsw_metric.md` invalide comme dead code. C'est
   **résolu en interne** par le `_metric` qui le dit explicitement.
   Pour #21 cela signifie : ne pas citer `audit_drift_hnsw.md` comme
   référence sans l'accompagner systématiquement du `_metric`.

2. **Aucune doc ne contredit le sprint 10 sur l'absence de FD
   persistant** : le point n'est mentionné *nulle part* hors de
   `audit_mempalace_artefacts.md` §3. C'est donc à la fois une
   information neuve à acter et une lacune actuelle de la doc
   pérenne — argument supplémentaire pour la créer.

3. **Le runbook `runbook_t_mempalace_live.md` (749 lignes)** mentionne
   le mot « quarantine » pour les segments HNSW dans un contexte
   opérationnel (« si quarantine → rollback section R »). Si le
   tour 2 documente `.corrupt-*` (la matérialisation filesystem de
   ce qu'opérationnellement on appelle « quarantine »), il vaudra
   la peine d'ajouter un renvoi croisé léger pour que l'opérateur
   du runbook sache où trouver l'explication structurelle.

4. **`CLAUDE.md` lignes 53-55** mentionne « 32 entrées résiduelles
   dans `mempalace_closets` non migrées ». Le sprint 10 confirme
   32 closets (cf. §2.1, table mapping UUID→segment). Cohérent — pas
   d'update nécessaire à `CLAUDE.md` sur ce point factuel.

5. **`docs/sprint4/audit_memory_layer.md`** mentionne 32 closets dès
   sprint 4. La permanence du chiffre depuis avril 2026 est un signal
   convergent que `mempalace_closets` n'a effectivement pas reçu de
   write depuis longtemps — ce qui plaide pour **lecture A** du
   §6.1 sprint 10 (Rust HNSW ne crée le dossier qu'à la première
   écriture post-démarrage). Information utile pour le tour 2 sans
   être bloquante.
