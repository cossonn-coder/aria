# ARIA — Kickoff sprint 7 : fork MemPalace embedder

**Date** : 2026-05-13
**État sprint 6** : clos avec demi-succès — ingénierie aboutie,
livraison bénéfice attendu reportée. Découverte cause racine.
**Phase suivante** : sprint 7, fork MemPalace pour rendre l'embedder
configurable. Le palace migré 768 et le script de migration restent
sur étagère, prêts à être réactivés une fois MemPalace patché.

---

## Clôture sprint 6 — bilan factuel

### Ce qui a été livré et est valide

**T-Z** : nettoyage repo, renommage branche, tag `sprint-5` pushé.
HEAD main `892434d`. Outils CLI DeepSeek commités. (Clos session
précédente.)

**T-Embedder1** : audit lecture seule, inventaire collections,
benchmark qualité multilingue 6 modèles × 8 cas terrain. Choix
`paraphrase-multilingual-mpnet-base-v2` (M2, dim 768) sur la base
R@3=0.88 vs 0.62 pour MiniLM, 0.38 pour la baseline `all-mpnet-base-v2-onnx`.
Branche `feat/sprint6-embedder-audit` jusqu'à `1e78b39`, pushée.

**T-Embedder2** : cleanup intent fantôme (Tâche A), décommissionnement
`chroma_db/` legacy (Tâche B), audit DeepSeek hard-codes dim 384
(Tâche C, zéro blocker confirmé), écriture script `migrate_embedder.py`
+ 4 patchs DeepSeek (Tâche D), test sur copie locale révélant 4 bugs
runtime corrigés (Tâche D-bis : `tempfile` manquant, truthiness numpy,
piège `os.replace` répertoire non-vide → swap par 2 `os.rename`
séquentiels). Pytest 208/208. HEAD `d780a66`.

**T-Embedder3** : runbook `docs/sprint6/runbook_t_embedder3.md`
rédigé et commité (`b6322f4`). Migration prod exécutée avec succès :
snapshot tar.gz créé, 697 entrées re-encodées en 138s à 5.0 phrases/s,
swap atomique réussi, marker écrit, validation count + dim conformes.
Bascule `config.py` commitée (`c12f5e7`).

### Ce qui a échoué et pourquoi

Au redémarrage ARIA, premier message Telegram a produit :

```
mempalace.embedding — Embedding function initialized
    (device=cpu providers=['CPUExecutionProvider'])
chromadb.errors.InvalidArgumentError:
    Collection expecting embedding with dimension of 768, got 384
```

**Cause racine** : MemPalace hardcode `ONNXMiniLM_L6_V2` dans
`embedding.py`. Le seul paramètre exposé (`embedding_device`) ne
change que le provider ONNX (CPU/CUDA/CoreML/DML), pas le modèle.
La docstring le revendique explicitement : *« The same all-MiniLM-L6-v2
model and 384-dim vectors ChromaDB ships by default are reused, so
switching device does not invalidate existing palaces. »* L'embedder
est traité par MemPalace comme un invariant.

Notre script a re-encodé le palace via `sentence_transformers` direct
(en 768), mais ARIA en runtime délègue l'embedding à MemPalace qui
encode en 384. Mismatch garanti à chaque upsert et chaque requête.

### Rollback

Exécuté à 13:18. Service stoppé. Palace migré 768 mis de côté sous
`~/.mempalace/palace.rollback-failed-20260513T131824/`. Snapshot
tar.gz `mempalace_drawers_backup_20260513T105601Z.tar.gz` extrait,
palace restauré à 697 entrées dim 384. Commit `c12f5e7` reverté par
`b696129`. Service redémarré, palace lu sans erreur, ARIA stable.

Le filet snapshot + revert a fonctionné de bout en bout. C'est sa
première mise en production réelle, et c'est concluant.

### Artefacts conservés (ne pas supprimer)

- `~/.mempalace/palace.rollback-failed-20260513T131824/` — palace
  migré en 768, prêt à être réinjecté une fois MemPalace patché.
  Évite de refaire 2'30 d'encodage et conserve la valeur du travail
  de migration.
- `~/.mempalace/mempalace_drawers_backup_20260513T105601Z.tar.gz` —
  snapshot pré-migration, sécurité supplémentaire.
- `~/.mempalace/palace_preprod_20260513T124229/` — copie pré-prod
  migrée, utile pour comparer si on suspecte un effet de bord
  spécifique à la prod.
- `/tmp/migrate_preprod_20260513T124229.log` et
  `/tmp/migrate_prod_20260513T125559.log` — logs des deux migrations.

À nettoyer **après** la première migration réussie post-patch
MemPalace, pas avant.

### Découverte stratégique

Le bug d'audit fondamental : on a benché un modèle qu'ARIA n'utilise
pas. La constante `config.EMBEDDING_MODEL` côté ARIA n'a aucune
relation avec l'embedder MemPalace runtime — elle n'était lue que
par nos scripts (bench, migration). Le log
`providers=['CPUExecutionProvider']` était un signal `onnxruntime`
qu'on a manqué pendant tout le sprint 6.

**Leçon transverse** : pour tout package tiers qui s'auto-administre
une ressource (embedder, cache, base, modèle LLM), auditer
**ce qu'il fait en runtime**, pas **ce que sa surface API revendique
qu'il fait**. Un `grep` du log de boot aurait suffi.

---

## Sprint 7 — T-MempalaceEmbedder

### Objectif

Rendre l'embedder MemPalace paramétrable, basculer ARIA sur
`paraphrase-multilingual-mpnet-base-v2`, valider live.

### Décomposition en sous-sprints

**T-S6-Closure** (priorité 1, démarrage sprint 7)
Clôture propre du sprint 6 avant d'attaquer le 7.

- Tag `sprint-6` sur `b696129`. Le tag matérialise l'état « sprint 6
  terminé avec rollback validé, sprint 7 prend le relais », pas
  « migration réussie ». Note explicite dans le message de tag.
- Merge `feat/sprint6-embedder-audit` → `main` après push de la
  branche. Le travail mérite d'être en `main` : script de migration
  réutilisable, runbook réutilisable, doc, cleanup intent fantôme,
  bench framework.
- Push `main` et tag.
- Décision : `feat/sprint6-embedder-audit` est supprimée après merge
  ou conservée pour traçabilité ? Reco : conservée jusqu'au tag
  `sprint-7`, supprimée ensuite. À arbitrer en début de sprint.

**T-Mempalace-Audit** (priorité 2)
Lecture du code source MemPalace par Claude Code. Inventaire des
points où l'embedder est utilisé : `embedding.py`, `backends/chroma.py`,
`backends/registry.py`, `palace.py`, et tout caller de
`get_embedding_function`. Cartographie des invariants implicites du
package (notamment le name-spoofing à `"default"` pour compat ChromaDB).
Livrable : `docs/sprint7/audit_mempalace_embedder.md` avec plan de
patch chiffré (lignes touchées, tests à ajouter, risques de
régression).

**T-Mempalace-Fork** (priorité 3, après audit)
Setup du fork. Clone du repo MemPalace sur GitHub, branche
`feat/configurable-embedder`. Configuration du venv ARIA pour pointer
sur le clone local (`pip install -e ../mempalace-fork`). Validation
que les tests upstream passent toujours dans le venv ARIA.
Livrable : fork en place, ARIA reprend ses tests pytest sans
régression vs version PyPI.

**T-Mempalace-Patch** (priorité 4)
Implémentation du patch dans le fork. Direction probable (à valider
en audit) : factory `get_embedding_function` accepte un nom de
modèle, registre de dims associées, fallback MiniLM par défaut pour
ne rien casser pour les utilisateurs MemPalace existants. Gestion du
name-spoofing ChromaDB : soit on conserve `name() = "default"` quel
que soit le modèle (risque de surprise pour les autres palaces), soit
on bascule sur le nom réel et on accepte la rupture compat (palaces
créés par MemPalace 3.x ne seront pas relisibles, mais ce n'est pas
notre cas — notre palace a été migré par notre propre script). À
arbitrer au moment du patch.

**T-Mempalace-Tests** (priorité 5)
Tests unitaires sur le fork : factory retourne bien le bon modèle,
fallback CPU/MiniLM marche, name-spoofing comportement défini.
Tests d'intégration ARIA : pytest 208+ verts, palace neuf créé avec
mpnet lit/écrit sans erreur, palace MiniLM existant continue de
fonctionner.

**T-Mempalace-Migrate-Reuse** (priorité 6)
Réutilisation du palace `palace.rollback-failed-20260513T131824/`
(déjà en 768). Test : MemPalace patché lit-il correctement ce palace ?
Si oui, gain de 2'30 d'encodage et validation indépendante du script
de migration. Si non, analyse de l'écart et re-migration depuis le
palace MiniLM courant.

**T-Mempalace-Live** (priorité 7, run live final)
Même protocole que T-Embedder3 : runbook, test pré-prod sur copie,
arrêt service, bascule, redémarrage, 4 messages Telegram-test (les
mêmes que le runbook actuel). Diff par rapport à T-Embedder3 : on a
maintenant **deux** points de bascule (config ARIA + config MemPalace)
qu'il faut articuler proprement dans le runbook.

### Hors-scope sprint 7

- Sortie de MemPalace au profit d'un wrapper ChromaDB direct (option
  trop large, gardée en réserve).
- PR upstream du fork. À considérer en fin de sprint si le patch est
  propre, mais n'est pas un livrable obligatoire.
- Optimisations de qualité retrieval au-delà du choix du modèle
  (tuning seuil similarité, re-ranking, etc.) — à traiter en sprint
  ultérieur, une fois que la qualité de base est confirmée meilleure.

---

## Dettes workflow consolidées

### Fermées au sprint 6

- **#8** chroma_db legacy versionné — Tâche B.
- **#18** bug planification voyage retrievé sur intent culinaire —
  **PAS fermée** finalement, puisqu'on n'a pas pu valider live.
  Réouverte en attente du sprint 7.

### Toujours ouvertes (à traiter au cours du sprint 7)

- **#9** psutil non documentée dans requirements. À régler en même
  temps que #10 (à identifier dans la dette historique).
- **#11** DeprecationWarning Python 3.14 sur `tar.extractall` sans
  `filter=` dans `migrate_embedder.py`. Cosmétique, mais à régler
  avant la prochaine utilisation du script.
- **#12** Piège `os.replace` sur répertoire non-vide. À documenter
  dans la doc tribale projet (`docs/lessons_learned.md` ?).
- **#13** Discipline workflow : consigne CLAUDE.md envoyée au
  milieu d'un brief Tâche dilue le focus. Consignes hors-brief ou en
  début de brief uniquement.

### Nouvelles dettes sprint 6 (clôture T-Embedder3)

- **#14** Runbook ne vérifie pas les outils CLI requis dans le
  pré-vol (rsync, tmux, tar, etc.). La VM `vDebianIA` n'a ni `rsync`
  ni `tmux`. À ajouter au modèle de runbook futur : section
  « outils requis + vérif `command -v` » en étape 0.
- **#15** Discipline pilote : quand un check pré-vol échoue, ne pas
  improviser, ne pas sauter d'étape. Si l'architecte est injoignable,
  défaut = stop + rollback léger (redémarrer service, on reprend
  plus tard). Le saut de l'étape 0 et de l'étape 1 ce sprint a
  manqué de peu de provoquer une perte mémoire silencieuse en prod.
- **#16** Audit de surface : pour tout package tiers s'auto-administrant
  une ressource (embedder, cache, modèle LLM, base), auditer ce qu'il
  fait en runtime (grep des logs de boot, lecture du code) avant
  d'engager une migration qui dépend de son comportement. **Cause
  racine du semi-échec sprint 6.**

---

## État technique en fin de sprint 6

- Branche `feat/sprint6-embedder-audit`, HEAD `b696129`, **non
  pushée**. 7 commits locaux non poussés depuis `1e78b39` :
  `82497a8`, `d99b623`, `71a994a`, `a4b4545`, `d780a66`, `b6322f4`,
  `c12f5e7`, `b696129`.
- Palace prod : `~/.mempalace/palace/`, 697 entrées, dim 384,
  embedder MiniLM (état pré-sprint restauré).
- `config.EMBEDDING_MODEL = "all-MiniLM-L6-v2"` (post-revert).
- Service ARIA `active`, fonctionnel.
- Untracked working tree : `CLAUDE.md` (modifié non commité),
  `docs/sprint7/` (brouillon ChatGPT, hors scope), `tmp/`,
  `.local/`, `docs/sprint6/context_sprint_6_T-Embedder3_kickoff.md`.
  À arbitrer ce qui rejoint le commit final et ce qui reste local.

---

## Vision long terme — ce que le fork change

ARIA = système cognitif partageable, palace MemPalace isolé par
utilisateur. Cette vision a guidé les choix sprint 4+ mais
supposait implicitement que MemPalace serait suffisamment générique
pour héberger des palaces de qualités différentes. La découverte
sprint 6 montre que MemPalace est figé sur un modèle anglais
performant pour l'anglais mais médiocre pour le français multilingue.

**Le fork n'est pas un détour, c'est l'alignement architectural
manquant.** En devenant co-mainteneur de la brique vectorielle, ARIA
peut :

- exposer un embedder par défaut adapté à sa langue cible,
- permettre à un utilisateur de choisir son embedder à l'instanciation
  d'un palace,
- évoluer indépendamment du calendrier upstream MemPalace.

PR amont possible mais pas obligatoire — la valeur du fork existe
même sans contribution upstream.

---

## Premier message à envoyer dans la nouvelle session

> Ouverture sprint 7 — fork MemPalace pour embedder configurable.
> Voici le contexte de transition [PIÈCE JOINTE : ce document].
>
> Sprint 6 clos avec demi-succès : ingénierie migration aboutie
> (script, snapshot, rollback validés en live aujourd'hui), mais
> bénéfice bloqué par le hardcode de l'embedder MemPalace dans
> `embedding.py`. Rollback exécuté, ARIA stable en MiniLM 384.
> Palace migré 768 conservé sous
> `~/.mempalace/palace.rollback-failed-20260513T131824/`.
>
> Premier objectif : rédiger le brief T-S6-Closure — tag `sprint-6`
> avec note explicite (clôture partielle, sprint 7 prend le relais),
> push de `feat/sprint6-embedder-audit`, merge → `main`. Décider
> du devenir de la branche post-merge. Arbitrer le sort de
> `CLAUDE.md` modifié non commité et `docs/sprint7/` brouillon.
>
> Objectif suivant : brief T-Mempalace-Audit — lecture lecture seule
> du code source MemPalace par Claude Code, livrable
> `docs/sprint7/audit_mempalace_embedder.md` avec plan de patch
> chiffré.
