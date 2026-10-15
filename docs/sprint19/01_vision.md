# Sprint 19 — tronçon 01 : vision lisible (#45, #46, #47, #48, #49, #50)

À lire avant : `CLAUDE.md`, `docs/sprint19/00_etat.md`,
`docs/sprint19/audit_vision.md` §1-§2.

## Objectif

Une photo reçue produit une description **en français** (ou dans la
langue de la légende), **courte**, **sans invention**, jamais tronquée,
par DeepSeek en premier, avec des logs qui disent qui a répondu.

## Fichiers à toucher

### `llm/image_router.py`

1. **Ordre de `VISION_ROUTING_TABLE`** (l. 29-60) : entrée `deepseek`
   **en premier**, puis `groq1`, `groq2`, `groq3`. L'entrée DeepSeek
   reçoit `"extra": {"thinking": {"type": "disabled"}}` (mesuré : sans
   ça, `deepseek-flash` consomme ~900 tokens de raisonnement et la
   réponse est coupée). Mettre à jour le commentaire qui la présente
   comme « dernier recours ».
2. **`_dispatch`** (l. 176-205) : transmettre `extra=entry.get("extra")`
   au constructeur du client (tous les clients acceptent `**_`,
   vérifié : Pollinations, HF, Groq, OpenRouter). Remplacer le
   `print(...)` l. 200 par `log.warning("[IMAGE ROUTER FALLBACK] %s failed: %s", ...)`
   avec `from logger import get_logger; log = get_logger(__name__)` en
   tête de module.
3. **Prompts de `handle_input`** (l. 121-137) — intention :
   - sans légende : prompt **en français**, demande une description en
     **quelques phrases** (sujet principal, contexte, éléments notables),
     **uniquement ce qui est visible**, et de **dire son incertitude**
     plutôt que de deviner un objet ou un lieu. Réponse en français.
     Supprimer le commentaire « volontairement en anglais ».
   - avec légende : cite la légende ; demande de répondre en tenant
     compte de ce contexte, en quelques phrases, sans rien affirmer qui
     ne soit visible, en signalant l'incertitude ; **remplacer**
     « Réponds directement à ce que l'utilisateur semble vouloir savoir ».
     Règle de langue : répondre en français, sauf si la légende est
     écrite dans une autre langue → répondre dans cette langue.
   Formulation de référence mesurée (sans légende, 116-307 tokens,
   `finish: stop` sur 3 photos, groq et DeepSeek) :
   « Décris cette photo en français, en quelques phrases : sujet
   principal, contexte, éléments notables. Ne décris que ce qui est
   visible ; si tu n'es pas sûr de ce qu'est un élément ou un lieu,
   dis-le au lieu de deviner. »
   Contraintes des tests existants (`tests/images/tests_caption_pipeline.py:89-145`) :
   prompt sans légende sans « L'utilisateur » ni « message » ; prompt avec
   légende contient la légende et « contexte » ou « compte ».

### `llm/vision/groq_vision.py`

1. `__init__` : accepter `extra: dict | None = None`, stocké ; fusionné
   dans le payload JSON (`payload.update(self.extra or {})`).
2. `max_tokens` : 512 → **1024**.
3. MIME : déduit de l'extension du fichier (`mimetypes.guess_type`,
   repli `image/jpeg`) au lieu de `image/png` en dur (l. 44).
4. Réponse vide : si `content` est vide ou `None` → `raise ValueError`
   (le `_dispatch` passe alors au fournisseur suivant), comme
   `llm/llm_router.py` le fait depuis le sprint 18.
5. Log de succès : `log.info("[VISION] %s a répondu.", self.model)` —
   le provider n'est pas connu du client ; si c'est plus simple, logger
   dans `_dispatch` après succès :
   `log.info("[VISION] %s (%s) a répondu.", entry["provider"], entry.get("model"))`.
   Choisir **un** des deux emplacements (préférer `_dispatch`, qui a le
   provider).

### `execution/routers/image_router.py`

1. `log = get_logger(__name__)` au niveau module (`from logger import get_logger`),
   à la place des imports locaux dans `_handle_input`,
   `_handle_input_enriched`, `_handle_generation`, `_build_generation_context`
   (l. 122, 175, 227, 283) — uniquement ces 4 imports, rien d'autre.
2. Après `write_image_artifact` réussi dans `_handle_input` (l. 119-120) :
   `log.info("image_write OK wing=aria_episodic intent_id=%s", intent_id)`.
3. `[IMAGE ENRICHED]` (l. 177) : `log.error` → `log.info`.

## Tests

- `tests/images/test_vision_chain.py` : ordre attendu
  `["deepseek", "groq1", "groq2", "groq3"]` et l'entrée deepseek porte
  `extra == {"thinking": {"type": "disabled"}}`.
- Nouveau test (cas nominal, dans `tests/images/`) : un
  `GroqVisionClient` dont `httpx.post` (monkeypatch, cf.
  `tests/images/test_client_contract.py`) renvoie `content: ""` lève
  une exception ; et un `ImageRouter(vision_table=[vide, ok])` renvoie
  la description du second.
- Les tests existants de `tests/images/` doivent rester verts.

## Hors scope (ne PAS faire)

- Mode standard via la chaîne LLM (décision Q1 : non).
- Toute modification de `LLMExecutionRouter`, `AnalystAgent`, intents
  (tronçon 02).
- `GENERATION_ROUTING_TABLE`, génération d'images (dette #44).
- Suppression de `OpenRouterVisionClient` / config morte (dette #53).
- Écriture de la photo dans `aria_conversation` (dette à créer).

## Critère de fin

`pytest tests/ -q` vert. Vérification VM : script jetable (scratchpad)
qui appelle `ImageRouter().handle_input(ImageInput(path=<jpg>))` sans
mock sur une photo de `received_images/` (ex. la plus récente) ;
attendu : description **en français**, non coupée, log
`[VISION] deepseek (deepseek-flash) a répondu.`, aucun fallback. Même
script avec `caption="What is this?"` → réponse en anglais.
