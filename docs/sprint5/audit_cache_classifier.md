# Audit cache classifier — dette #20

**Sprint 5 / T1 — audit lecture seule, aucun fix.**
**Amendé en T2** : §4 schéma cible mis à jour suite au spot-check
bridge (Option A confirmée — operation portée par `room`, pas par
`metadata.operation`). Cf. §8 point 7.

Le cache classifier (~199 entrées dans `aria_classifier`) ne hit jamais en
prod. Cause acquise en T7-bis-6 du sprint 4 :

- `write_classifier_cache` (memory/writer.py:170) indexe le document
  `json.dumps({"message": M, "operation": O})`.
- `_search_cache` (cognition/cognitive_classifier.py:259) cherche avec
  `query=M` (message brut).
- Cosine similarity 0.47-0.60 sur des messages strictement identiques
  (vérifié par `scripts/diagnose_classifier_cache_similarity.py`).
  Seuil métier 0.92 → jamais de hit.

Cet audit prépare le fix T2 : indexer le message brut, porter
`operation` via le `room` (cf. §4 amendé).

---

## 1. Callers de `write_classifier_cache`

Grep dans `aria/`, `tests/`, `scripts/`. Trois sites total (hors
définition et hors import).

### cognition/cognitive_classifier.py:309 (prod, indirect via `_store_cache`)

```python
306  def _store_cache(message: str, operation: CognitiveOperation, confirmed: bool = False):
307      """Stocke un mapping message → operation dans le cache classifier."""
308      try:
309          write_classifier_cache(message, operation.value, confirmed=confirmed)
310      except Exception as e:
```

`_store_cache` lui-même est appelé en deux endroits du module :
- ligne 239 dans `classify_operation` (cache LLM-confirmed)
- ligne 256 dans `store_confirmed_operation` (cache user-confirmed)

### tests/memory/test_writer.py:140 (test fonctionnel)

```python
139  def test_write_classifier_cache_wing_and_document_format(fake_col):
140      w.write_classifier_cache("Tu te rappelles des carottes ?", "fact_recall")
141      meta = fake_col.last_meta
142      assert meta["wing"] == "aria_classifier"
```

### tests/memory/test_writer.py:161 (test garde-fou type)

```python
159      class FakeEnum(Enum):
160          FOO = "foo"
161      with pytest.raises(TypeError):
162          w.write_classifier_cache("msg", FakeEnum.FOO)
```

**Synthèse :** un seul caller prod (`_store_cache`), deux callers de
test. Refactor T2 contenu.

---

## 2. Callers de `_search_cache`

Fonction privée (`_`-prefix). Un seul caller, dans le même module.

### cognition/cognitive_classifier.py:212

```python
210      # ── 4. Cache MemPalace ───────────────────────────────────────────────────
211      cached = _search_cache(message, bridge)
212      if cached:
213          return cached
```

Aucun import externe de `_search_cache` détecté. Refactor T2 strictement
local au module.

Les tests appellent `classify_operation` (qui appelle `_search_cache` en
interne) — voir §5.

---

## 3. Inventaire metadata actuelles

Lecture directe de la collection ChromaDB via
`col.get(where={"wing":"aria_classifier"}, limit=3, include=['documents','metadatas'])`.

### Format du document indexé

```
{"message": "créé un programme de remise en forme pour un homme de 39ans",
 "operation": "planning"}
```

JSON sérialisé, 100 % des entrées suivent ce format. C'est la chaîne qui
est embeddée par ChromaDB, donc la cible des recherches cosinus.

### Clés metadata observées (3 entrées)

| Clé           | Type   | Valeur typique                          | Origine             |
|---------------|--------|-----------------------------------------|---------------------|
| `wing`        | str    | `"aria_classifier"`                     | writer.py:188       |
| `room`        | str    | `"classifier_cache"`                    | writer.py:189       |
| `type`        | str    | `"classifier_cache"`                    | writer.py:190       |
| `timestamp`   | str    | `"2026-04-22T09:39:59.478304+00:00"`    | writer.py:191       |
| `confirmed`   | bool   | `False`                                 | writer.py:192       |
| `hall`        | str    | `"general"`                             | **legacy** (palace) |
| `intent`      | str    | `"classifier_cache"`                    | **legacy** (palace) |

### Champs cibles absents

- `operation` → **pas en metadata aujourd'hui**. Vit uniquement dans le
  document JSON. C'est le levier du fix T2.
- `message` → idem, vit dans le JSON. Sera promu en document.

### Doc_id observés

```
interaction_classifier_cache_394a8520
interaction_classifier_cache_9594a0b2
interaction_classifier_cache_2d019b5b
```

Format `interaction_<intent_id>_<sha256[:16]>`, posé par
`_idempotent_doc_id(json_text, "classifier_cache")` (writer.py:185).
Le préfixe `interaction_` est hérité de `_idempotent_doc_id` qui
préfixe tout — sans rapport avec le type. Pas de coût à conserver.

---

## 4. Schéma cible — AMENDÉ T2 (Option A après spot-check bridge)

**Découverte spot-check T2** : ni `MempalaceBridge.retrieve_memories()` ni
le wrapper `mempalace_store.search()` ne propagent `metadata` dans les
hits. Le store sous-jacent (`mempalace.searcher.search_memories`, package
externe) extrait seulement `wing`, `room`, `source_file`, `created_at`.
Une approche `metadata.operation` aurait nécessité de patcher le bridge
ou d'ajouter une méthode dédiée. **Option retenue** : porter `operation`
via le `room` — déjà propagé par le store, aucun patch infra
nécessaire, room joue son rôle sémantique uniformément avec les autres
wings (aria_episodic.room=intent_id, aria_semantic.room=subject,
aria_classifier.room=operation).

| Aspect                         | Avant                                              | Après (Option A)                            | Justification |
|--------------------------------|----------------------------------------------------|---------------------------------------------|---------------|
| `documents=[…]` indexé         | `json.dumps({"message": M, "operation": O})`       | `M` (message brut)                          | Aligne ce qui est embedé en écriture avec ce qui est embedé en recherche. Cause directe du bug. |
| `metadata.room`                | `"classifier_cache"` (uniforme, sans information)  | `operation` (str, ex `"fact_recall"`)       | Propagé tel quel par le store dans `hit["room"]`. Récupérable sans `json.loads` ni dépendance metadata. |
| `_search_cache` lecture        | `data = json.loads(hit["text"]); op = data["operation"]` | `op = hit["room"]`                    | Plus simple, plus robuste. Aucune dépendance sur le format document. |
| `_idempotent_doc_id` clé       | `_idempotent_doc_id(json_text, "classifier_cache")` | `_idempotent_doc_id(message, "classifier_cache")` | Doc_id stable sur la fenêtre 60 s pour un même message. Préfixe `intent_id="classifier_cache"` conservé pour cohérence (cf. §6). |
| `metadata.confirmed`           | `bool`                                             | `bool` (inchangé)                           | Champ métier, pas impacté. |
| `metadata.wing/type/timestamp` | inchangés                                          | inchangés                                   | Schéma structurel posé après le spread `extra` (règle CLAUDE.md #1). |

**Forme cible de l'upsert** (T2) :

```python
col.upsert(
    documents=[message],          # M brut, embedé directement
    ids=[doc_id],                 # _idempotent_doc_id(message, "classifier_cache")
    metadatas=[{
        "wing": "aria_classifier",
        "room": operation,         # ← Option A : room porte l'operation
        "type": "classifier_cache",
        "timestamp": _now_iso(),
        "confirmed": confirmed,
    }],
)
```

**Forme cible de la lecture** (T2) :

```python
hit = hits[0]
if hit.get("similarity", 0) < 0.92:
    return None
return _parse_operation(hit.get("room", "unknown"))
```

---

## 5. Tests existants à adapter

### Adaptation triviale (mock à mettre à jour)

| Fichier | Test | Impact |
|---------|------|--------|
| `tests/memory/test_writer.py` | `test_write_classifier_cache_wing_and_document_format` | Remplacer `data = json.loads(fake_col.last_doc); assert data["message"] == ...` par `assert fake_col.last_doc == "Tu te rappelles des carottes ?"` et ajouter `assert fake_col.last_meta["operation"] == "fact_recall"`. |
| `tests/memory/test_writer.py` | `test_write_classifier_cache_rejects_non_string_operation` | Le contrat `operation: str` est conservé. Test inchangé sauf si la signature évolue (ex : on accepte enum côté caller). À garder tel quel par défaut. |
| `tests/mempalace/test_mempalace_bridge.py` | `test_retrieve_memories_max_distance_none_skips_filter` | Aucune ligne de logique à changer. Le commentaire mentionne le cache classifier — éventuellement rafraîchir le commentaire en T2, sans urgence. |

### Adaptation substantielle (logique de mock à revoir)

| Fichier | Test | Impact |
|---------|------|--------|
| `tests/cognition/test_classifier_bridge_cache.py` | `_make_bridge` (helper, lignes 13-21) + 4 tests qui en dépendent | Le helper construit `{"hits": [{"similarity": ..., "text": json.dumps({"message": ..., "operation": ...})}]}`. **Post-Option A**, `_search_cache` lit `hit["room"]`. Helper réécrit : `{"hits": [{"similarity": ..., "room": operation, "text": "test"}]}`. Tests impactés : `test_classify_operation_uses_bridge_cache`, `test_classify_operation_skips_cache_below_threshold`. Tests inchangés : `test_classify_operation_no_bridge_skips_cache`, `test_classify_operation_bridge_empty_hits`. |

### Tests **non** impactés (vérifiés)

- `tests/cognition/test_classifier_ingestion_removed.py` — porte sur le
  prompt LLM et le `_ROUTING_TABLE`, pas sur le cache.
- `tests/images/test_interrogative_vision_pipeline.py` — utilise
  `is_interrogative_caption`, pas de cache.
- `tests/images/test_image_generation_kernel.py` — appelle
  `classify_operation` mais via l'heuristique IMAGE_GENERATION (étape 2,
  avant le cache).

---

## 6. Dette d'idempotence

Question : changer `_idempotent_doc_id(json_text, ...)` →
`_idempotent_doc_id(message, ...)` crée-t-il des collisions plausibles ?

**Réponse : non.** Analyse cas par cas :

1. **Même message classifié deux fois en < 60 s, même operation** : même
   doc_id, upsert idempotent, pas de doublon. Comportement identique à
   aujourd'hui.

2. **Même message classifié deux fois en < 60 s, operation différente**
   (cas théorique : LLM stochastique, prompt instable) : même doc_id,
   le second upsert remplace le premier. **C'est le comportement
   désirable** — la classification la plus récente gagne, plutôt que
   d'avoir deux entrées contradictoires en cache.

3. **Même message à > 60 s d'écart** : doc_ids différents (bucket
   change). Deux entrées en base — déjà le cas aujourd'hui (cf. §3,
   entrées 1 et 2 sont quasi-identiques avec doc_ids distincts). Non
   régression.

4. **Messages différents qui mappent vers la même operation** : doc_ids
   différents (sha256 sur le message), aucune collision. Conforme.

Aucune réécriture nécessaire au-delà du paramètre passé.

---

## 7. Script de wipe — spécification seule

**Fichier cible** : `scripts/wipe_classifier_cache.py` (à créer en T2).

**Pourquoi un wipe et pas une migration in-place** : les ~199 entrées
existantes ont leur document encodé en JSON et n'ont pas
`metadata.operation`. Une migration nécessiterait `json.loads` + upsert
sur chaque entrée — coût équivalent au wipe + reconstruction
incrémentale par le pipeline normal, sans bénéfice (ces entrées sont
inerte aujourd'hui puisque le cache ne hit jamais). Wipe net est plus
sûr.

**Spec fonctionnelle** :

```
1. count_before = col.get(where={"wing": "aria_classifier"}, include=[]) → len(ids)
2. col.delete(where={"wing": "aria_classifier"})
3. count_after  = col.get(where={"wing": "aria_classifier"}, include=[]) → len(ids)
4. Assert count_after == 0, log explicite
5. Log dans docs/sprint5/audit_cache_classifier.md (section "Exécution wipe T2")
   ou fichier dédié docs/sprint5/wipe_log.md à arbitrer en T2
6. Mode dry-run par défaut (--execute pour write réel), pattern hérité de
   scripts/migrate_wing_aria_to_episodic.py
```

**Garde-fous** :

- Drapeau `--execute` obligatoire pour écriture (confirme l'intention).
- Sortie console structurée : `BEFORE: N entries`, `AFTER: 0 entries`.
- Pas de `--all-wings` ni d'autre élargissement de scope.
- Pas de `try/except Exception` masquant — laisser remonter les erreurs
  ChromaDB.

**Hors scope T2** : pas de notion de backup avant wipe. Les entrées sont
inerte donc leur perte est sans conséquence métier. Si un backup est
souhaité, le mentionner explicitement à T2.

---

## 8. Surprises / points d'attention

1. **Pollution metadata legacy.** Les entrées actuelles portent `hall`
   et `intent` (= `"classifier_cache"`) qui ne sont plus posés par le
   writer actuel (memory/writer.py:170-195). C'est de l'héritage de
   l'ancien `mempalace_writer.py` (avant strangler pattern sprint 4).
   Argument supplémentaire en faveur d'un wipe (§7) : repartir d'un
   schéma propre.

2. **Wrapper `memory.mempalace_store.search()` filtre les metadata.**
   Une lecture via ce wrapper retourne `metadata: {}` même quand
   ChromaDB en stocke. Pour cet audit j'ai dû passer par
   `col.get(include=['metadatas'])` directement. **À ne pas confondre
   avec un schéma vide en base.**

3. **Le test `_make_bridge` actuel mocke `text=json.dumps(...)` sans
   metadata.** Il "fonctionne" parce que `_search_cache` parse le
   document. Après fix Option A, le mock doit poser `room=operation`.
   Refactor nécessaire au mock, pas seulement à l'assertion.

4. **`scripts/diagnose_classifier_cache_similarity.py` deviendra
   obsolète après T2.** Sa raison d'être était de prouver le mismatch
   (étape 2 du diagnostic T7-bis). Archivage prévu dans
   `scripts/archive/` en T2.

5. **Divergence chemin docs.** La spec T1 demande
   `docs/sprint_5/audit_cache_classifier.md` mais le dossier existant
   est `docs/sprint5/` (sans underscore, contenant déjà
   `context_sprint_5_kickoff.md`). J'ai écrit dans `docs/sprint5/`
   pour cohérence. Renommer si besoin.

6. **Aucun caller indirect surprise.** Le grep complet
   (`aria/`, `tests/`, `scripts/`, `memory/`, `cognition/`) ne révèle
   aucun appel à `write_classifier_cache` ou `_search_cache` en dehors
   des sites listés §1 et §2. Surface de fix T2 : 2 fichiers prod
   (`memory/writer.py`, `cognition/cognitive_classifier.py`) + 2 tests
   à adapter.

7. **Spot-check T2 — bridge ne propage pas la metadata complète.**
   `MempalaceBridge.retrieve_memories()` est un passe-plat sur
   `mempalace_store.search()` qui appelle
   `mempalace.searcher.search_memories()` (package venv,
   non modifiable). Cette dernière construit chaque entry avec
   `text/wing/room/source_file/created_at/similarity/distance` — pas
   de clé `metadata` dans les hits. Conclusion :

   - **Option retenue (A)** : porter `operation` via `room` (déjà
     propagé). Aucun patch infra nécessaire, schéma minimaliste,
     room sémantiquement aligné avec les autres wings.
   - Options B (méthode bridge dédiée `retrieve_classifier_cache`)
     et C (wrapper `search()` étendu) écartées : plus invasives sans
     bénéfice fonctionnel.

   Ce point a invalidé le schéma initial §4 (metadata.operation) et
   conduit à l'amendement T2 ci-dessus.
