# Sprint 18 — état (chaîne de fallback LLM, dette #42)

**Phase** : B figée le 2026-10-15 → prêt pour `/sprint-auto sprint 18`
**Branche** : `feat/sprint18-llm-catalog`
**Docs** : `context_kickoff_sprint_18.md` (cadrage), `audit_chaine_llm.md` (audit 2026-10-15)

## Carte des tronçons

| # | Kickoff | Qui | État |
|---|---|---|---|
| 01 | `01_chaine_texte.md` — chaînes groq → DeepSeek → Anthropic, `extra`, réponse vide = échec, log de succès | /sprint-auto | ✅ |
| 02 | `02_vision.md` — vision groq qwen3.8 → DeepSeek | /sprint-auto | ✅ |
| 03 | `03_run_live.md` — conversation + 2 photos | Nico | ⏳ |

## Décisions arrêtées (2026-10-15, Nico)

- Q1 chaînes texte : groq ×3 `qwen/qwen3.8-27b` → DeepSeek → Anthropic
  `claude-haiku-4-5`. DeepSeek = `deepseek-flash` (CHAT, PLANNING,
  REFLECTION), `deepseek-v4-pro` (REASONING), raisonnement désactivé
  (`thinking: {type: disabled}`). Mistral, OpenRouter, Cerebras sortent
  des chaînes texte (clés conservées dans `config.py`). REFLECTION
  (sans caller) alignée sur CHAT.
  Raison : seuls groq, DeepSeek et Anthropic répondent aujourd'hui ;
  Cerebras 402, Mistral quota épuisé, OpenRouter free saturé.
- Q2 : réponse vide ou absente = échec → fallback. Champ optionnel
  `extra` par entrée de chaîne, fusionné dans le payload.
  Raison : un modèle à raisonnement renvoie `''` sur petit budget
  (audit §3) et le router actuel le prend pour un succès.
- Q3 : vision dans le sprint. Chaîne : groq ×3 `qwen/qwen3.8-27b` →
  DeepSeek `deepseek-flash`, client `GroqVisionClient` (OpenAI générique).
  OpenRouter retiré, pas d'Anthropic vision.
- Q4 : génération d'images (hors service, audit §7) → sprint dédié, dette #44.
  Raison : nécessite que Nico choisisse un service et crée une clé.
- Découpage : 01 chaîne texte, 02 vision, 03 run live.
- Revue agents (audit §6) : les 4 agents et les 2 callers non-agents
  passent par les 4 rôles, tous couverts par la même structure de chaîne.

## Dettes à reporter au kickoff sprint 19

- #42 : fermée si le run live passe.
- #44 : génération d'images hors service (Pollinations timeout / 401,
  HF domaine mort + FLUX.1-schnell 410).
- `llm/image_router.py:199` utilise `print()` (règle projet).
- `scripts/check_keys.py` teste des modèles retirés.
- Config morte : `gemini_model`, `sambanova_*`, et désormais
  `cerebras_*`, `mistral_*`, `openrouter_vision_models`, `OpenRouterVisionClient`.
- `LLMRole.REFLECTION` sans caller.
- `CriticAgent` : sortie jamais lue (appel LLM sans effet).
- Sujets de conception (avis Claude, revue du 2026-10-15) : pas d'accès
  au monde extérieur (web/outils) ; pas de consolidation mémoire
  (REFLECTION, `aria_semantic` #17, `extract_every_n_turns` inutilisé).

## §REPRISE

Tronçon 01 ✅ (2026-10-15, non commité à la sortie du sous-agent) :
`ROUTING_TABLE` construite par `_text_chain(deepseek_model)` (groq ×3 →
deepseek → anthropic), `extra` fusionné dans le payload OpenAI-compatible,
réponse vide → `ValueError` → fallback (OpenAI-compat et Anthropic), log de
succès OpenAI-compat. pytest 254 verts (+2 :
`tests/llm/test_empty_response_fallback.py`). Vérif VM sans mock : les
4 rôles répondent via `groq (qwen/qwen3.8-27b)`, aucun `[LLM FALLBACK]` ;
appels directs `_call` OK sur deepseek-flash, deepseek-v4-pro,
claude-haiku-4-5.

Tronçon 02 ✅ (2026-10-15, non commité à la sortie du sous-agent) :
`groq_vision_model` = `qwen/qwen3.8-27b` ; `VISION_ROUTING_TABLE` = groq ×3
→ deepseek (`GroqVisionClient`, `config.deepseek_model`) ; entrée et import
OpenRouter retirés de `llm/image_router.py`. pytest 255 verts (+1 :
`tests/images/test_vision_chain.py`). Vérif VM sans mock (PNG synthétique,
un disque rouge) : chaîne complète → description non vide via groq, aucun
`[IMAGE ROUTER FALLBACK]` ; DeepSeek seul → description non vide et exacte.
Observation : groq qwen3.8 a décrit « trois cercles rouges » au lieu d'un
[n=1] — qualité à juger au run live. Prochaine étape : run live 03 (Nico).
