# Plan de migration embedder — ARIA Sprint 6 · T-Embedder3

## 1. Objectif et contexte

La collection `mempalace_drawers` (655 entrées, backend ChromaDB persistant sous `~/.mempalace/palace/`) utilise actuellement `all-MiniLM-L6-v2` (dim 384). La migration vers `sentence-transformers/paraphrase-multilingual-mpnet-base-v2` (dim 768) est la dernière étape du sprint 6 embedder-audit. Elle est motivée par les mesures de T-Embedder1 : le R@3 sur le matching d'intents passe de 0.625 avec MiniLM à 1.000 avec mpnet-multilingual couplé au cleanup ghost (Tâche A). Ce document est le protocole d'exécution en prod. Lire, exécuter dans l'ordre, ne pas improviser.

---

## 2. Pré-requis avant exécution

Vérifier chaque point avant de continuer.

- [ ] Branche `feat/sprint6-embedder-audit` checkoutée et à jour (`git pull`)
- [ ] Tâche A (cleanup ghost intents) appliquée sur `intents.json` et committée
- [ ] Tâche B (suppression chroma_db legacy) mergée dans la branche
- [ ] Tâche C (audit hard-codes dim 384) lue — zéro blocker confirmé
- [ ] Test sur copie déjà effectué en T-Embedder2 D : count post-migration == 655, dim == 768, rollback testé, idempotence testée
- [ ] Espace disque disponible sur la partition hébergeant `~/.mempalace` : au moins 2× la taille actuelle du répertoire `palace/` (snapshot + nouvelle collection)

```bash
du -sh ~/.mempalace/palace/
df -h ~/.mempalace/
```

- [ ] Dépendances présentes dans le venv

```bash
./venv/bin/pip show chromadb sentence-transformers tqdm | grep -E "^Name|^Version"
```

- [ ] Service ARIA arrêté (voir étape 3.1)

---

## 3. Procédure d'exécution pas-à-pas

### 3.1 Arrêt du service

```bash
sudo systemctl stop aria
sudo systemctl status aria
```

Résultat attendu : `Active: inactive (dead)`. Si le service reste `active`, attendre 10 secondes et relancer. Ne pas continuer tant qu'il est up.

---

### 3.2 Test sur copie pré-prod (dernier filet)

```bash
cp -r ~/.mempalace ~/.mempalace.preprod-test

./venv/bin/python scripts/migrate_embedder.py \
    --palace-path ~/.mempalace.preprod-test/palace \
    --no-snapshot
```

Log attendu (extrait) :

```
... [INFO] ARIA — migrate_embedder.py
... [INFO]   palace-path : /home/nico/.mempalace.preprod-test/palace
... [INFO]   from-model  : all-MiniLM-L6-v2 (dim=384)
... [INFO]   to-model    : sentence-transformers/paraphrase-multilingual-mpnet-base-v2 (dim=768)
...
... [INFO] ✓ Count OK : 655 entrées.
... [INFO] ✓ Dimension OK : 768.
... [INFO] ✓ Migration réussie : 'all-MiniLM-L6-v2' → '...-mpnet-base-v2' | 655 entrées | dim 384 → 768
```

**Ça a marché** : les trois lignes `✓` présentes, exit code 0.  
**Ça ne va pas** : n'importe quel `[ERROR]` ou `[CRITICAL]`, exit code non-zéro, ou count/dim incorrects. Dans ce cas, stopper et investiguer avant de toucher à la prod.

Vérification manuelle rapide post-test :

```bash
./venv/bin/python - <<'EOF'
import chromadb, os
c = chromadb.PersistentClient(path=os.path.expanduser("~/.mempalace.preprod-test/palace"))
col = c.get_collection("mempalace_drawers")
r = col.peek(1)
print("count:", col.count(), "| dim:", len(r["embeddings"][0]))
EOF
```

Attendu : `count: 655 | dim: 768`.

Cleanup de la copie :

```bash
rm -rf ~/.mempalace.preprod-test
```

---

### 3.3 Migration en prod

**Obligatoirement dans un screen ou tmux** — une fermeture de terminal pendant l'étape E (delete/add) laisserait la collection dans un état indéterminé sans rollback automatique.

```bash
screen -S aria-migration
# ou : tmux new -s aria-migration

./venv/bin/python scripts/migrate_embedder.py \
    --palace-path ~/.mempalace/palace
```

Le snapshot sera créé automatiquement. Noter le chemin logué :

```
... [INFO] Snapshot créé : /home/nico/.mempalace/mempalace_drawers_backup_YYYYMMDDTHHMMSSZ.tar.gz (X.X Mo, X.Xs)
```

**Conserver ce chemin** — il sera nécessaire si rollback manuel.

Durée estimée : 2–5 minutes selon la charge CPU (encodage de 655 phrases avec mpnet-multilingual).

**Ça a marché** : ligne finale `✓ Migration réussie`, exit code 0, marker présent.  
**Ça ne va pas** : lignes `[ROLLBACK]` dans les logs — voir section 5.

---

### 3.4 Validation post-migration

```bash
./venv/bin/python - <<'EOF'
import chromadb, os
from pathlib import Path

palace = os.path.expanduser("~/.mempalace/palace")
c = chromadb.PersistentClient(path=palace)
col = c.get_collection("mempalace_drawers")
r = col.peek(1)

print("count :", col.count())
print("dim   :", len(r["embeddings"][0]))
print("id[0] :", r["ids"][0])
print("meta  :", r["metadatas"][0])
marker = Path(palace) / ".embedder-migration-marker"
print("marker:", marker.read_text().strip()[:12], "..." if marker.exists() else "ABSENT")
EOF
```

Valeurs attendues : `count: 655`, `dim: 768`, marker présent.

---

### 3.5 Bascule de `EMBEDDING_MODEL` dans `config.py`

Éditer le fichier de configuration (commit **séparé** du reste du sprint) :

```python
# config.py
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
```

```bash
git add config.py
git commit -m "config: bascule EMBEDDING_MODEL vers mpnet-multilingual (T-Embedder3)"
```

---

### 3.6 Redémarrage du service

```bash
sudo systemctl start aria
sudo systemctl status aria
```

Attendu : `Active: active (running)`. Vérifier aussi les premières lignes de log du service :

```bash
sudo journalctl -u aria -n 50 --no-pager
```

Aucune `DimensionMismatchError` ni `InvalidDimensionException` ne doit apparaître.

---

### 3.7 Test fumée Telegram

Envoyer trois messages à ARIA depuis Telegram, dans l'ordre :

1. `"c'est quoi une bonne recette de tarte aux poireaux ?"` → intent attendu : cuisine / recette
2. `"tu connais Lisbonne ?"` → intent attendu : voyage / destination
3. `"salut !"` → intent attendu : salutation / small-talk
4. `"Planifier des vacances en Normandie"` → intent attendu : réservation voyage / voyage organisation

Dans les logs du service (`journalctl -u aria -f`), vérifier l'absence de toute erreur liée aux dimensions et la présence de lignes confirmant le matching d'intent (format propre à ARIA).

---

## 4. Validation post-migration en prod — critères chiffrés

| Critère | Valeur attendue |
|---|---|
| `collection.count()` | 655 |
| `len(embedding[0])` | 768 |
| Peek 1 entrée | ids, documents, metadatas non vides |
| Marker `.embedder-migration-marker` | présent, hash non vide |
| Journalctl post-démarrage | zéro `DimensionMismatch` |
| Test fumée Telegram (3 messages) | intents matchés, aucune erreur dim |

---

## 5. Procédure de rollback en prod

### Scénario A — Erreur pendant la migration (étapes E ou F)

Le script déclenche le rollback automatiquement et logge :

```
... [ERROR] [ROLLBACK] Tentative de restauration depuis snapshot…
... [INFO]  [ROLLBACK] Palace restauré depuis : /home/nico/.mempalace/mempalace_drawers_backup_...tar.gz
```

Vérifier le retour à l'état initial :

```bash
./venv/bin/python - <<'EOF'
import chromadb, os
c = chromadb.PersistentClient(path=os.path.expanduser("~/.mempalace/palace"))
col = c.get_collection("mempalace_drawers")
r = col.peek(1)
print("count:", col.count(), "| dim:", len(r["embeddings"][0]))
EOF
```

Attendu après rollback : `count: 655 | dim: 384`. Si ce n'est pas le cas, passer au scénario B (restauration manuelle depuis le snapshot).

---

### Scénario B — Erreur après migration, avant bascule `config.py`

`config.py` est toujours sur MiniLM — pas de modification nécessaire. Restaurer uniquement le palace depuis le snapshot :

```bash
SNAPSHOT="/home/nico/.mempalace/mempalace_drawers_backup_YYYYMMDDTHHMMSSZ.tar.gz"  # adapter
cd ~/.mempalace
rm -rf palace/
tar -xzf "$SNAPSHOT"
```

Puis relancer le service :

```bash
sudo systemctl start aria
```

---

### Scénario C — Erreur découverte après bascule `config.py` et redémarrage

Tâche C — pas d'intégration code.
audit hard-codes effectué, 0 blocker, voir audit DeepSeek docs/sprint6/audit_deepseek_embedder.md

```bash
# 1. Stopper le service
sudo systemctl stop aria

# 2. Revenir sur config.py
git revert HEAD   # ou git checkout HEAD~1 -- config.py selon le workflow

# 3. Restaurer le palace depuis le snapshot
SNAPSHOT="/home/nico/.mempalace/mempalace_drawers_backup_YYYYMMDDTHHMMSSZ.tar.gz"  # adapter
cd ~/.mempalace
rm -rf palace/
tar -xzf "$SNAPSHOT"

# 4. Relancer
sudo systemctl start aria

# 5. Vérifier
sudo journalctl -u aria -n 30 --no-pager
```

Vérifier ensuite le count/dim via le snippet Python du §3.4 : `count: 655 | dim: 384`.

---

## 6. Limites connues et zones de fragilité

**Pagination ChromaDB.** Le script pagine la lecture avec `offset=`. Ce paramètre n'est pas garanti stable sur toutes les versions de ChromaDB. Si l'étape D produit un comportement erratique (count lu ≠ 655, boucle infinie), vérifier en premier :

```bash
./venv/bin/pip show chromadb | grep Version
```

Versions validées : ≥ 0.4.x. En dessous, mettre à jour avant de relancer.

**Marker non lié à la révision HuggingFace.** Le marker hash le *nom* du modèle, pas le SHA du commit HuggingFace. Si HF publie une révision silencieuse de `paraphrase-multilingual-mpnet-base-v2`, le marker ne le détectera pas. À surveiller manuellement si une régression de qualité apparaît post-migration.

**Charge mémoire.** Le script charge les 655 embeddings reconstruits (768 × 4 octets × 655 ≈ 1.9 Mo) intégralement en RAM. Négligeable aujourd'hui, problème à réévaluer si la collection dépasse ~50 000 entrées (dette future documentée dans ARIA backlog).

**Kill brutal entre E et F.** Si le process reçoit un SIGKILL entre la suppression de la collection (étape E) et la validation (étape F), le rollback automatique ne se déclenche pas. Le snapshot reste intact sur disque — rollback manuel via scénario B. C'est la raison pour laquelle l'exécution sous `screen` ou `tmux` est **obligatoire**.
