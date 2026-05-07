# Décisions architecturales — Sprint 4
**Date : 2 mai 2026**
**Source : Réponses architecte aux Q1–Q7 de audit_memory_layer.md**

---

## Q1 — 70 entrées wing=`aria` : migrer vers `aria_episodic`

**Décision : oui, option (a), conditional.**

Le script `scripts/migrate_wing_aria_to_episodic.py` est **exploitable sans modification** :
- Dry-run par défaut, `--execute` pour appliquer
- Migre uniquement `wing="aria"`, préserve `aria_classifier`
- Batch de 100, vérification post-migration intégrée

**Condition d'exécution : ne pas lancer avant que le nouveau code d'écriture
soit en place et validé.** Sinon, le bug W4 (`llm_router.py` step 10 wing="aria")
continue de produire de nouvelles entrées mal routées, et la migration est à refaire.

Ordre d'opérations :
1. Corriger le bug W4 dans `llm_router.py`
2. Valider en run live que les nouvelles interactions écrivent dans `aria_episodic`
3. Exécuter : `./venv/bin/python scripts/migrate_wing_aria_to_episodic.py --execute`
4. Vérifier avec `count_memory_by_wing.py`

---

## Q2 — API d'écriture : couche d'adaptation ARIA

**Décision : couche d'adaptation interne `aria/memory/writer.py`.**

MemPalace est un paquet externe (`v3.3.0`, auteur `milla-jovovich`, MIT, GitHub).
ARIA est client — on ne PR pas upstream.

**Architecture cible :**

```
aria/memory/writer.py          ← nouveau module (remplace mempalace_writer.py)
    write_interaction(text, intent_id, intent_name, source) → None
    write_image_artifact(artifact, intent_id) → None
    write_semantic_fact(fact, subject, source) → None
    write_classifier_cache(message, operation, confirmed) → None
```

Règles :
- `wing` et `room` sont des **paramètres positionnels nommés de l'API**,
  jamais déductibles d'un spread `**metadata`
- Le caller ne passe plus de champ `wing` dans un dict arbitraire
- `mempalace.palace.get_collection()` reste l'accès bas niveau (pas d'API write publique MemPalace)

`mempalace_writer.py` existant : conserver pendant la migration (strangler pattern),
supprimer quand tous les callers ont migré vers `writer.py`.

---

## Q3 — `media/image_service.py` dead code

**Décision : hors scope sprint 4. Documenter comme dette.**

Nouvelle dette : `ImageService` (media/image_service.py) est non utilisée en prod —
uniquement référencée dans `tests/images/test_image_generation.py` et
`test_image_input.py`. Doublon fonctionnel avec `store_image_artifact()` dans
`mempalace_writer.py`. Supprimer dans un sprint de nettoyage dédié.

---

## Q4 — Défaut `wing="aria"` dans `mempalace_store.py`

**Décision : supprimer le défaut, paramètre obligatoire.**

`memory/mempalace_store.py:9` : `wing: str = "aria"` → `wing: str`.

Aucun caller prod ne s'appuie sur ce défaut (tous passent un wing explicite).
Forcer l'explicite protège contre les appels futurs accidentels sans wing.

---

## Q5 — `MemoryStack` (L0/L1/L2/L3) : non cible sprint 4

**Décision : ne pas adopter `MemoryStack` dans ce sprint.**

ARIA a sa propre architecture (intents + bridge + writer).
`MemoryStack` porte une vision différente (4 couches, identité statique, L1 auto-générée
depuis la mémoire brute). Les deux visions cohabitent mal.

Nommé comme **tension architecturale** à arbitrer ultérieurement (sprint 5+).
`MemoryStack` reste disponible dans le venv mais non importée par ARIA.

---

## Q6 — Classifier bypass du bridge : le classifier passe par le bridge

**Décision : étendre `MempalaceBridge.retrieve_memories()` avec paramètre `wing` explicite.**

`retrieve_memories()` reçoit déjà `wing: str = "aria_episodic"`. Il suffit que
`_search_cache()` appelle `bridge.retrieve_memories(query, wing="aria_classifier", n=1)`
au lieu d'importer `mempalace_store.search` directement.

La règle "un seul point d'accès en lecture" tient sans exception.
`MempalaceBridge` injecté dans `CognitiveEngine` ou passé à `classify_operation()`.

**Impact :** `cognitive_classifier.py` ne peut plus appeler `search()` directement
— la dépendance sur `mempalace_store` disparaît de ce module.

---

## Q7 — `scripts/migrate_wing_aria_to_episodic.py` : exploitable

**Décision : capitaliser sur le script existant, aucune réécriture.**

Script complet, testé (dry-run intégré). Cf. Q1 pour les conditions d'exécution.

---

## Récapitulatif des dettes nouvelles issues de cet audit

| Dette | Description | Priorité |
|---|---|---|
| #12 | `media/image_service.py` dead code — supprimer | nettoyage, sprint 5+ |
| #13 | Défaut `wing="aria"` dans `mempalace_store.py` — rendre obligatoire | sprint 4 (trivial) |
| #14 | Tension architecturale `MemoryStack` vs architecture ARIA — arbitrer | sprint 5+ |

Les dettes #11 (bug W4 wing="aria") et le bypass classifier (Q6) sont des
objectifs de développement du sprint 4, pas des dettes reportées.
