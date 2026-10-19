─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 27 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-19
**Tag de référence sortie**       : `sprint-26`
**État sprint 26**                : CLOS. Coach d'échecs en 4 tronçons de code
  (`7b3ad38`, `4ee056f`, `b3d79f0`, `9006900`) + runs live 04 et 06 (partiels).
  Détail : `docs/sprint26/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 26 (rappel synthétique)

- `chess_coach/` : analyse Stockfish 17.1 (`/usr/games/stockfish`), qualité des
  demi-coups (5 niveaux, % de gain Lichess), ≤ 3 positions critiques, notation FR,
  rendu PNG (Pillow + DejaVu), synthèse de partie (`summarize`).
- Opération `CHESS_ANALYSIS` (PGN avec en-tête, avant la règle URL),
  `execution/routers/chess_router.py` ; contrat router `images` (règle 4 amendée) ;
  Telegram : photos puis texte.
- Fiche `chess_game` (`write_chess_game`, `aria_episodic`, room `chess`, dédoublonnée
  par hash des coups UCI).
- Échange d'analyse écrit sous l'intent imposé `jeux echecs` (`forced_intent_name`) ;
  ancre « Partie contre <adversaire> <date> <ouverture> » en tête du bloc et de la réponse.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 27

Pressentie (décision Nico 2026-10-19) : **#87 coups conseillés « explosifs »**.
Arbitrages d'entrée à confirmer en `/conception` : périmètre avec #81 (bilan joueur) ;
rangement des fiches `chess_game` en wing `echecs` / room par ouverture (idée Nico).

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-19 (post sprint 26)

| #  | Sujet | Statut |
|----|-------|--------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6) | ouverts, non touchés |
| 17 | Semantic wings non câblées | ouvert, architectural |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet |
| 26 | Artefacts résiduels `~/.mempalace/` | partiellement résolue sprint 10 |
| 31 | Drift HNSW mécanique récurrent | ouvert — quarantaines `dba15bea…` aux runs live 25 (08:31:46) et 26-06 (11:12:57) |
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
| 52 | `scripts/check_keys.py` teste des modèles retirés | ouvert |
| 53 | Config morte : `gemini_model`, `sambanova_*`, `cerebras_*`, `mistral_*`, `openrouter_vision_models`, `OpenRouterVisionClient` | ouvert |
| 54 | `LLMRole.REFLECTION` sans caller | ouvert |
| 55 | `CriticAgent` : sortie jamais lue (appel LLM sans effet) | ouvert |
| 56 | Mode enrichi : question en anglais → réponse en français (message enrichi majoritairement FR, `user.md` « Langue : français ») | ouvert, accepté par Nico |
| 58 | #51 option (b) : rattachement photo → intent sur correspondance forte | ouvert, seulement si perte de contexte projet constatée |
| 60 | Vision : lecture fine inventée (position d'échecs), limite modèle ; le LLM texte dit alors « je ne vois pas l'image » alors que la description est dans l'historique | ouvert, accepté (reformulée sprint 20) |
| 63 | Photo analysée deux fois après redémarrage (23:16:01 / 23:16:18) — rejeu Telegram ou double envoi | instrumentée sprint 21 (log `telegram_update`), à confirmer |
| 64 | `IntentActionType.IGNORE` déclaré, jamais utilisé | ouvert, polish |
| 65 | `aria.service` versionné pointe `/home/nico/projects/aria` (installé : Nextcloud) | ouvert |
| 66 | Découpage 4096 de `send()` coupe au milieu des mots (commentaire faux) | ouvert, polish |
| 67 | IPv6 VM → Telegram injoignable | ouvert, piste si timeouts persistent |
| 68 | Rappels différés + envoi proactif (scheduler) | ouvert, sprint dédié |
| 70 | Météo dédiée (aujourd'hui via `web_search`) | ouvert |
| 71 | `print()` dans `core/kernel.py` `_normalize` | ouvert, polish |
| 72 | Code sans caller apparent : `cognition/cognitive_dispatcher.py`, `execution/execution_plan_builder.py`, `cognition/dispatcher_types.py` | ouvert |
| 73 | Groq 413 sur conversation chargée (ITPM `Limit 7000`) : depuis sprint 25, un 413 saute les autres Groq → DeepSeek répond 3 s après le 413 [run live 25-02, n=1, horodatage à la seconde] ; Groq reste inutilisable en REASONING dès que l'historique pèse (piste B « budget historique » écartée sprint 25) | partiellement résolue sprint 25 |
| 74 | Réponse hors sujet « Prochaine action : Résumer l'état actuel du projet potager… » à un message conversationnel (« lol non… ») [n=1, 2026-10-16] | ouvert, à diagnostiquer |
| 75 | Intent parasite `vacances normandie train` créé sur une question de suivi de lecture d'URL (« et la gastronomie normande… ») [n=1] | ouvert |
| 76 | Suite de lecture : la réponse refusionne la tranche 1 et parle de « trois parties » au lieu de deux [n=1] | ouvert, polish prompt |
| 77 | Image-to-image (photo + légende de génération) : Pollinations accepte `image=`, il faut une URL publique de la photo | ouvert |
| 78 | `llm/image_gen/hf_client.py` + `config.hf_image_model` morts (HF hors table depuis sprint 24) | ouvert, polish |
| 79 | Position d'échecs depuis une image (photo d'échiquier physique + capture d'écran) | ouvert |
| 80 | Relance moteur sur une position citée en texte libre (coups tapés sans en-tête : LLM seul, 15.Cg5+ conseillé à tort au run 06, SF d22 [1 run] : 15.exd6 +2,8) | ouvert |
| 81 | Bilan joueur / progression / déviations de répertoire (lecture des fiches `chess_game`) | ouvert, candidat sprint 27 |
| 82 | Questions d'ouverture sans PGN (LLM seul, hallucinations constatées) | ouvert |
| 83 | Lien de partie Chess.com → PGN via API publique | ouvert |
| 84 | Récit LLM inventé autour des coups (matériel / menaces absents du bloc enrichi) | ouvert |
| 85 | Positions critiques et meilleur coup instables entre deux analyses de la même partie (A : 16…Fe6 → 3…g6 ; F : 12.e5 → 38.Dc4+) [runs 04 et 06] | ouvert |
| 86 | 413 Groq systématique sur les échanges échecs, suivis compris (bloc enrichi dans l'historique > ITPM 7000) | ouvert |
| 87 | Coups conseillés « explosifs » : fenêtre de tolérance MultiPV + score pièges / forçants / déséquilibre / volatilité ; Maia (lc0) en v2 ; cas de test Nico dans `docs/sprint26/00_etat.md` | **cible sprint 27** (décision Nico) |
| 88 | Question de suivi « la position 1 de cette partie » répond sur une autre partie malgré l'ancre (run 06 C, n=1) ; hypothèse non vérifiée : historique pollué par la mauvaise réponse du run 04 | ouvert, à auditer |

Sujet de conception hors dettes (avis Claude, revue 2026-10-15) : pas de
consolidation mémoire (REFLECTION, `aria_semantic` #17,
`extract_every_n_turns` inutilisé).

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-26` (tag sur le commit de clôture documentaire).
- Branche sprint 27 à créer en conception.
- Prochaine étape : `/conception sprint 27`.
