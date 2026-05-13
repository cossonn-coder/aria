# Runbook T-Embedder3 — Migration embedder live prod

**Sprint 6 / T-Embedder3.** Exécution prod : copie pré-prod, arrêt
ARIA, migration `~/.mempalace/palace/`, bascule `EMBEDDING_MODEL`,
redémarrage, validation Telegram. **Lire dans l'ordre, ne pas
improviser. Un Go/No-Go à chaque étape — au moindre doute, stop +
rollback.**

Source : `all-MiniLM-L6-v2` (dim 384).
Cible : `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
(dim 768). Palace prod : `~/.mempalace/palace/` (~9 Mo, ~689 entrées
au 2026-05-10, peut avoir crû).

---

## Étape 0 — Pré-vol

```bash
cd ~/Nextcloud/projects/aria
git rev-parse --short HEAD                       # attendu : d780a66
git status --short                                # working tree propre côté code
git branch --show-current                         # attendu : feat/sprint6-embedder-audit
du -sh ~/.mempalace/palace                        # noter la taille
df -h ~/.mempalace | tail -1                      # ≥ 500 Mo libres requis (snapshot + tmpdir extraction)
./venv/bin/python -c "import sentence_transformers, chromadb, tqdm; print('deps OK')"
./venv/bin/python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2'); print('model warm-up OK')"
```

**Attendu** :
- HEAD = `d780a66`, working tree propre (sauf untracked autorisés).
- Branche = `feat/sprint6-embedder-audit`.
- `deps OK` puis `model warm-up OK` (le modèle est mis en cache HF
  pour éviter le téléchargement pendant la fenêtre service stoppé).

**Go/No-Go** : tous les checks verts → continuer. Sinon stop, investiguer.

---

## Étape 1 — Test pré-prod sur copie fraîche

Copie du palace, migration test, vérif sortie, cleanup. **Cette étape
est obligatoire** : valide que le script tourne sur les données prod
exactes avant d'y toucher.

```bash
TS=$(date +%Y%m%dT%H%M%S)
rsync -a ~/.mempalace/palace/ ~/.mempalace/palace_preprod_${TS}/
ls -lh ~/.mempalace/palace_preprod_${TS}/

./venv/bin/python scripts/migrate_embedder.py \
    --palace-path ~/.mempalace/palace_preprod_${TS} \
    --no-snapshot \
    2>&1 | tee /tmp/migrate_preprod_${TS}.log
```

**Attendu** dans le log :
- Header avec `from-model : all-MiniLM-L6-v2 (dim=384)` et
  `to-model : sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (dim=768)`.
- ÉTAPE B : `Nombre d'entrées : N` (noter N), `Dimension actuelle des vecteurs : 384`.
- ÉTAPE D : `Encodage terminé : N phrases en X.Xs → ~4-15 phrases/s`.
- ÉTAPE E : `Insertion terminée : N entrées en X.Xs`.
- ÉTAPE F : `✓ Count OK : N entrées.` + `✓ Dimension OK : 768.`.
- Ligne finale : `✓ Migration réussie : 'all-MiniLM-L6-v2' → '...-mpnet-base-v2' | N entrées | dim 384 → 768`.

```bash
./venv/bin/python -c "
import chromadb
c = chromadb.PersistentClient('/home/nico/.mempalace/palace_preprod_${TS}')
col = c.get_collection('mempalace_drawers')
res = col.peek(1)
print('count:', col.count(), '| dim:', len(res['embeddings'][0]))
"
# Attendu : count = N (= ÉTAPE B), dim = 768
```

**Cleanup copie pré-prod après validation** :

```bash
rm -rf ~/.mempalace/palace_preprod_${TS}
```

**Go/No-Go** : compte préservé, dim=768, exit code 0 → continuer.
Sinon stop, ne pas toucher au palace prod.

---

## Étape 2 — Arrêt service ARIA

```bash
sudo systemctl stop aria.service
systemctl is-active aria.service                  # attendu : inactive
sudo journalctl -u aria.service -n 5 --no-pager   # vérifier shutdown propre
```

**Attendu** : `inactive`, dernières lignes du log sans erreur de
shutdown.

**Go/No-Go** : service arrêté proprement → continuer.

---

## Étape 3 — Migration prod (dans tmux)

```bash
tmux new -s migrate
cd ~/Nextcloud/projects/aria
./venv/bin/python scripts/migrate_embedder.py \
    --palace-path ~/.mempalace/palace \
    2>&1 | tee /tmp/migrate_prod_$(date +%Y%m%dT%H%M%S).log
```

**Attendu** :
- ÉTAPE A : `Snapshot créé : .../mempalace_drawers_backup_YYYYMMDDTHHMMSSZ.tar.gz (~X Mo, ~Xs)`.
- ÉTAPES B-G : mêmes critères qu'en pré-prod (count préservé,
  dim 384 → 768, marker écrit).
- Durée totale : 3-5 minutes attendues.
- Exit code 0.

**En cas d'échec entre E et F** : le script déclenche le rollback
automatique via snapshot. Lire les lignes `[ROLLBACK]` : si
`Palace restauré depuis : ...tar.gz` apparaît → palace revenu à
l'état pré-migration, **passer à la procédure rollback en bas du
runbook**. Sinon (rollback échoué) → restauration manuelle depuis le
tar.gz, conserver le log pour post-mortem.

**Go/No-Go** : exit code 0 + `✓ Migration réussie` dans le log →
continuer. Sortir de tmux : `Ctrl-b d` (le log est persisté dans /tmp).

---

## Étape 4 — Vérification post-migration

```bash
du -sh ~/.mempalace/palace                        # taille ↑ vs étape 0 (vecteurs 2× plus grands)
ls -lh ~/.mempalace/mempalace_drawers_backup_*.tar.gz   # snapshot bien créé
cat ~/.mempalace/palace/.embedder-migration-marker      # hash SHA256 du modèle cible

./venv/bin/python -c "
import chromadb
c = chromadb.PersistentClient('/home/nico/.mempalace/palace')
col = c.get_collection('mempalace_drawers')
res = col.peek(1)
print('count:', col.count(), '| dim:', len(res['embeddings'][0]))
"
```

**Attendu** :
- `palace/` plus gros (vecteurs 768 vs 384).
- Au moins un fichier `mempalace_drawers_backup_*.tar.gz` présent.
- Marker existe, contient un hash hex 64 chars.
- `count = N` (identique à étape B), `dim = 768`.

**Go/No-Go** : tout conforme → continuer. Sinon → rollback (procédure
en bas).

---

## Étape 5 — Bascule `config.py` et commit

Appliquer le diff (cf. bloc en bas du runbook) :

```bash
cd ~/Nextcloud/projects/aria
# Éditer config.py:35 : remplacer "all-MiniLM-L6-v2" par
# "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
git diff config.py                                 # vérifier le diff
./venv/bin/python -c "from config import config; print(config.EMBEDDING_MODEL)"
# Attendu : sentence-transformers/paraphrase-multilingual-mpnet-base-v2

git add config.py
git commit -m "feat(sprint6): T-Embedder3 bascule EMBEDDING_MODEL → mpnet-multilingual"
git log --oneline -3
```

**Go/No-Go** : commit créé, sortie config.EMBEDDING_MODEL conforme →
continuer.

---

## Étape 6 — Redémarrage service ARIA

```bash
sudo systemctl start aria.service
sleep 3
systemctl is-active aria.service                  # attendu : active
sudo journalctl -u aria.service -n 30 --no-pager  # pas d'erreur au boot
```

**Attendu** : `active`, pas de `ERROR`/`Traceback`/`dim mismatch` dans
les logs de démarrage. Le chargement initial du modèle ajoute ~1-2s
au boot (premier `SentenceTransformer` du process).

**Go/No-Go** : service actif sans erreur → continuer. Sinon → rollback.

---

## Étape 7 — Test fumée Telegram

Dans un terminal séparé, laisser tourner :

```bash
sudo journalctl -u aria.service -f -o cat
```

Envoyer les 4 messages ci-dessous via Telegram, **un à la fois**, et
attendre la réponse complète avant le suivant. Observer le tail
`journalctl` en parallèle pour détecter `ERROR`, `Traceback`,
`dim mismatch`, latences anormales (> 5s côté retrieval).

| # | Message exact à envoyer | Cas couvert | Attendu (comportement + mémoires rappelées) |
|---|---|---|---|
| 1 | `Bonjour` | Salutation courte — vérif no-op embedding, soul.md respecté, latence stable, pas d'erreur log. | Réponse conversationnelle naturelle (soul.md), pas d'injection de mémoires hors-sujet. Latence < 3s. Aucun `ERROR` au log. |
| 2 | `Planifier des vacances en Normandie` | Cas piège bug #18 — bench M0 : ATTACH faux sur intent fantôme `Dans ma cuisine j'ai...` (oracle `réservation voyage` au rang 53/63). Post-M2 + Tâche A : oracle au rang 1 (score 0.578). | ATTACH sur intent `réservation voyage` (ou `voyage organisation`). Réponse cohérente sur voyage Normandie. Au log : score top-1 retrieval > 0.55 sur l'intent voyage. Si retour intent culinaire/jardin → No-Go (régression M2). |
| 3 | `Quelle recette aux lentilles et épinards je peux faire ?` | Fact-recall cuisine (T-Embedder1 C5_T2). Bench M0 : top-1 < 0.45 → CREATE. M2 : ATTACH ✓ sur `recettes santé culinaire` (R@3 M0 0.62 → M2 0.88 sur l'ensemble). | ATTACH sur intent `recettes santé culinaire`. La réponse devrait croiser une mémoire culinaire existante (intolérances, préférences si présentes en `aria_semantic` — sinon réponse générique côté agent). Si CREATE d'un nouvel intent culinaire → écart vs prédiction bench, à noter sans bloquer. |
| 4 | `Qu'est-ce que je peux cuisiner avec ce que j'ai dans ma cuisine ?` | Planning multi-mémoires (T-Embedder1 C5_T4). Bench pré-cleanup : pollué par intent fantôme `Dans ma cuisine j'ai...` au top-1 (M0 0.824, M2 0.892). Post-Tâche A (intent désactivé via `status=completed`) + M2 : ce cas devrait **enfin** ATTACHer sur un intent culinaire valide ou fait un CREATE propre. **Teste l'effet conjoint des deux fixes du sprint 6.** | Pas de top-1 sur `Dans ma cuisine j'ai...` (cleanup OK). ATTACH attendu sur `recettes santé culinaire` ou `méthodes de cuisson saines`, sinon CREATE propre. La réponse devrait évoquer plusieurs mémoires culinaires (inventaire, préférences). Si top-1 reste l'intent fantôme → No-Go (Tâche A insuffisante). |

**Go/No-Go global** : pour chacun des 4 messages — pas d'`ERROR` au
log, latence < 5s, comportement conforme à l'attendu. Si 3/4 OK avec
1 cas borderline sur C3 → Go partiel (noter, ne pas rollback). Si
C2 régresse (top-1 hors voyage) ou C4 reste pollué intent fantôme →
No-Go, rollback.

---

## Étape 8 — Critère Go/No-Go global et rollback

**Go global** ssi :
- Étape 4 : count préservé, dim 768, snapshot et marker présents.
- Étape 6 : service actif sans erreur de boot.
- Étape 7 : 4/4 ou 3/4 messages conformes (cf. tolérance ci-dessus),
  aucune erreur au log.

**Si Go** : laisser tourner ARIA 10-15 min en usage normal, surveiller
`journalctl -u aria -f -o cat` pour confirmer la stabilité avant de
considérer la migration close. Tâche T-Embedder3 terminée.

### Procédure rollback (si No-Go)

```bash
# 1. Arrêt service
sudo systemctl stop aria.service

# 2. Swap inverse via 2 rename séquentiels (même stratégie que le script)
cd ~/.mempalace
mv palace palace.rollback-failed-$(date +%Y%m%dT%H%M%S)
SNAPSHOT=$(ls -t mempalace_drawers_backup_*.tar.gz | head -1)
tar -xzf "$SNAPSHOT" -C .
ls -d palace                                       # vérifier que le palace est revenu

# 3. Revert commit config.py
cd ~/Nextcloud/projects/aria
git revert --no-edit HEAD                          # crée un commit de revert
./venv/bin/python -c "from config import config; print(config.EMBEDDING_MODEL)"
# Attendu : all-MiniLM-L6-v2

# 4. Redémarrage
sudo systemctl start aria.service
sleep 3
systemctl is-active aria.service                   # attendu : active
sudo journalctl -u aria.service -n 30 --no-pager   # pas d'erreur

# 5. Vérification palace post-rollback
./venv/bin/python -c "
import chromadb
c = chromadb.PersistentClient('/home/nico/.mempalace/palace')
col = c.get_collection('mempalace_drawers')
res = col.peek(1)
print('count:', col.count(), '| dim:', len(res['embeddings'][0]))
"
# Attendu : count = N (= étape B), dim = 384
```

**Conserver** : log `/tmp/migrate_prod_*.log`, le tar.gz, le palace
renommé `palace.rollback-failed-*` pour post-mortem. **Ne pas
relancer** la migration sans avoir identifié la cause de l'échec.

---

## Diff `config.py` (NON appliqué)

```diff
diff --git a/config.py b/config.py
index ...
--- a/config.py
+++ b/config.py
@@ -32,7 +32,7 @@ class Config:
     gemini_model: str = "gemini-2.0-flash"
     mistral_model: str = "mistral-small-latest"
     sambanova_model: str = "Meta-Llama-3.3-70B-Instruct"
-    EMBEDDING_MODEL = "all-MiniLM-L6-v2"
+    EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

     # ── Modèles vision ────────────────────────────────────────────────────────
     groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
```

**Message de commit suggéré** :

```
feat(sprint6): T-Embedder3 bascule EMBEDDING_MODEL → mpnet-multilingual

Active paraphrase-multilingual-mpnet-base-v2 (dim 768) en prod, en
remplacement de all-MiniLM-L6-v2 (dim 384). Migration du palace
exécutée via scripts/migrate_embedder.py (snapshot tar.gz + marker
d'idempotence). Validation : 4 tests Telegram conformes au runbook
docs/sprint6/runbook_t_embedder3.md.
```

**Caveat hard-codes restants** : `all-MiniLM-L6-v2` apparaît encore en
plusieurs endroits du repo, mais **aucun n'est un blocker pour la
prod** :

- `scripts/migrate_embedder.py` : valeur par défaut `--from-model`
  et registre `MODEL_EXPECTED_DIM`. Comportement souhaité (le script
  doit savoir migrer DEPUIS MiniLM).
- `scripts/embedder_bench/_models.py` : baseline de benchmark
  comparatif. Hors-prod.
- `docs/sprint6/audit_*.md`, `docs/sprint6/plan_migration_embedder.md`,
  `docs/sprint6/context_sprint_6_T-Embedder3_kickoff.md` : doc
  historique du sprint, ne pas réécrire.
- `tests/test_migrate_embedder.py` : tests unitaires du script (utilise
  MiniLM comme cas de figure). À conserver.

Pas de hard-code prod à corriger dans ce tour.
