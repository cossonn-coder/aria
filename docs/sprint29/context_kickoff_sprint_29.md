─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 29 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-20
**Tag de référence sortie**       : `sprint-28`
**État sprint 28**                : CLOS (run live 04 + contrôle du correctif 05 OK).
  Tronçons `55a24f2`, `4d31f78`, `60a2f5f`, `4684ddc`. Détail : `docs/sprint28/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 28 (rappel synthétique)

- `chess_coach/difficulty.py` : difficulté Elo de chaque coup par Maia-2
  (R − 400·log10(P/(1−P)), hors coups 1-10), stockée dans `plies_json` (`difficulty`,
  `second_gap`) ; poids dans `/home/nico/.cache/aria-maia/`, maia2 installé `--no-deps`.
- `chess_coach/player_model.py` : `build_profile(games)` pur, recalculé à chaque analyse
  depuis les fiches saison 1 ; classements Elo par thème (pièces en prise, punir les
  erreurs, ouverture, convertir l'avantage, finale, résultats) ; Global = moyenne des 6 ;
  niveaux par palier de 100 ; 8 badges ; inventaire d'ouvertures famille × couleur.
- `bridge.load_chess_games()` ; bloc « 🎮 Progression » écrit par le router sous la
  réponse LLM (lignes fusionnées si même coup) ; ligne « Historique (données) » au LLM.
- Groq retiré du rôle REASONING.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 29

Pressentie (Nico, run live sprint 28) : **thèmes par motif tactique** (#100) — un coup
trouvé fait monter le niveau de son motif (fourchette, sacrifice, clouage…), le Global
reste la moyenne des thèmes + Résultats. Nécessite une détection de motifs (python-chess ;
sacrifice déjà calculé par `explosive`). Arbitrage d'entrée : remplacer ou compléter les
thèmes actuels. Touche le calcul du profil, pas l'écriture du palace.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-20 (post sprint 28)

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
| 73 | Groq 413 sur conversation chargée (ITPM `Limit 7000`) : depuis sprint 25, un 413 saute les autres Groq → DeepSeek répond 3 s après le 413 [run live 25-02, n=1, horodatage à la seconde] ; Groq reste inutilisable en REASONING dès que l'historique pèse (piste B « budget historique » écartée sprint 25) | partiellement résolue sprint 25 ; sprint 28 : Groq retiré du rôle REASONING (CHAT / PLANNING / REFLECTION le gardent : 121 réponses Groq en 7 jours) |
| 74 | Réponse hors sujet « Prochaine action : Résumer l'état actuel du projet potager… » à un message conversationnel (« lol non… ») [n=1, 2026-10-16] | ouvert, à diagnostiquer |
| 75 | Intent parasite `vacances normandie train` créé sur une question de suivi de lecture d'URL (« et la gastronomie normande… ») [n=1] | ouvert |
| 76 | Suite de lecture : la réponse refusionne la tranche 1 et parle de « trois parties » au lieu de deux [n=1] | ouvert, polish prompt |
| 77 | Image-to-image (photo + légende de génération) : Pollinations accepte `image=`, il faut une URL publique de la photo | ouvert |
| 78 | `llm/image_gen/hf_client.py` + `config.hf_image_model` morts (HF hors table depuis sprint 24) | ouvert, polish |
| 79 | Position d'échecs depuis une image (photo d'échiquier physique + capture d'écran) | ouvert |
| 80 | Relance moteur sur une position citée en texte libre (coups tapés sans en-tête : LLM seul, 15.Cg5+ conseillé à tort au run 06, SF d22 [1 run] : 15.exd6 +2,8) | ouvert |
| 81 | Bilan joueur / progression / déviations de répertoire (lecture des fiches `chess_game`) | partiellement résolue sprint 28 (modèle joueur RPG) ; déviations de répertoire non traitées |
| 82 | Questions d'ouverture sans PGN (LLM seul, hallucinations constatées) | ouvert |
| 83 | Lien de partie Chess.com → PGN via API publique | ouvert |
| 84 | Récit LLM inventé autour des coups (matériel / menaces absents du bloc enrichi) | partiellement résolue sprint 27 (lignes `matériel :` / `attaquées :`) ; résidu → #92 |
| 85 | Positions critiques et meilleur coup instables entre deux analyses de la même partie (A : 16…Fe6 → 3…g6 ; F : 12.e5 → 38.Dc4+) [runs 04 et 06] | ouvert ; `test_explosive_early_queen_nf6` en échec 3/5 suites complètes [n=5, sprint 28] et 1/5 isolé [n=5] |
| 86 | 413 Groq systématique sur les échanges échecs, suivis compris (bloc enrichi dans l'historique > ITPM 7000) | partiellement résolue sprint 28 : analyse (REASONING) sans Groq, vérifié au run live ; suivis en CHAT non vérifiés |
| 88 | Question de suivi « la position 1 de cette partie » répond sur une autre partie malgré l'ancre (run 06 C, n=1) ; hypothèse non vérifiée : historique pollué par la mauvaise réponse du run 04 | ouvert, à auditer |
| 87 | Coups conseillés « explosifs » (sorte d) | partiellement résolue sprint 27 : moteur ✅ (Morra 8.Nd5, Dame précoce, letton) ; texte → #89-#92 ; Maia (lc0) = v2 |
| 89 | Variante du tournant (e) non montrée par le LLM malgré la consigne et les coups fournis (3/3 tournants au run live 27-10) ; piste : variante écrite par le router, pas par le LLM | ouvert |
| 90 | « Avantage clair » trop permissif : critères développement (écart ≥ 2) et activité (écart ≥ 10 coups légaux) valident des fins de variante à 36-54 % de gain [n=4, run live 27-10] | ouvert, seuils à réviser |
| 91 | Occasions explosives sans vrai piège en ouverture : la réponse logique est une des bonnes réponses (2.d4!? sur 2.Nf3, 2...Nf6!?, 11...Na6!?) [run live 27-10] | ouvert |
| 92 | Faits inventés résiduels : « 8.e5 c'est le meilleur coup » (légende : 8.Qe2), « 11...Na6 sacrifie un pion » (cavalier offert) [2/5 parties, run live 27-10] | ouvert |
| 93 | Polish rendu échecs : légende tournant « joué X (meilleur X) » redondante ; « fin de variante : matériel : … » (double deux-points) | ouvert, cosmétique |
| 94 | Échiquier d'analyse rejouable (chessground) avec flèches meilleur / explosif ; calque Chess.com limité à l'écran d'analyse post-partie (fair-play) | ouvert |
| 95 | Inventaire / bilan complet sans PGN (« où j'en suis aux échecs ? ») | ouvert (sprint 28) |
| 96 | `summary.unconverted` vrai sur les parties à résultat `*` (outcome unknown) | ouvert (sprint 28) |
| 97 | Renvoyer une ancienne partie la replace en dernier dans la chronologie (timestamp d'analyse) | ouvert (sprint 28) |
| 98 | Fiches parasites « Test » ×2 / « Ami » dans le palace prod (ignorées : hors saison) | ouvert (sprint 28) |
| 99 | Arrêt d'`aria.service` > 90 s puis SIGKILL (threads python + `tokio-runtime` ChromaDB) : antérieur au sprint 28 (14:41, 19:00, 23:02 le 2026-10-19) ; risque d'écriture ChromaDB interrompue | ouvert, à auditer |
| 100 | Thèmes du modèle joueur par motif tactique (fourchette, sacrifice, clouage…) : détection de motifs inexistante | **cible pressentie sprint 29** |
| 101 | Ligne fusionnée du bloc Progression (deux thèmes au même coup) non observée en live, couverte par les tests seuls | ouvert, à observer |
| 102 | Mémoire du service 2,2 Go après 4 analyses (Maia/torch chargé) sur VM 4 Go [1 relevé] | ouvert, à surveiller |

Hors dettes (Q4 sprint 27) : rangement des fiches `chess_game` en wing `echecs` / room
par ouverture.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `main` mergé sur `sprint-28` (tag sur le commit de clôture documentaire).
- Branche sprint 29 à créer en conception.
- Prochaine étape : `/conception sprint 29`.
