# Audit drift segment HNSW — palace prod, 2026-05-19

## Verdict architecte (2026-05-20)

Diagnostic technique accepté : le mécanisme du fork (quarantine
`.drift-*` + reconstruction HNSW depuis sqlite) a fonctionné
nominalement, count=750 cohérent, aucune entrée perdue. **Refus
du pivot sprint 13** : sqlite est la source de vérité, le HNSW
est dérivé reconstructible, l'événement n'a rien cassé. La
pollution `.drift-*` à terme et l'absence de retention policy
justifient une dette à part — **dette #31 à ouvrir au kickoff
sprint 14**, pas d'action dans ce sprint. Le sprint 13 reste
sur #28 (pin mempalace désaligné).

Tour micro-audit déclenché par la quarantine HNSW observée au
smoke #30 du runbook sprint 7 § 6, exécuté juste avant cet audit.

```
Quarantined corrupt HNSW segment
/home/nico/.mempalace/palace/4462953f-2f2e-4df1-90de-40565b4b340b
(sqlite 22129s newer than HNSW and integrity check failed);
renamed to .../4462953f-2f2e-4df1-90de-40565b4b340b.drift-20260519-171527
```

Le mécanisme du fork a contenu l'incident (palace ouvert,
count=750, dim=768, backend ST actif, exit 0 du heredoc), donc la
section R du runbook ne s'applique pas. Cet audit cherche à
qualifier le segment quarantained : dormant ancien (drift contenu,
dette à part) ou actif (drift mécanique récurrent, pivot du
sprint).

**Méthodo** : lecture seule stricte. `ls`, `stat`, `find`, `diff`
côté filesystem. `sqlite3 file:...?mode=ro` côté chroma.sqlite3.
Aucune connexion chromadb, aucun python qui ouvre le palace.
`aria.service` est resté actif pendant tout l'audit.

---

## 1. État filesystem du palace

### Top-level `/home/nico/.mempalace/palace/`

```
drwx------ 4 nico nico    4096 19 mai 17:17 .
drwx------ 8 nico nico    4096 19 mai 10:51 ..
drwxrwxr-x 2 nico nico    4096 19 mai 17:15 4462953f-2f2e-4df1-90de-40565b4b340b
drwxrwxr-x 2 nico nico    4096 18 mai 10:13 4462953f-2f2e-4df1-90de-40565b4b340b.drift-20260519-171527
-rw-rw-r-- 1 nico nico       0  2 mai 15:45 .blob_seq_ids_migrated
-rw-r--r-- 1 nico nico 6774784 19 mai 17:17 chroma.sqlite3
-rw-rw-r-- 1 nico nico      64 18 mai 10:13 .embedder-migration-marker
-rw-rw-r-- 1 nico nico      86 18 mai 10:13 .mempalace-embedder.json
```

Markers cohérents avec la migration sprint 7 § 4 (étape G, écriture
du marker en dernier, 18 mai 10:13). `.mempalace-embedder.json`
contient bien `paraphrase-multilingual-mpnet-base-v2` (mpnet-768),
ce qui explique l'exit 0 du heredoc côté backend.

### Segments HNSW persistés (dossiers d'UUID)

| Dossier | Type | Heures (mtime dossier / fichiers) |
|---|---|---|
| `4462953f-...-b340b/` | actif | dossier 19 mai 17:15, fichiers 19 mai 17:15 |
| `4462953f-...-b340b.drift-20260519-171527/` | quarantined | dossier 18 mai 10:13, fichiers 19 mai 11:03 |

Pour chaque dossier, contenu identique (HNSW chromadb-rust à plat) :

| Fichier | Actif (taille / mtime) | Drift (taille / mtime) |
|---|---|---|
| `data_level0.bin` | 321 200 / 19 mai 17:15 | 321 200 / 19 mai 11:03 |
| `header.bin` | 100 / 19 mai 17:15 | 100 / 19 mai 11:03 |
| `length.bin` | 400 / 19 mai 17:15 | 400 / 19 mai 11:03 |
| `link_lists.bin` | 0 / 19 mai 17:15 | 0 / 19 mai 11:03 |

Tailles à plat identiques (paramètres HNSW `M`/`ef` inchangés,
`link_lists.bin` vide = un seul niveau dans l'index, normal pour
~750 entrées). `diff` binaire confirme que `length.bin` diffère
entre actif et drift → contenu différent malgré les tailles
identiques. Le segment actif a été reconstruit au reload du fork
au moment de la quarantine (mtime 19 mai 17:15:27 = instant du
heredoc).

Le mtime du dossier drift (18 mai 10:13) reflète la création du
dossier à la migration sprint 7 § 4. Les fichiers HNSW à
l'intérieur ont été écrasés à 19 mai 11:03 (dernier flush HNSW
avant le crash), sans changer le mtime du dossier parent (écriture
en place, pas d'add/remove d'entrée dans le dossier).

### Quarantine `.drift-*` / `.corrupt-*`

```
find /home/nico/.mempalace/palace/ -name '.drift-*' -o -name '.corrupt-*'
→ (un seul match)
  /home/nico/.mempalace/palace/4462953f-...-b340b.drift-20260519-171527/
```

**Un seul artefact de quarantine sur tout le palace.** Aucun
`.corrupt-*`, aucun `.drift-*` antérieur. Le drift d'aujourd'hui
est un **one-off observé**, pas une récurrence visible côté
filesystem.

### Segment manquant : `mempalace_closets` VECTOR

L'inspection sqlite (§ 2) déclare deux collections, donc deux
segments VECTOR attendus. Seul un sur disque
(`4462953f-...` = drawers). Le VECTOR de closets
(`3b1fb30f-7da4-43f1-969e-f0b180ca92e3`, cf. § 2) n'a aucun
dossier dans `palace/`. Hypothèse : closets n'a jamais été
matérialisé sur disque côté HNSW depuis la migration (collection
figée depuis le 15 avril, cf. § 2 — pas de query côté lecture qui
forcerait une instanciation, et le flush HNSW initial n'a peut-être
jamais eu lieu sur cette collection). Hors-scope strict du tour,
noté pour mémoire.

---

## 2. Inspection sqlite du palace

`sqlite3 file:.../chroma.sqlite3?mode=ro`, mtime du fichier
`19 mai 17:17:56` (frais — ARIA est actif).

### Collections et segments

```
collections:
  64d7d455-...-da93 → mempalace_closets
  0756d591-...-931a → mempalace_drawers

segments:
  3b1fb30f-...-92e3 | VECTOR (hnsw-local-persisted) | closets
  77f2d20c-...-77aa | METADATA (sqlite)             | closets
  4462953f-...-b340b| VECTOR (hnsw-local-persisted) | drawers     ← QUARANTINED
  e60429a8-...-f711 | METADATA (sqlite)             | drawers
```

→ Le segment quarantained est le segment VECTOR de
**`mempalace_drawers`**, c'est-à-dire la collection prod active
(interactions, image_input, image_generated — cf. CLAUDE.md
§ Couches mémoire). Ce n'est PAS le segment de closets (legacy,
figé depuis avril).

### Contenu par segment METADATA (côté embeddings)

| Segment METADATA | Coll. | count | min seq_id | max seq_id | min created_at | max created_at |
|---|---|---|---|---|---|---|
| `77f2d20c-...` | closets | 32 | 15 | 451 | 2026-04-15 09:57 | 2026-04-15 10:01 |
| `e60429a8-...` | drawers | **753** | 452 | 1204 | 2026-05-18 08:13 | **2026-05-19 15:17:56** |

`created_at` est en UTC dans sqlite (offset +2h vs local
observé : 15:17 UTC = 17:17 local).

- **closets** : 32 entrées sur seq_id 15-451 (= 437 slots dont
  ~405 deletes / orphelins seq_id). Plus aucune écriture depuis
  le 15 avril 2026. Aucun risque de drift sur ce segment (HNSW
  jamais persisté = jamais en jeu pour l'integrity check côté
  fork). Cohérent avec la note CLAUDE.md sur les 32 entrées
  résiduelles non migrées.
- **drawers** : 753 entrées sur seq_id 452-1204 contigus
  (1204-452+1 = 753, **aucun gap**). Distribution par jour :

  ```
  2026-05-18 : 738 entrées  (migration sprint 7 § 4, repopulation massive)
  2026-05-19 :  15 entrées  (activité ARIA d'aujourd'hui)
  ```

### `segment_metadata` côté sqlite

```
SELECT * FROM segment_metadata WHERE segment_id IN
  ('3b1fb30f-...', '4462953f-...');
→ vide (0 row)
```

Aucun paramètre HNSW persisté côté sqlite pour les segments
VECTOR. Le fork (resp. chromadb-rust) reconstruit avec les
defaults `M=16`, `ef_construction=100`, etc. lors d'un reload —
ce qui explique pourquoi la reconstruction post-quarantine a
réussi sans config externe.

### Calcul de l'écart sqlite vs HNSW (segment drawers)

| Source | Heure (local) | Heure (UTC) |
|---|---|---|
| Dernier flush HNSW (mtime fichiers drift) | 19 mai **11:03** | 19 mai 09:03 |
| Dernier write sqlite (max created_at drawers) | 19 mai **17:17:56** | 19 mai 15:17:56 |
| Quarantine déclenchée par smoke | 19 mai **17:15:27** | 19 mai 15:15:27 |

Écart sqlite (au moment du smoke) vs HNSW :
- 17:15:27 − 11:03 ≈ **6 h 12 min ≈ 22 320 s**
- Le fork a annoncé `22129s` → cohérent à la fenêtre près
  (timestamps tronqués / horloge fine vs mtime arrondi).

### Embeddings écrits APRÈS le dernier flush HNSW (cœur du drift)

Filtre `created_at > '2026-05-19 11:03:00'` (UTC, équivalent
≥ 13:03 local — sur-estime légèrement la fenêtre, mais aucun
embedding ne tombe dans l'intervalle 11:03-13:03 local donc le
résultat est exact) :

```
SELECT COUNT(*) FROM embeddings
WHERE segment_id='e60429a8-...' AND created_at > '2026-05-19 11:03:00';
→ 10
```

Détail des 10 entrées (les 15 derniers seq_id, on garde celles
après flush) :

| seq_id | created_at (UTC) | local | côté HNSW ? |
|---|---|---|---|
| 1195 | 2026-05-19 15:10:44 | 17:10:44 | non |
| 1196 | 2026-05-19 15:10:57 | 17:10:57 | non |
| 1197 | 2026-05-19 15:11:00 | 17:11:00 | non |
| 1198 | 2026-05-19 15:11:22 | 17:11:22 | non |
| 1199 | 2026-05-19 15:11:29 | 17:11:29 | non |
| 1200 | 2026-05-19 15:11:40 | 17:11:40 | non |
| 1201 | 2026-05-19 15:12:01 | 17:12:01 | non — présent dans HNSW reconstruit (count=750) |
| 1202 | 2026-05-19 15:17:26 | 17:17:26 | **non — écrit APRÈS le smoke** |
| 1203 | 2026-05-19 15:17:51 | 17:17:51 | **non — écrit APRÈS le smoke** |
| 1204 | 2026-05-19 15:17:56 | 17:17:56 | **non — écrit APRÈS le smoke** |

Note importante : la dernière entrée 1194 indexée dans le HNSW
drift a été écrite à 09:03:19 UTC (11:03:19 local), juste avant le
flush. Donc le HNSW a flushé en couvrant l'entrée 1194, puis ARIA
a écrit 7 entrées (1195-1201) avant le smoke sans déclencher de
nouveau flush, puis 3 entrées (1202-1204) après le smoke
également sans flush.

---

## 3. Cohérence count=750

Sources du count :

- Smoke heredoc (17:15:27 local) → `count=750`
- Sqlite sur drawers METADATA (17:17:56 local) → 753 embeddings

Le segment HNSW actif (mtime 17:15) couvre seq_id 452 à 1201
(= 750 entries) — c'est ce que le smoke a vu. Les 3 entrées
1202-1204 ont été écrites en sqlite **après** le smoke (17:17),
donc absentes du HNSW actif (mtime gelé à 17:15).

**Reconstruction côté fork** : à la quarantine, le fork a
renommé l'ancien dossier en `.drift-*` puis rebuilt le HNSW
depuis sqlite. À 17:15:27, sqlite contenait 750 entrées
(jusqu'à 1201). Le nouveau HNSW couvre exactement ces 750. Plus
de drift au moment de la reconstruction — il reprend immédiatement
dès que ARIA écrit (3 entries en germe à l'heure de cet audit).

**Le segment drift avant quarantine couvrait combien d'entrées ?**
Le HNSW drift a été flushé pour la dernière fois à 09:03 UTC.
Entrées écrites dans sqlite avant ce moment (`created_at <=
'2026-05-19 09:03:20'`) : seq_id 452 à 1194 = **743 entrées**.
C'est ce que contenait probablement le HNSW drift au moment où
le fork l'a quarantained. (Vérifié indirectement par `diff` :
`length.bin` actif vs drift diffèrent → contenus distincts.)

---

## 4. Verdict diagnostique

### Le segment drift = dormant ou actif ?

**Actif.** C'est le segment VECTOR de `mempalace_drawers`, la
collection prod où ARIA écrit toutes ses interactions
(`interaction|image_input|image_generated`). Pas un orphelin,
pas un dormant — le **seul** segment vecteur persisté du palace
(closets n'a jamais matérialisé son HNSW). 738 entries écrites
le 18 mai (migration sprint 7 § 4), 15 supplémentaires
aujourd'hui dont 10 directement responsables du drift.

### Récurrence ou one-off ?

**One-off observé** côté filesystem (un seul `.drift-*`, aucun
`.corrupt-*`, aucun antérieur). Mais one-off **conjoncturel** : la
mécanique sous-jacente est clairement récurrente — `aria.service`
écrit en sqlite à chaque interaction, mais le flush HNSW
chromadb-rust ne suit pas synchroniquement (10 entries
accumulées entre le dernier flush 09:03 UTC et la quarantine
15:15 UTC, et déjà 3 entries en attente depuis 17:15 ce soir).
À chaque nouvelle ouverture du palace (smoke, redémarrage
d'aria.service, reload après crash), le fork va re-déclencher la
même quarantine si l'écart sqlite vs HNSW dépasse son seuil
d'intégrité. La probabilité d'un nouveau drift à la prochaine
ouverture est élevée.

### Hypothèses sur le mécanisme (hors-scope investigation, juste pour cadrer)

- Le flush HNSW à 09:03 UTC ne correspond à aucun évènement
  documenté (pas de redémarrage de service ce matin à ma
  connaissance). Possible flush conditionnel chromadb-rust
  (taille de buffer, seuil d'entrées, fenêtre de temps) — à
  cartographier dans le sprint qui suivra ce tour, hors-scope
  ici.
- Le seuil de quarantine du fork (`22129s` ≈ 6h09) suggère un
  threshold côté `ChromaBackend._read_embedder_marker` /
  integrity check, à confirmer.

### Recommandation

**Pivoter.** Le drift n'est pas contenu — il va se reproduire
mécaniquement à chaque ouverture du palace tant que la cadence
de flush HNSW est désynchronisée des writes sqlite côté ARIA.
Continuer sprint 13 sur #28 sans traiter ce mécanisme laisse une
fenêtre à chaque cycle :

- Smoke #30 redéclenchera la quarantine (sauf si on flush avant)
- Restart `aria.service` redéclenchera la quarantine
- Reboot machine idem

Le risque concret : à terme, accumulation de `.drift-*` dans
`palace/` (sans retention policy visible — un seul aujourd'hui,
mais rien n'empêche d'en avoir 10 dans 10 ouvertures), et
surtout, à chaque quarantine + reconstruction, on perd les N
entrées écrites depuis le dernier flush si la reconstruction se
fait à un moment où sqlite est en cours d'écriture (race
condition non observée mais théorique).

**Proposition pour le tour suivant du sprint 13** (à cadrer
ailleurs, ce n'est pas le livrable de ce tour) :

1. Cartographier le mécanisme de flush HNSW côté chromadb-rust /
   wrapper fork (où, quand, sous quelle condition).
2. Vérifier s'il existe une API `flush()` / `persist()`
   exposable, et l'invoquer à minima dans le shutdown handler
   d'`aria.service` et avant chaque smoke.
3. Définir une retention policy pour les `.drift-*` (auj. : aucune,
   ils restent en place indéfiniment).
4. Statuer sur #28 : à reporter au sprint suivant, ou à traiter
   en parallèle si on estime que les deux chantiers n'interagissent
   pas.

### Hors-scope confirmés (rappel)

- Aucune réparation du segment quarantained — il reste en place.
- Aucune modification du palace ni du marker.
- Aucun fix sur le flush HNSW dans ce tour.
- Pas d'inspection du code mempalace côté flush (juste l'état
  observé sur disque).
- Pas d'investigation #26, #29, autres dettes adjacentes.

---

## Annexe — commandes utilisées (reproductibilité)

```bash
# Filesystem
ls -la /home/nico/.mempalace/palace/
ls -la /home/nico/.mempalace/palace/4462953f-2f2e-4df1-90de-40565b4b340b/
ls -la /home/nico/.mempalace/palace/4462953f-2f2e-4df1-90de-40565b4b340b.drift-20260519-171527/
find /home/nico/.mempalace/palace/ -name '.drift-*' -o -name '.corrupt-*'
stat -c '%y %n' /home/nico/.mempalace/palace/.{blob_seq_ids_migrated,mempalace-embedder.json,embedder-migration-marker} \
                /home/nico/.mempalace/palace/chroma.sqlite3
diff -q <actif>/<f> <drift>/<f>   # pour chaque f des 4 fichiers HNSW

# Sqlite (read-only)
SQ='sqlite3 file:/home/nico/.mempalace/palace/chroma.sqlite3?mode=ro'
$SQ '.tables'
$SQ "SELECT id, name FROM collections;"
$SQ "SELECT id, type, scope, collection FROM segments;"
$SQ "SELECT segment_id, COUNT(*) FROM embeddings GROUP BY segment_id;"
$SQ "SELECT * FROM max_seq_id;"
$SQ "SELECT MIN(created_at), MAX(created_at), COUNT(*) FROM embeddings
     WHERE segment_id='e60429a8-94f5-4ec6-adff-a20323e2f711';"
$SQ "SELECT COUNT(*) FROM embeddings
     WHERE segment_id='e60429a8-94f5-4ec6-adff-a20323e2f711'
       AND created_at > '2026-05-19 11:03:00';"
$SQ "SELECT * FROM segment_metadata WHERE segment_id IN
     ('3b1fb30f-...','4462953f-...');"
```

Lecture : exécutables tels quels, lecture seule, palace prod
intact post-audit (mtime `chroma.sqlite3` peut bouger entre-temps
sous l'effet d'ARIA, c'est nominal).
