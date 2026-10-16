─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 22 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-16
**Tag de référence sortie**       : `sprint-21`
**État sprint 21**                : CLOS. Robustesse réseau Telegram en 1
  tronçon de code (`7c2c072`) + run live 02 (OK).
  Détail : `docs/sprint21/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 21 (rappel synthétique)

- Démarrage sans réseau : `run_polling(bootstrap_retries=-1)`, plus de
  crash ni de relance systemd.
- Envoi : retry sur `NetworkError` dans `send()` (3 tentatives, 2 s puis
  4 s ; doublon possible accepté) ; `add_error_handler` → une ligne WARNING.
- Log INFO de réception `telegram_update update_id=… message_id=… type=…`
  (instrumente #63).
- Run live 02 (coupure `iptables`) : A, B, C conformes. **#62 fermée.**

─────────────────────────────────────────────────────────────────────────

## Cible sprint 22

À choisir par Nico en `/conception`. Candidats : #44 (génération d'images),
sujets hors dettes ci-dessous.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-16 (post sprint 21)

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
| 52 | `scripts/check_keys.py` teste des modèles retirés | ouvert |
| 53 | Config morte : `gemini_model`, `sambanova_*`, `cerebras_*`, `mistral_*`, `openrouter_vision_models`, `OpenRouterVisionClient` | ouvert |
| 54 | `LLMRole.REFLECTION` sans caller | ouvert |
| 55 | `CriticAgent` : sortie jamais lue (appel LLM sans effet) | ouvert |
| 56 | Mode enrichi : question en anglais → réponse en français (message enrichi majoritairement FR, `user.md` « Langue : français ») | ouvert, accepté par Nico |
| 58 | #51 option (b) : rattachement photo → intent sur correspondance forte | ouvert, seulement si perte de contexte projet constatée |
| 60 | Vision : lecture fine inventée (position d'échecs), limite modèle ; le LLM texte dit alors « je ne vois pas l'image » alors que la description est dans l'historique | ouvert, accepté (reformulée sprint 20) |
| 62 | Telegram : timeout réseau au démarrage → crash (relance systemd) ; timeout à l'envoi → réponse perdue, « No error handlers are registered » | **FERMÉE sprint 21** (bootstrap_retries, retry `send()`, error handler) |
| 63 | Photo analysée deux fois après redémarrage (23:16:01 / 23:16:18) — rejeu Telegram ou double envoi | instrumentée sprint 21 (log `telegram_update`), à confirmer |
| 64 | `IntentActionType.IGNORE` déclaré, jamais utilisé | ouvert, polish |
| 65 | `aria.service` versionné pointe `/home/nico/projects/aria` (installé : Nextcloud) | ouvert |
| 66 | Découpage 4096 de `send()` coupe au milieu des mots (commentaire faux) | ouvert, polish |
| 67 | IPv6 VM → Telegram injoignable | ouvert, piste si timeouts persistent |

Sujets de conception hors dettes (avis Claude, revue 2026-10-15) : pas
d'accès au monde extérieur (web/outils) ; pas de consolidation mémoire
(REFLECTION, `aria_semantic` #17, `extract_every_n_turns` inutilisé).

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-21` (tag sur le commit de clôture
  documentaire).
- Branche sprint 22 à créer en conception, une fois la cible choisie.
- Prochaine étape : `/conception sprint 22`.
