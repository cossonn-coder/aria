# Sprint 18 — tronçon 02 : chaîne vision

À lire avant : `CLAUDE.md`, `docs/sprint18/00_etat.md`,
`docs/sprint18/audit_chaine_llm.md` §1.d et §4. Le tronçon 01 est fait
(`config.deepseek_api_key`, `config.deepseek_model` existent).

## Objectif

La vision est entièrement cassée : groq `llama-4-scout` 404, modèles
OpenRouter retirés. Mesuré le 2026-10-15 sur une image de test :
groq `qwen/qwen3.8-27b` 200 en 0,46 s [n=1] et DeepSeek `deepseek-flash`
200 en 1,5 s [n=1], au format OpenAI `image_url` en data URL.

## Fichiers à toucher

### `config.py`

`groq_vision_model` → `"qwen/qwen3.8-27b"`. Ne pas supprimer
`openrouter_vision_models` (hors scope).

### `llm/image_router.py`

`VISION_ROUTING_TABLE` (l. 30-59) devient : groq1, groq2, groq3
(inchangés hormis le modèle via config) → entrée DeepSeek :

```python
{
    "provider": "deepseek",
    "client": GroqVisionClient,
    "model": config.deepseek_model,
    "base_url": "https://api.deepseek.com/chat/completions",
    "api_key": lambda: config.deepseek_api_key,
},
```

`GroqVisionClient` est un client OpenAI-compatible générique : pas de
nouveau client. L'entrée OpenRouter sort de la table ; retirer l'import
`OpenRouterVisionClient` de `llm/image_router.py` s'il devient inutilisé.
**Ne pas supprimer** `llm/vision/openrouter_vision.py`
(`tests/images/test_architecture_rules.py` l'importe).

## Tests

Les tests `tests/images/` monkeypatchent `VISION_ROUTING_TABLE` : ils
doivent rester verts. Ajouter un test minimal : la table vision contient
une entrée `deepseek` après les trois groq.

## Hors scope

- `print()` de `_dispatch` (l. 199) : dette, ne pas toucher.
- Génération d'images (`GENERATION_ROUTING_TABLE`) : dette #44.
- Pas de paramètre `extra` / `thinking` dans `GroqVisionClient` : à
  512 tokens, `deepseek-flash` répond correctement (mesuré).

## Critère de fin

pytest vert. Vérification VM : script jetable (scratchpad) qui appelle
`ImageRouter().handle_input(ImageInput(path=<png de test>))` sans mock ;
attendu : description non vide, pas de `[IMAGE ROUTER FALLBACK]`.
