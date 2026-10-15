# Sprint 20 — tronçon 01 : photo en mode standard dans l'historique (#57)

## Objectif

Une photo traitée en mode standard (légende absente ou non interrogative)
doit apparaître dans `aria_conversation`, pour qu'une relance texte
(« évalue la position », « pourtant les noirs abandonnent ici ») voie la
description. Aujourd'hui seul le mode enrichi y écrit (via
`LLMExecutionRouter`, `execution/routers/llm_router.py` l. 253-260).

## Fichier à toucher

`execution/routers/image_router.py`, méthode `_handle_input` (l. 92-142).
Le mode standard est le `return {"text": artifact.caption or ""}` final
(l. 142), atteint aussi quand la légende est interrogative mais la
description vision vide.

## Comportement attendu

Juste avant ce `return` du mode standard :

- clé : `conversation_key = str(payload.get("metadata", {}).get("chat_id", "default"))`
  (même convention que `llm_router.py` l. 180 ; `chat_id` arrive déjà dans
  `payload["metadata"]` depuis `interfaces/telegram_interface.py` l. 105).
- tour **user** (décision Q3, format du mode enrichi) :
  `f"[Analyse visuelle : {description}]"`, suivi de `"\n\n" + légende`
  si la légende utilisateur existe.
- tour **assistant** : la description (`artifact.caption or ""`), soit
  exactement le texte renvoyé à Nico.
- écriture via `write_conversation_turn` (import depuis `memory.writer`,
  règle inviolable 1), non bloquante : même motif que `llm_router.py`
  l. 255-260 (`try` / `log.info("conversation_write OK key=%s", …)` /
  `except Exception: log.exception("conversation_write ERROR key=%s", …)`).

Le mode enrichi ne change pas : il écrit déjà via `LLMExecutionRouter`
(ne pas écrire deux fois).

Mettre à jour le commentaire d'en-tête du module (pipeline mode standard)
et la docstring de `_handle_input` en une ligne chacun.

## Tests (cas nominal)

`tests/images/test_interrogative_vision_pipeline.py`, classe
`TestImageRouterEnrichedMode` (helpers `_router`, `_payload` existants) :

- 1 test : légende descriptive + `metadata={"chat_id": 42}` →
  `write_conversation_turn` (patché sur `execution.routers.image_router`)
  appelé 2 fois : `("42", "user", <contient "[Analyse visuelle : " + description et la légende>)`
  puis `("42", "assistant", description)`.

Les tests existants du mode standard n'ont pas besoin de patch :
`tests/conftest.py` redirige `config.mempalace_path` vers `tmp_path`
(autouse). Ne pas ajouter d'assertion sur le mode enrichi.

## Hors scope (ne PAS faire)

- Ne pas toucher `is_interrogative_caption` (« évalue la position » reste
  en mode standard) ni les prompts vision (#60 hors sprint).
- Ne pas écrire dans `aria_conversation` depuis le mode enrichi ni depuis
  `_handle_generation`.
- Pas de garde sur description vide.

## Critère de fin

`pytest tests/ -q` vert (258 + 1). Diff limité à `image_router.py` et au
fichier de test.
