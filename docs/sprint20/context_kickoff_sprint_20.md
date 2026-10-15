─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 20 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-15
**Tag de référence sortie**       : `sprint-19`
**État sprint 19**                : CLOS. Vision lisible en 4 tronçons
  (`195aced`, `e6bf64a`, `2ec9bae` + runs live 03 et 05).
  Détail : `docs/sprint19/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 19 (rappel synthétique)

- Vision : DeepSeek `deepseek-flash` d'abord (raisonnement coupé), groq ×3
  en secours. Prompts FR sobres, anti-invention, `max_tokens` 1024, MIME
  par extension, réponse vide = échec. Logs `[VISION] <provider> (<modèle>)
  a répondu.`, `image_write OK`, `[IMAGE ENRICHED]`.
- Photo avec question (mode enrichi) : aucune résolution/mutation d'intent
  (`metadata["skip_intent"]`) ; consigne « ne rattache à un projet que si
  justifié ; sinon, ne mentionne pas ses projets » ; règle de langue FR+EN.
- Run live 05 : pas de mention parasite des projets ; lien tomates justifié
  sur la photo du châssis ; « What's this? » répond encore en français
  (accepté, #56). **#45-#51 fermées.**

─────────────────────────────────────────────────────────────────────────

## Cible sprint 20

À choisir par Nico en `/conception`. Candidats issus du sprint 19 : #59
(intents parasites sur relances texte), #60 (inventions en mode texte),
#57 (photo absente de l'historique en mode standard). Autres : #44
(génération d'images), sujets hors dettes ci-dessous.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-15 (post sprint 19)

| #  | Sujet | Statut |
|----|-------|--------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6) | ouverts, non touchés |
| 17 | Semantic wings non câblées | ouvert, architectural |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet |
| 26 | Artefacts résiduels `~/.mempalace/` | partiellement résolue sprint 10 |
| 31 | Drift HNSW mécanique récurrent | ouvert — nouvelle quarantaine au run live 05 (2026-10-15 22:08) |
| 32 | Digression Normandie → Belgique | à reconfirmer |
| 33 | Garde runbook `"mempalace-fork" in __file__` | ouvert, polish trivial |
| 35 | Tests dépendants de l'auto-sys.path pytest | ouvert |
| 36 | `LLMRouter.route()` inerte, jamais appelée | ouvert |
| 37 | `max_history_turns` compte des tours, l'API des messages | ouvert |
| 38 | Double présence épisodique / conversation dans le contexte | ouvert |
| 39 | executor/critic (phase `execution`) sans historique | ouvert |
| 40 | Embeddings inutiles sur `aria_conversation` (latence CPU, HNSW) | ouvert |
| 41 | `executor_agent.py`, `critic_agent.py` absents de l'inventaire des callers de `complete` | ouvert |
| 43 | `mempalace_mcp` logue en ERROR « No palace found » au 1er message après reset | ouvert, cosmétique |
| 44 | Génération d'images hors service (Pollinations timeout / 401, HF mort) | ouvert, sprint dédié (clé à créer par Nico) |
| 45 | Vision : réponse en anglais sans légende ; règle FR par défaut / langue de la question | **FERMÉE sprint 19** |
| 46 | Vision : `max_tokens: 512` en dur → réponses tronquées | **FERMÉE sprint 19** |
| 47 | Vision : aucun log de succès ; échecs via `print()` (`llm/image_router.py:~200`) | **FERMÉE sprint 19** |
| 48 | Vision : consigne avec légende pousse à deviner (inventions photo savoyarde) | **FERMÉE sprint 19** |
| 49 | Vision : MIME `image/png` en dur dans `GroqVisionClient` (photos Telegram en JPEG) | **FERMÉE sprint 19** |
| 50 | Vision : réponse vide ≠ échec → pas de fallback | **FERMÉE sprint 19** |
| 51 | Mode enrichi : photo rattachée d'autorité à un intent actif (« ta maison de montagne ») | **FERMÉE sprint 19** |
| 52 | `scripts/check_keys.py` teste des modèles retirés | ouvert |
| 53 | Config morte : `gemini_model`, `sambanova_*`, `cerebras_*`, `mistral_*`, `openrouter_vision_models`, `OpenRouterVisionClient` | ouvert |
| 54 | `LLMRole.REFLECTION` sans caller | ouvert |
| 55 | `CriticAgent` : sortie jamais lue (appel LLM sans effet) | ouvert |
| 56 | Mode enrichi : question en anglais → réponse en français (message enrichi majoritairement FR, `user.md` « Langue : français ») | ouvert, accepté par Nico |
| 57 | Mode standard : la photo n'est pas écrite dans `aria_conversation` (relance texte sans la photo dans l'historique) | ouvert |
| 58 | #51 option (b) : rattachement photo → intent sur correspondance forte | ouvert, seulement si perte de contexte projet constatée |
| 59 | Relances texte après photo : intents parasites créés (`evaluation position`, `abandon des noirs`) | ouvert |
| 60 | Mode texte : invention de détails absents de la description (position d'échecs inventée) | ouvert |
| 61 | Intent supprimé (« maison de montagne ») encore cité via l'historique conversationnel | ouvert, hypothèse non vérifiée |


Sujets de conception hors dettes (avis Claude, revue 2026-10-15) : pas
d'accès au monde extérieur (web/outils) ; pas de consolidation mémoire
(REFLECTION, `aria_semantic` #17, `extract_every_n_turns` inutilisé).

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-19` (tag sur le commit de clôture
  documentaire).
- Branche sprint 20 à créer en conception, une fois la cible choisie.
- Prochaine étape : `/conception sprint 20`.
