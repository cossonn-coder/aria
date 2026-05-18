# ARIA — Kickoff sprint 9 (T-Drift-HNSW, audit dette #20)

**Date** : 2026-05-18
**Branche de travail prévue** : feat/sprint9-drift-hnsw
  (à créer depuis main au démarrage de la première session)
**Tag de référence sortie sprint 8** : `sprint-8`
**État sprint 8** : CLOS. Palace prod migré
  all-MiniLM-L6-v2 → paraphrase-multilingual-mpnet-base-v2,
  bug #18 résolu, fumée Telegram validée (msg factuel +
  retrieval long-terme). Mergé dans main.

---

## Acquis sprint 8 (rappel synthétique)

- Patch `migrate_embedder.py` : étape B en lecture SQLite
  directe (`_read_collection_dim_count_sqlite`), étape F en
  filet souple. 218/218 verts.
- Migration prod : 734 entrées, dim 384 → 768, RC=0 en 193s.
- Bascule `aria/config.py` (EMBEDDING_MODEL = mpnet
  multilingue) commit local 98387c0, poussé via merge sprint 8.
- Backup `palace.backup-pre-live-20260518T100943/` (9,2M)
  CONSERVÉ comme filet d'observation. À supprimer après
  période d'observation confortable (sprint 10 ou au-delà,
  arbitrage pilote).
- Service ARIA actif sous mpnet depuis 14:37 le 18 mai.

---

## Cible sprint 9 : dette #20 — drift sqlite/HNSW non flushé

### Énoncé
`systemctl stop aria` ne déclenche pas de flush du HNSW. Le
drift sqlite/HNSW reste strictement constant avant et après
stop (+31.235 s mesurés en preprod-2). Conséquence
opérationnelle : à chaque migration ou redémarrage, la
collection qui vient d'être réécrite produit un segment
`drift-*` ou `corrupt-*` quarantiné par le fork au prochain
load. Bénin tant que le fork tolère, mais c'est du bruit qui
masque les vraies anomalies et accumule des artefacts dans
le palace.

### Hypothèses en piste
- Bug fork : pas de signal de flush propagé à la fermeture
  ChromaDB côté MemPalace
- Bug upstream ChromaDB : pas de flush automatique en
  shutdown
- Bug ARIA : pas de handler SIGTERM qui ferme proprement le
  palace avant exit
- Mix des trois

### Premier objectif sprint 9 — AUDIT pur, pas de fix

Demander à Claude Code une cartographie complète :
1. Lecture du chemin de fermeture palace côté fork
   MemPalace (modules `mempalace.backends.chroma`,
   `mempalace.embedding`, `mempalace.palace`)
2. Lecture du chemin de fermeture côté ChromaDB upstream
   (PersistentClient, segments, HNSW persistence)
3. Lecture du shutdown ARIA : main, hook signal, lifespan
   Telegram bot
4. Identification de l'éventuel point d'appel `_persist()`
   ou équivalent, et des conditions sous lesquelles il
   s'exécute ou non
5. Reproduction contrôlée du drift en environnement test
   (palace jetable, séquence write → stop → reload, mesure
   du delta sqlite vs HNSW)

Le fix arrive dans un tour séparé après audit complet.
Discipline standard : pas de patch spéculatif.

### Hors-scope explicite sprint 9
- Dettes #17 (semantic wings), #21 (closets dim 384),
  #22 (orphelins drift/corrupt), #25 (heredoc smoke),
  #26 (audit ~/.mempalace/)
- Push direct sur main
- Toute modification fonctionnelle ARIA non liée au flush

---

## Dettes ouvertes au 18 mai 2026

| #  | Sujet                                                  | Statut                      |
|----|--------------------------------------------------------|-----------------------------|
| 9  | (legacy sprint < 6)                                    | ouvert                      |
| 10 | (legacy)                                               | ouvert                      |
| 11 | (legacy)                                               | ouvert                      |
| 13 | (legacy)                                               | ouvert                      |
| 15 | (legacy)                                               | ouvert                      |
| 16 | (legacy)                                               | ouvert                      |
| 17 | Semantic wings non câblées                             | ouvert, sujet architectural |
| 18 | Palace MiniLM anglais sur contenu français             | **RÉSOLUE sprint 8**        |
| 19 | (legacy)                                               | ouvert                      |
| 20 | systemctl stop ne flushe pas HNSW, drift stable +31s   | **CIBLE SPRINT 9**          |
| 21 | Collection closets legacy dim 384                      | ouvert, atténué par fork    |
| 22 | Orphelins .drift-* / .corrupt-* dans palace prod       | ouvert                      |
| 23 | (legacy)                                               | ouvert                      |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet  |
| 25 | Heredoc smoke runbook trop strict sur pattern ST       | nouveau                     |
| 26 | Artefacts résiduels ~/.mempalace/ à auditer            | nouveau                     |

---

## Calibrage du niveau d'exigence (rappel)

Règle acquise sprint 8, toujours en vigueur :
**fix qui marche + 1 test de non-régression sur le cas nominal,
rien de plus**. Pas de filets try/except spéculatifs, pas de
mesure empirique sur dettes adjacentes en cours de sprint.
Quand on hésite entre deux niveaux de soin, prendre le moins
exigeant.

Exception réactivée : si le fix dette #20 touche au shutdown
du palace prod, le tour de bascule passe en mode prudent
(snapshot, fumée Telegram). On verra au moment du tour fix,
pas avant.

---

## Premier message à envoyer dans la nouvelle session

> Démarrage sprint 9 : audit dette #20 (drift sqlite/HNSW
> non flushé au stop). Voici le contexte de transition
> [PIÈCE JOINTE : ce document]. Sprint 8 mergé dans main,
> tag `sprint-8` posé, ARIA tourne en prod sous mpnet
> multilingue depuis le 18 mai.
>
> Premier objectif : rédiger le brief T-Drift-HNSW-Audit
> (cartographie pure, pas de fix) qui demande à Claude Code
> de tracer le chemin de fermeture du palace côté fork +
> upstream ChromaDB + ARIA, et de reproduire le drift en
> environnement contrôlé.
>
> Préalable matériel : créer la branche feat/sprint9-drift-hnsw
> depuis main avant toute autre action.
