─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 28 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-19
**Tag de référence sortie**       : `sprint-27`
**État sprint 27**                : CLOS (run live 10 partiel, clôture décidée par Nico).
  Tronçons de code `ed7d4de`, `e2d267c`, `c3ecf3c`, `8ebc367`, `9f5f8fa`, `1cfee01`,
  `3114235` ; runs live 03, 07 KO, 10 partiel. Détail : `docs/sprint27/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 27 (rappel synthétique)

- `chess_coach/explosive.py` : sorte d « occasion explosive » (MultiPV 5 ∪ coups par
  forme, score sacrifice + forçant + piège + volatilité, sacrifice réel sur ligne
  stabilisée), en bonus (n'évince jamais a/b/c), flèche orange ; budget ≤ 30 s.
- Sorte e « tournant » (erreur adverse ≥ 15 punie), ordre a/b, e, c ; seuil du coup
  unique 15 ; repli « pire coup » supprimé ; ouverture assumée (a/b ≥ 20 avant le coup 10).
- `clear_advantage` (`chess_coach/analysis.py`) : variantes coupées au 1er avantage clair
  (≤ 10 demi-coups sauf suite forcée, borne 16) ; position écartée sans avantage clair.
- Router : format court (ancre, 1 à 3 phrases par position, ligne « Niveau : »), faits
  calculés (`matériel :`, `attaquées :`), notation anglaise (`_to_english`), en-têtes PGN
  indentés acceptés. Stockfish Threads=8 Hash=256.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 28

Pressentie (Nico, conception sprint 27) : **modèle joueur** (fusion #81) — axes de travail
façon RPG (acquis après 3 validations, maîtrisé si jamais raté, priorité qui remonte en
cas d'échec) + appréciation du style (mal joué / passif / solide / brillant) sur
l'historique ; retour des axes de travail dans la réponse d'analyse. À concevoir comme
premier usage de la consolidation mémoire (#17 `aria_semantic`, #54 REFLECTION,
`extract_every_n_turns`). **Touche le palace prod.**
Arbitrage d'entrée : traiter ou non les résidus texte du sprint 27 (#89-#92) avant.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-19 (post sprint 27)

| #  | Sujet | Statut |
|----|-------|--------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6) | ouverts, non touchés |
| 17 | Semantic wings non câblées | ouvert, architectural |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet |
| 26 | Artefacts résiduels `~/.mempalace/` | partiellement résolue sprint 10 |
| 31 | Drift HNSW mécanique récurrent | ouvert — quarantaines `dba15bea…` aux runs live 25 (08:31:46), 26-06 (11:12:57) et 27-10 (19:01:56) |
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
| 81 | Bilan joueur / progression / déviations de répertoire (lecture des fiches `chess_game`) | **cible sprint 28** (modèle joueur) |
| 82 | Questions d'ouverture sans PGN (LLM seul, hallucinations constatées) | ouvert |
| 83 | Lien de partie Chess.com → PGN via API publique | ouvert |
| 84 | Récit LLM inventé autour des coups (matériel / menaces absents du bloc enrichi) | partiellement résolue sprint 27 (lignes `matériel :` / `attaquées :`) ; résidu → #92 |
| 85 | Positions critiques et meilleur coup instables entre deux analyses de la même partie (A : 16…Fe6 → 3…g6 ; F : 12.e5 → 38.Dc4+) [runs 04 et 06] | ouvert, aggravé sprint 27 (Threads=8 + limites en temps, accepté) ; `test_explosive_early_queen_nf6` intermittent ~1/10 [n=10] |
| 86 | 413 Groq systématique sur les échanges échecs, suivis compris (bloc enrichi dans l'historique > ITPM 7000) | ouvert — 5/5 au run live 27-10, repli DeepSeek |
| 88 | Question de suivi « la position 1 de cette partie » répond sur une autre partie malgré l'ancre (run 06 C, n=1) ; hypothèse non vérifiée : historique pollué par la mauvaise réponse du run 04 | ouvert, à auditer |
| 87 | Coups conseillés « explosifs » (sorte d) | partiellement résolue sprint 27 : moteur ✅ (Morra 8.Nd5, Dame précoce, letton) ; texte → #89-#92 ; Maia (lc0) = v2 |
| 89 | Variante du tournant (e) non montrée par le LLM malgré la consigne et les coups fournis (3/3 tournants au run live 27-10) ; piste : variante écrite par le router, pas par le LLM | ouvert |
| 90 | « Avantage clair » trop permissif : critères développement (écart ≥ 2) et activité (écart ≥ 10 coups légaux) valident des fins de variante à 36-54 % de gain [n=4, run live 27-10] | ouvert, seuils à réviser |
| 91 | Occasions explosives sans vrai piège en ouverture : la réponse logique est une des bonnes réponses (2.d4!? sur 2.Nf3, 2...Nf6!?, 11...Na6!?) [run live 27-10] | ouvert |
| 92 | Faits inventés résiduels : « 8.e5 c'est le meilleur coup » (légende : 8.Qe2), « 11...Na6 sacrifie un pion » (cavalier offert) [2/5 parties, run live 27-10] | ouvert |
| 93 | Polish rendu échecs : légende tournant « joué X (meilleur X) » redondante ; « fin de variante : matériel : … » (double deux-points) | ouvert, cosmétique |
| 94 | Échiquier d'analyse rejouable (chessground) avec flèches meilleur / explosif ; calque Chess.com limité à l'écran d'analyse post-partie (fair-play) | ouvert |

Hors dettes (Q4 sprint 27) : rangement des fiches `chess_game` en wing `echecs` / room
par ouverture.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-27` (tag sur le commit de clôture documentaire).
- Branche sprint 28 à créer en conception.
- Prochaine étape : `/conception sprint 28`.
