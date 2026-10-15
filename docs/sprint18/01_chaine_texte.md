# Sprint 18 — tronçon 01 : chaîne texte (modèles, DeepSeek, réponse vide = échec)

À lire avant : `CLAUDE.md`, `docs/sprint18/00_etat.md`,
`docs/sprint18/audit_chaine_llm.md` §1-3 et §6.

## Objectif

Remplacer, dans `ROUTING_TABLE` de `llm/llm_router.py`, des chaînes de
fallback mortes (modèles retirés, Cerebras 402, Mistral quota épuisé,
OpenRouter saturé) par une chaîne qui répond : groq ×3 → DeepSeek →
Anthropic. Empêcher qu'une réponse vide soit prise pour un succès.

## Fichiers à toucher

### `config.py`

- Clés API : ajouter `deepseek_api_key: str = ""` et, dans
  `__post_init__`, `self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY", "")`
  (la variable existe déjà dans `.env`).
- Modèles texte : `groq_model` → `"qwen/qwen3.8-27b"`. Ajouter
  `deepseek_model: str = "deepseek-flash"` et
  `deepseek_reasoning_model: str = "deepseek-v4-pro"`.
- Ne pas toucher aux autres clés ni à `cerebras_model`, `mistral_model`,
  `gemini_model`, `sambanova_*` (dette, hors scope).

### `llm/llm_router.py`

1. `ROUTING_TABLE` (l. 40-151) : les 4 rôles deviennent :

   | Rôle | Chaîne (ordre) |
   |---|---|
   | CHAT, PLANNING, REFLECTION | groq, groq_2, groq_3 (`config.groq_model`) → deepseek (`config.deepseek_model`) → anthropic `claude-haiku-4-5` |
   | REASONING | groq, groq_2, groq_3 → deepseek (`config.deepseek_reasoning_model`) → anthropic `claude-haiku-4-5` |

   Entrée DeepSeek : `"provider": "deepseek"`,
   `"base_url": "https://api.deepseek.com"`,
   `"api_key": lambda: config.deepseek_api_key`,
   `"extra": {"thinking": {"type": "disabled"}}`.
   Les entrées groq et anthropic gardent leur forme actuelle.
   Mistral, OpenRouter et Cerebras disparaissent de la table.
   La chaîne CHAT doit **commencer par `groq` puis `groq_2`** :
   `tests/llm/test_negative_cache.py` en dépend.
   Supprimer le commentaire périmé `# ... reste inchangé` (l. 85).
   La façon d'éviter la répétition (liste partagée, fonction) est
   libre, tant que ça reste simple.

2. `_call`, branche OpenAI-compatible (l. 395-425) :
   - fusionner `provider_cfg.get("extra", {})` dans `payload` après sa
     construction ;
   - si `content` est `None` ou vide après `.strip()`, lever une
     exception (`ValueError` avec provider et `finish_reason`) → le
     fallback de `complete()` prend le relais ;
   - ajouter un log de succès calqué sur celui d'Anthropic :
     `log.info("[LLM] %s (%s) a répondu.", provider, provider_cfg["model"])`.
   - Même contrôle de contenu vide côté branche Anthropic (l. 384).
   **Ne pas changer la signature de `_call`** : les tests la
   monkeypatchent avec `(self, prompt, provider_cfg, temperature, max_tokens)`.

### `execution/routers/image_router.py`

l. 158, docstring de `_handle_input_enriched` : « REASONING est aussi le
rôle LLM le plus puissant (Cerebras qwen-3-235b) » devient faux. Remplacer
par le modèle DeepSeek de REASONING, sans toucher au reste.

## Tests à ajouter (cas nominal)

Dans `tests/llm/` (nouveau fichier ou fichier existant) :
- réponse OpenAI-compatible avec `content` vide → `complete()` passe
  au provider suivant (mock HTTP, pas de réseau) ;
- l'entrée `extra` est fusionnée dans le payload envoyé.

`pytest tests/ -q` vert, y compris `test_negative_cache.py` et
`test_llm_router_messages.py`.

## Hors scope

- `config.py` : suppression des clés/modèles morts.
- `scripts/check_keys.py`, `bin/`.
- `LLMRouter.route()` (#36), `CriticAgent` (sortie non lue).
- Vision (`llm/image_router.py`) : tronçon 02.
- Pas de nouveau rôle, pas de modification des agents ni de leurs `max_tokens`.

## Critère de fin

pytest vert. Vérification VM : un script jetable (scratchpad, pas commité)
appelle `LLMRouter().complete("Dis bonjour.", role=…)` pour les 4 rôles,
avec `max_tokens=20`, sans mock. Attendu : réponse non vide, log
`[LLM] groq (qwen/qwen3.8-27b) a répondu.`, aucun `[LLM FALLBACK]`.
