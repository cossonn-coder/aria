# Sprint 20 — tronçon 02 : namer contextuel, « aucun » possible (#59)

## Objectif

ARIA juge si un message mérite un intent, comme un humain : une relance
de projet se rattache au projet, un nouveau projet durable crée un
intent, une question ponctuelle ou une remarque n'en crée **aucun**.
Aujourd'hui tout message sous le seuil cosine crée un intent : 4 intents
sur 5 en prod sont parasites (audit `audit_relances_photo.md` §3).

Décisions (00_etat Q2, Q5) : le recall cosine reste **inchangé** (message
seul, seuil 0.45) ; le contexte passe par le namer LLM, uniquement quand
le recall propose `create` ou `split`. Pas de concaténation d'embeddings
(mesure : faux rattachements, voir 00_etat).

## Fichiers à toucher

1. `llm/intent_namer.py` (29 lignes) — `NAMER_PROMPT`, `extract_intent_name`.
2. `execution/routers/llm_router.py` — `_run_pipeline` (l. 99-266).
3. `intent/intent_engine.py` — `apply`, branche `SPLIT` (l. 177-188).

## Comportement attendu

### `extract_intent_name`

Nouvelle signature (seul caller : `llm_router.py` l. 142) :

```python
def extract_intent_name(message, llm_router, previous_message=None,
                        active_intent_names=()) -> str | None
```

Le prompt reçoit : la liste des intents actifs (ou « (aucun) »), le
message précédent de l'utilisateur (ou « (aucun) »), le message. Consigne,
en substance :

- si le message prolonge un des projets listés (directement ou via le
  message précédent), réponds **exactement** le nom de ce projet ;
- si c'est un nouveau projet ou objectif durable de l'utilisateur
  (quelque chose qu'il compte faire, apprendre, suivre), réponds son sujet
  en 2 à 5 mots (règles de forme actuelles conservées) ;
- sinon (question ponctuelle, relance sans projet, remarque, bavardage),
  réponds `aucun`.

Exemples à garder/ajouter : « je veux partir en normandie en train » →
`vacances normandie train` ; « aide moi à apprendre docker » →
`apprentissage docker` ; « il fait beau aujourd'hui » → `aucun` ;
« évalue la position » (précédent : photo d'échiquier) → `aucun` ;
« combien de pieds pour la surface ? » (précédent : tomates cerises
balcon, projet listé `plantation tomates balcon est`) →
`plantation tomates balcon est`.

Réponse normalisée (`strip().lower()`) égale à `aucun` → retourne `None`.
Le reste du comportement est conservé (troncature 60, fallback
`message[:60]` sur réponse vide ou exception). `max_tokens=20` suffit.

### `LLMExecutionRouter._run_pipeline`

- Déplacer le chargement de l'historique (bloc 4c, l. 175-187) **avant**
  le bloc 2-3 (l. 119-148), sans le dupliquer : `conversation_history`
  est chargé une seule fois et reste passé à l'agent comme aujourd'hui.
- `previous_message` = contenu du **dernier** tour `role == "user"` de
  `conversation_history` (l'historique ne contient pas encore le message
  courant), `None` si absent.
- Appeler le namer quand `recall_decision.action in ("create", "split")`
  (aujourd'hui `create` seulement), avec `previous_message` et les noms de
  `active_intents` (déjà calculé l. 129).
- Si le namer renvoie `None` : ne **pas** appeler `apply`, `intent = None`,
  `log.info("intent SKIPPED reason=namer_aucun")`. La suite du pipeline
  gère déjà `intent is None` (chemin éprouvé par `skip_intent`, sprint 19 :
  `retrieve_by_intent` sauté, `write_interaction` sauté avec
  `memory_write SKIPPED reason=no_intent_resolved`, conversation écrite).

### `IntentEngine.apply`, branche `SPLIT`

Appliquer à `SPLIT` le même dédoublonnage par nom que `CREATE`
(l. 136-153 : `_find_by_name` puis `_find_by_name_semantic` quand
`intent_name` est fourni), pour qu'un nom existant renvoyé par le namer
rattache aussi en cas de split. Création inchangée sinon.

## Tests (cas nominal)

- `tests/execution/test_llm_execution_router.py` (helper `make_router`) :
  `intent_engine.resolve` → `MagicMock(action="create")`, namer patché
  (`execution.routers.llm_router.extract_intent_name`) → `None` :
  `intent_engine.apply` non appelé, `write_interaction` non appelé.
- Nouveau `tests/llm/test_intent_namer.py` (ou fichier existant s'il y en
  a un) : `llm_router.complete` mocké renvoyant `content="Aucun"` →
  `None` ; et le prompt envoyé contient un nom d'intent actif et le
  message précédent.

## Hors scope (ne PAS faire)

- Ne pas modifier `IntentRecallEngine` (seuil, embeddings, IGNORE mort).
- Ne pas nettoyer `~/.aria/intents.json` (décision Q6 : les 4 intents
  parasites restent).
- Ne pas toucher le prompt `AnalystAgent` ni `soul.md`.
- Pas de nouvel appel LLM : le namer reste l'unique appel, au même endroit.

## Critère de fin

`pytest tests/ -q` vert. Diff limité aux 3 fichiers + tests.
