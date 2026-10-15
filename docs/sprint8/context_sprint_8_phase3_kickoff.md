# ARIA — Kickoff sprint 8 phase 3 (T-Mempalace-Prod, run live)

**Date** : 2026-05-18
**État sprint 8** : phase 1 close (commit 513ac2a, lecture
SQLite directe étape B + filet étape F, 218/218 verts), phase 2
close (Preprod-2 verdict GO sur palace réel avec quarantaines).
**Session précédente** : clôture phase 1 + phase 2, mesure
empirique dette #20 (stop service ne flushe pas le HNSW, drift
stable à +31s), validation retrieval français OK avec
paraphrase-multilingual-mpnet-base-v2.

---

## Pourquoi nouvelle session

Discipline acquise depuis sprint 6 : run live prod en session
dédiée. La session précédente a consommé ~60% sur les phases 1
et 2 (deux livrables denses, écarts à arbitrer en cours de
tour). La phase 3 touche au palace prod réel avec bascule
config.py et redémarrage ARIA — réaction temps réel possible,
exige fenêtre claire.

---

## Acquis sprint 8 phase 1 + 2

### Patch script
- HEAD ARIA : 513ac2a (commit local non poussé)
- migrate_embedder.py : étape B en lecture SQLite directe via
  `_read_collection_dim_count_sqlite(palace_path, name)`,
  assertion mismatch dim renforcée, étape F en filet
  try/except avec warning + traceback court
- Suite pytest : 218/218 verts dont 10 tests nouveaux sur le
  lecteur SQLite et l'inspection étape B
- Robuste aux palaces dégradés (quarantained HNSW)

### Validation Preprod-2
- Copie /home/nico/.mempalace/palace.preprod2-20260518T074203
  CONSERVÉE pour référence (9.56 MB, 34 fichiers)
- Migration MiniLM → paraphrase-multilingual-mpnet-base-v2 en
  3m31s, RC=0
- count=726, dim=768, retrieval français cohérent
- Effet secondaire confirmé : ouverture post-migration
  quarantained le HNSW de `mempalace_closets` (legacy
  dette #21), comportement fork attendu sur collection
  non-migrée

### Choix modèle cible (changement vs brief initial)
- Cible retenue :
  `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- PAS `all-mpnet-base-v2` (anglais) — le bug #18 vient
  précisément du fait que le palace tourne en MiniLM anglais
  sur contenu français. Le multilingue est l'objectif réel.
- Modèle déjà en cache HF côté VM (1.1 GB).

---

## Dette #20 — signal empirique acquis

`systemctl stop aria` ne flushe pas le HNSW. Drift sqlite/HNSW
mesuré strictement constant avant et après stop (+31.235 s).
Hypothèse "stop converge" invalidée. À ré-investiguer dans un
sprint dédié — bug fork ou bug ChromaDB upstream. Hors-scope
sprint 8.

Conséquence pour la phase 3 : pas la peine de chercher à
flusher avant le rsync prod, on accepte le drift résiduel comme
on l'a accepté en Preprod-2.

---

## Plan d'exécution phase 3

### Tour 1 : T-Mempalace-Prod (run live)
Exécution du runbook
docs/sprint7/runbook_t_mempalace_live.md sections 2 à 10 :

1. Pré-vol (git HEAD = 513ac2a, venv fork, pytest 218 verts)
2. Stop service ARIA
3. Snapshot tar.gz du palace prod
4. Rsync à froid → palace.backup-pre-live-<ISO>
5. Migration du palace prod via script patché
   --to-model paraphrase-multilingual-mpnet-base-v2
6. Smoke (count=726 attendu, dim=768)
7. Bascule config.py (EMBEDDING_MODEL = nouveau modèle)
8. Start service ARIA
9. Fumée Telegram (1-2 messages courts pour valider que ARIA
   répond et que la mémoire fonctionne)
10. Vérif logs journalctl côté pilote (Nico)

Interventions pilote nécessaires : stop, start, fumée Telegram,
copie sortie journalctl.

À anticiper dans le brief : la quarantaine HNSW closets va se
produire à la première ouverture du palace migré post-bascule.
Côté pilote, ne PAS s'alarmer du message
"Quarantined corrupt HNSW segment 3b1fb30f-..." dans les logs
ARIA — c'est le comportement attendu du fork sur la collection
legacy non-migrée.

### Tour 2 : T-Mempalace-Cleanup (phase 4 sprint 8)
Nettoyage post-succès :
- palace.preprod2-20260518T074203 (référence Preprod-2)
- palace.preprod-20260517T215402 (référence Preprod-1 sprint 7)
- palace.backup-pre-live-<ISO> (snapshot étape 4)
- snapshot tar.gz étape 3
- /tmp/migrate_*.log
- répertoires .drift-* et .corrupt-* orphelins du palace prod
  migré (surprise n°1 audit sprint 7)

### Tour 3 : T-Sprint8-Cloture (phase 5)
- Validation finale (services up, ARIA répond, retrieval
  cohérent sur 2-3 requêtes Telegram)
- Push origin de 513ac2a + commits sprint 8 (config.py,
  éventuel patch runbook)
- Arbitrage Nico : tag sprint-7 séparé OU tout dans sprint-8 ?
- Merge main si OK
- Rédaction context_sprint_9_kickoff.md (sujets à arbitrer
  par Nico : dette #20 prioritaire ? semantic wings dette #17 ?
  cleanup closets dette #21 ? autre ?)

---

## Dettes ouvertes (cumul, inchangées hors #20 acquis)

- #9, #10, #11, #13, #15, #16, #17 (semantic wings non câblées),
  #18 (résolue par migration mpnet, à confirmer en prod),
  #19, #21 (closets legacy dim 384), #22 (orphelins .drift-*
  /.corrupt-*), #23
- **#20 — signal acquis** : stop ne flushe pas HNSW. Drift
  stable à 31s. Bug à investiguer dans un sprint dédié.
- **#24 — nouveau** : `_read_collection_dim_count_sqlite`
  ignore `database_id` dans la requête SELECT. ARIA est
  mono-database, sans effet pour le moment. À fixer le jour
  où une seconde database apparaît.

---

## Calibrage du niveau d'exigence (acquis sprint 8)

Nouvelle règle ajoutée dans les instructions projet :
**fix qui marche + 1 test de non-régression sur le cas
nominal**. Pas de filets "au cas où", pas de mesure empirique
sur dettes adjacentes en cours de sprint. Quand on hésite
entre deux niveaux de soin, prendre le moins exigeant.
S'applique à partir de la phase 3.

Exception phase 3 : run live prod = mode prudent natif
(pré-vol systématique, snapshot avant migration, fumée
Telegram). Ce n'est pas un excès de soin, c'est la définition
même du run live.

---

## Premier message à envoyer dans la nouvelle session

> Démarrage sprint 8 phase 3 : T-Mempalace-Prod, run live
> migration MiniLM → paraphrase-multilingual-mpnet-base-v2 sur
> le palace prod. Voici le contexte de transition
> [PIÈCE JOINTE : ce document].
>
> Phases 1 et 2 closes session précédente, patch validé en
> Preprod-2 sur palace réel avec quarantaines. Modèle cible
> tranché : multilingue (pas anglais), pour résoudre bug #18.
> Tout est en place pour le run live.
>
> Premier objectif : rédiger le brief T-Mempalace-Prod qui
> applique le runbook docs/sprint7/runbook_t_mempalace_live.md
> sections 2-10, avec ces ajustements :
>   - to-model = paraphrase-multilingual-mpnet-base-v2
>   - count attendu = 726
>   - note explicite : quarantaine HNSW closets attendue à la
>     première ouverture post-migration, NON-bloquant
>   - fumée Telegram = 2 messages courts (un factuel, un qui
>     teste retrieval mémoire)
>
> Lis le runbook dans la VM Claude Code, pas besoin de me le
> re-citer.