# Tronçon 01 — plafond + budget de l'historique conversationnel (#37/#38 reformulées)

Lire avant : `CLAUDE.md`, `docs/sprint33/00_etat.md`, `docs/sprint33/audit_historique.md` (§2-§5).

## Objectif

L'historique passé à l'analyst ne doit plus dépasser **6 000 car.** au total, aucun message
plus de **1 500 car.** Sur un `salut` après une analyse d'échecs, le payload passe de
36 813 à ≈ 11 500 car. (simulé) → Groq n'est plus sauté (`GROQ_MAX_PAYLOAD_CHARS = 12_000`).

## Fichier à toucher

`execution/routers/llm_router.py`, étape 1b (`_run_pipeline`, branche `else` de
`if metadata.get("skip_history")`, ≈ lignes 134-141) :

```python
conversation_history = self.mempalace_bridge.load_conversation_history(
    conversation_key, n=config.max_history_turns * 2,
)
log.info("conversation_history loaded key=%s messages=%d", ...)
```

## Comportement attendu

Juste après la lecture bridge, appliquer une petite fonction de module (ex. `_trim_history`) :

1. Parcourir les messages **du plus récent au plus ancien**.
2. Chaque `content` de plus de `HISTORY_MESSAGE_MAX_CHARS = 1_500` car. est coupé à cette
   longueur et suffixé ` […]`. Les autres clés du tour (`role`, `timestamp`) sont gardées.
3. Ajouter tant que le total des `content` reste ≤ `HISTORY_BUDGET_CHARS = 6_000` ; au premier
   message qui ferait dépasser, **s'arrêter** (fenêtre contiguë, pas de trou).
4. Rendre la liste en **ordre chronologique** (plus ancien → plus récent), comme le bridge.

- Les deux constantes sont au niveau du module `llm_router.py` (même idiome que
  `GROQ_MAX_PAYLOAD_CHARS` dans `llm/llm_router.py`), avec un commentaire court en français
  (sprint 33, raison : blocs enrichis d'échecs / web relus en historique). Pas de clé config.
- Le log devient `conversation_history loaded key=%s messages=%d chars=%d` (messages et
  caractères **après** plafonnement).
- Le namer (`user_turns[-1]` plus bas) lit l'historique plafonné : c'est voulu.

## Tests à ajouter (cas nominal)

Dans `tests/execution/test_llm_execution_router.py` (réutiliser `make_router()` et le motif
de `test_conversation_history_loaded_and_written`) :

- historique bridge = 3 échanges dont 3 messages user de 9 000 car. et des réponses courtes ;
  vérifier que `ctx.extra["conversation_history"]` : total des `content` ≤ 6 000, aucun
  `content` > 1 500 + len(" […]"), ordre chronologique conservé, et le dernier message du
  bridge est bien le dernier de la liste.

`test_conversation_history_loaded_and_written` (contenu court) doit rester vert sans
modification. `pytest tests/ -q` vert.

## Hors scope (ne PAS faire)

- Ne pas toucher `MempalaceBridge.load_conversation_history` (lecture brute, utilisée en n=2
  par `web_router` — reprise « lis la suite » via le marqueur du tour user — et par
  `cognitive_classifier`).
- Ne pas changer ce qui est **écrit** (`write_conversation_turn`, `write_interaction`), ni les
  routers échecs / web / image.
- Ne pas renommer `max_history_turns` (#37), ne pas toucher au `context_builder` (#38).
- Pas de `try/except` autour du plafonnement.

## Critère de fin

Test ajouté vert, `pytest tests/ -q` vert, commit local
`feat(sprint33) tronçon 01: plafond + budget de l'historique conversationnel`.
