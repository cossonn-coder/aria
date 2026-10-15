─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 19 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-15
**Tag de référence sortie**       : `sprint-18`
**État sprint 18**                : CLOS. Chaîne de fallback LLM refaite
  en 3 tronçons (`ab0fc98`, `9145969`, run live `edfb660`).
  Détail : `docs/sprint18/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 18 (rappel synthétique)

- Chaînes texte (4 rôles) : groq ×3 `qwen/qwen3.8-27b` → DeepSeek
  (`deepseek-flash`, `deepseek-v4-pro` pour REASONING, raisonnement
  désactivé via `extra`) → Anthropic `claude-haiku-4-5`.
- Réponse vide = échec → fallback (texte uniquement). Log de succès
  `[LLM] <provider> (<modèle>) a répondu.`
- Vision : groq ×3 `qwen/qwen3.8-27b` → DeepSeek, via `GroqVisionClient`.
  OpenRouter retiré du routage vision.
- Run live 2026-10-15 : groq répond à chaque appel texte, aucun 404,
  message 7-13 s contre 22-31 s avant [n=3 messages chacun].
  Mode image enrichi (`c'est quoi`) OK. **#42 fermée.**

─────────────────────────────────────────────────────────────────────────

## Cible sprint 19 : vision lisible (demande Nico)

Constats du run live sprint 18 (photos, `docs/sprint18/00_etat.md`) :

- Photo sans légende → réponse **en anglais**, **tronquée**. Le prompt
  sans légende est en anglais exprès (`llm/image_router.py:~133`) et la
  description est renvoyée brute ; `max_tokens: 512` en dur
  (`llm/vision/groq_vision.py:~57`).
- Photo légende descriptive (« Paysage savoyard ») → mode standard :
  le modèle de vision répond seul, sans mémoire. Il a inventé un
  « massif des Bornes » et un « café-buvette » (c'était un bain
  nordique). Consigne en cause probable : « Réponds directement à ce
  que l'utilisateur semble vouloir savoir » (`llm/image_router.py:~124`).
- Photo « c'est quoi » → mode enrichi : « C'est ta **maison de
  montagne** » — la photo est rattachée d'autorité à l'intent actif.
  Justesse non confirmée par Nico.
- **Aucun log** sur le chemin photo : ni succès vision, ni écriture
  mémoire ; les échecs vision passent par `print()`
  (`llm/image_router.py:~200`). Fournisseur vision non identifiable.

Règle de langue posée par Nico (2026-10-15) : **français par défaut,
sinon la langue dans laquelle Nico pose sa question.**

À trancher en conception : le mode standard doit-il passer lui aussi
par la chaîne LLM (mémoire, langue, ton ARIA) ou seulement changer de
prompt ; budget de tokens vision ; formulation anti-invention ;
périmètre des logs (succès vision, fournisseur, écriture mémoire).

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-15 (post sprint 18)

| #  | Sujet | Statut |
|----|-------|--------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6) | ouverts, non touchés |
| 17 | Semantic wings non câblées | ouvert, architectural |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet |
| 26 | Artefacts résiduels `~/.mempalace/` | partiellement résolue sprint 10 |
| 31 | Drift HNSW mécanique récurrent | ouvert |
| 32 | Digression Normandie → Belgique | à reconfirmer |
| 33 | Garde runbook `"mempalace-fork" in __file__` | ouvert, polish trivial |
| 35 | Tests dépendants de l'auto-sys.path pytest | ouvert |
| 36 | `LLMRouter.route()` inerte, jamais appelée | ouvert |
| 37 | `max_history_turns` compte des tours, l'API des messages | ouvert |
| 38 | Double présence épisodique / conversation dans le contexte | ouvert |
| 39 | executor/critic (phase `execution`) sans historique | ouvert |
| 40 | Embeddings inutiles sur `aria_conversation` (latence CPU, HNSW) | ouvert |
| 41 | `executor_agent.py`, `critic_agent.py` absents de l'inventaire des callers de `complete` | ouvert |
| 42 | Chaîne de fallback LLM moribonde + DeepSeek absent | **FERMÉE sprint 18** |
| 43 | `mempalace_mcp` logue en ERROR « No palace found » au 1er message après reset | ouvert, cosmétique |
| 44 | Génération d'images hors service (Pollinations timeout / 401, HF mort) | ouvert, sprint dédié (clé à créer par Nico) |
| 45 | Vision : réponse en anglais sans légende ; règle FR par défaut / langue de la question | **cible sprint 19** |
| 46 | Vision : `max_tokens: 512` en dur → réponses tronquées | **cible sprint 19** |
| 47 | Vision : aucun log de succès ; échecs via `print()` (`llm/image_router.py:~200`) | **cible sprint 19** |
| 48 | Vision : consigne avec légende pousse à deviner (inventions photo savoyarde) | **cible sprint 19** |
| 49 | Vision : MIME `image/png` en dur dans `GroqVisionClient` (photos Telegram en JPEG) | **cible sprint 19** |
| 50 | Vision : réponse vide ≠ échec → pas de fallback | **cible sprint 19** |
| 51 | Mode enrichi : photo rattachée d'autorité à un intent actif (« ta maison de montagne ») | à confirmer par Nico |
| 52 | `scripts/check_keys.py` teste des modèles retirés | ouvert |
| 53 | Config morte : `gemini_model`, `sambanova_*`, `cerebras_*`, `mistral_*`, `openrouter_vision_models`, `OpenRouterVisionClient` | ouvert |
| 54 | `LLMRole.REFLECTION` sans caller | ouvert |
| 55 | `CriticAgent` : sortie jamais lue (appel LLM sans effet) | ouvert |

Sujets de conception hors dettes (avis Claude, revue 2026-10-15) : pas
d'accès au monde extérieur (web/outils) ; pas de consolidation mémoire
(REFLECTION, `aria_semantic` #17, `extract_every_n_turns` inutilisé).

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-18` (tag sur le commit de clôture
  documentaire).
- Branche sprint 19 à créer (nom proposé : `feat/sprint19-vision`).
- Prochaine étape : `/conception sprint 19`.
