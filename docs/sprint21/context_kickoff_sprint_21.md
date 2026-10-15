─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 21 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-15
**Tag de référence sortie**       : `sprint-20`
**État sprint 20**                : CLOS. Relances après photo en 2 tronçons
  de code (`2359a4f`, `07a890c`) + runs live 03 (partiel) et 04 (OK).
  Détail : `docs/sprint20/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 20 (rappel synthétique)

- Photo en mode standard écrite dans `aria_conversation` (user =
  `[Analyse visuelle : …]` + légende, assistant = description) → une
  relance texte voit la photo.
- Namer contextuel : reçoit le tour user précédent et les intents actifs ;
  répond un nom existant (→ rattachement), un nouveau nom, ou « aucun »
  (→ `intent SKIPPED reason=namer_aucun`, pas d'écriture épisodique).
  Appelé seulement en create/split ; `SPLIT` dédoublonne par nom.
- Données : 4 intents parasites passés en `status: "abandoned"` dans
  `~/.aria/intents.json` (sauvegarde `.bak-sprint20`). Actifs : tomates,
  docker.
- Run live bis : relances échecs → `namer_aucun` ; terreau → tomates.
  **#57, #59, #61 fermées.**

─────────────────────────────────────────────────────────────────────────

## Cible sprint 21

À choisir par Nico en `/conception`. Candidats : #62 (robustesse réseau
Telegram), #44 (génération d'images), sujets hors dettes ci-dessous.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-15 (post sprint 20)

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
| 57 | Mode standard : la photo n'est pas écrite dans `aria_conversation` | **FERMÉE sprint 20** |
| 58 | #51 option (b) : rattachement photo → intent sur correspondance forte | ouvert, seulement si perte de contexte projet constatée |
| 59 | Relances texte après photo : intents parasites créés | **FERMÉE sprint 20** (namer « aucun » + parasites `abandoned`) |
| 60 | Vision : lecture fine inventée (position d'échecs), limite modèle ; le LLM texte dit alors « je ne vois pas l'image » alors que la description est dans l'historique | ouvert, accepté (reformulée sprint 20) |
| 61 | Intent supprimé encore cité via l'historique | **FERMÉE sprint 20** sans code (symptôme éteint sprint 19) |
| 62 | Telegram : timeout réseau au démarrage → crash (relance systemd) ; timeout à l'envoi → réponse perdue, « No error handlers are registered » | ouvert (run live bis 2026-10-15) |
| 63 | Photo analysée deux fois après redémarrage (23:16:01 / 23:16:18) — rejeu Telegram ou double envoi | à confirmer |
| 64 | `IntentActionType.IGNORE` déclaré, jamais utilisé | ouvert, polish |

Sujets de conception hors dettes (avis Claude, revue 2026-10-15) : pas
d'accès au monde extérieur (web/outils) ; pas de consolidation mémoire
(REFLECTION, `aria_semantic` #17, `extract_every_n_turns` inutilisé).

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-20` (tag sur le commit de clôture
  documentaire).
- Branche sprint 21 à créer en conception, une fois la cible choisie.
- Prochaine étape : `/conception sprint 21`.
