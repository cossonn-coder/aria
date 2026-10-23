─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 34 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-23
**Tag de référence sortie**       : `sprint-33`
**État sprint 33**                : CLOS (tronçon 01 validé live).
  Détail et run live : `docs/sprint33/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 33 (rappel synthétique)

- Historique passé à l'analyst plafonné : 1 500 car. par message (suffixe ` […]`), 6 000 car.
  au total, du plus récent au plus ancien (`_trim_history`, étape 1b de `llm_router.py`).
  Bridge, écriture et lecteurs directs inchangés.
- Run live : `salut` après une analyse en 3 s (sprint 32 : 6 s), `chars=5463`, Groq répond.
- Coût constaté : une question de suivi de partie a reçu une réponse inventée (#115).

─────────────────────────────────────────────────────────────────────────

## Cible sprint 34

**À arbitrer en `/conception`.** Candidates :
- #115 : suivi de partie inventé (prémisse fausse acceptée, faits moteur hors historique).
- #72 élargie : ranger executor / critic devenus sans caller (+ #39, #41, #55).
- #114 : `actions_history` qui grossit `intents.json`.
Autres : #94 échiquier rejouable ; texte coach #92, #109, #110 ; #112.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-23 (post sprint 33)

| #  | Sujet | Statut |
|----|-------|--------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6) | ouverts, non touchés |
| 17 | Semantic wings non câblées | ouvert, architectural |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet |
| 26 | Artefacts résiduels `~/.mempalace/` | partiellement résolue sprint 10 |
| 31 | Drift HNSW mécanique récurrent | ouvert — voir #105 |
| 32 | Digression Normandie → Belgique | à reconfirmer |
| 33 | Garde runbook `"mempalace-fork" in __file__` | ouvert, polish trivial |
| 35 | Tests dépendants de l'auto-sys.path pytest | ouvert |
| 36 | `LLMRouter.route()` inerte, jamais appelée | ouvert |
| 37 | `max_history_turns` compte des tours, l'API des messages | ouvert, reformulée sprint 33 : nommage seul, sans effet sur le volume (plafond 6 000 car. en aval) |
| 38 | Double présence épisodique / conversation dans le contexte | ouvert, bornée (400 car./souvenir), pas la cause du volume [audit sprint 33] |
| 39 | executor/critic (phase `execution`) sans historique | **sans objet sprint 32** : executor/critic plus appelés, code à ranger avec #72 |
| 40 | Embeddings inutiles sur `aria_conversation` (latence CPU, HNSW) | ouvert |
| 41 | `executor_agent.py`, `critic_agent.py` absents de l'inventaire des callers de `complete` | **sans objet sprint 32** : plus aucun caller, à ranger avec #72 |
| 43 | `mempalace_mcp` logue en ERROR « No palace found » au 1er message après reset | ouvert, cosmétique |
| 52 | `scripts/check_keys.py` teste des modèles retirés | ouvert |
| 53 | Config morte : `gemini_model`, `sambanova_*`, `cerebras_*`, `mistral_*`, `openrouter_vision_models`, `OpenRouterVisionClient` | ouvert |
| 54 | `LLMRole.REFLECTION` sans caller | ouvert |
| 55 | `CriticAgent` : sortie jamais lue (appel LLM sans effet) | **sans objet sprint 32** : plus appelé, à ranger avec #72 |
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
| 71 | `print()` dans `core/kernel.py` `_normalize` | **résolue sprint 29** (logger, tronçon 01) |
| 72 | Code sans caller apparent : `cognition/cognitive_dispatcher.py`, `execution/execution_plan_builder.py`, `cognition/dispatcher_types.py` ; depuis sprint 32 aussi `agents/executor_agent.py`, `agents/critic_agent.py` et leurs entrées du registre | ouvert |
| 73 | Groq 413 sur conversation chargée (ITPM `Limit 7000`) | **résolue sprint 31** : saut préventif de Groq au-delà de 12 000 car. (`GROQ_MAX_PAYLOAD_CHARS`), aucun 413 au run live ; Groq garde les petites requêtes |
| 74 | Réponse hors sujet « Prochaine action : … » à un message conversationnel [n=4] | **résolue sprint 32** : messages courts et non classés → analyst seul ; au run live, `salut` en 6 s, un seul appel DeepSeek, plus de « Prochaine action » |
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
| 86 | 413 Groq systématique sur les échanges échecs, suivis compris | **résolue sprint 31** (via #73), suivis vérifiés au run live |
| 88 | Question de suivi « la position 1 de cette partie » répond sur une autre partie malgré l'ancre (run 06 C, n=1) ; hypothèse non vérifiée : historique pollué par la mauvaise réponse du run 04 | ouvert, à auditer |
| 87 | Coups conseillés « explosifs » (sorte d) | partiellement résolue sprint 27 : moteur ✅ (Morra 8.Nd5, Dame précoce, letton) ; texte → #89-#92 ; Maia (lc0) = v2 |
| 89 | Variante du tournant (e) non montrée par le LLM | **résolue sprint 29** : ligne « Variante : » écrite par le router (tronçon 15), vue sur les 4 tournants du run live 13 |
| 90 | « Avantage clair » trop permissif : critères développement (écart ≥ 2) et activité (écart ≥ 10 coups légaux) valident des fins de variante à 36-54 % de gain [n=4, run live 27-10] | ouvert, seuils à réviser |
| 91 | Occasions explosives sans vrai piège : la réponse logique est une des bonnes réponses | **résolue sprint 29** : espérance humaine Maia, réponse affichée = réponse humaine la plus probable (tronçon 04) ; bruit d'ouverture accepté (2.d4, 3.Bb5, 6.Bb5) |
| 92 | Faits inventés résiduels dans le texte LLM : run live 27-10 (« 8.e5 meilleur coup », « Na6 sacrifie un pion ») ; run live 13 sprint 29 : « trois pièces de plus » à +3 points, « Rd1# imparable » alors que 39.Qc2 pare, « tu prends tout sur la colonne d » hors variante [3 sur 21 entrées] | ouvert |
| 93 | Polish rendu échecs : légende tournant « joué X (meilleur X) » redondante ; « fin de variante : matériel : … » (double deux-points) | ouvert, cosmétique |
| 94 | Échiquier d'analyse rejouable (chessground) avec flèches meilleur / explosif ; calque Chess.com limité à l'écran d'analyse post-partie (fair-play) | ouvert |
| 95 | Inventaire / bilan complet sans PGN (« où j'en suis aux échecs ? ») | ouvert (sprint 28) |
| 96 | `summary.unconverted` vrai sur les parties à résultat `*` (outcome unknown) | ouvert (sprint 28) |
| 97 | Renvoyer une ancienne partie la replace en dernier dans la chronologie (timestamp d'analyse) | ouvert (sprint 28) |
| 98 | Fiches parasites « Test » ×2 / « Ami » dans le palace prod (ignorées : hors saison) | ouvert (sprint 28) |
| 99 | Arrêt d'`aria.service` > 90 s puis SIGKILL | **résolue sprint 29** : `os._exit(0)` après arrêt PTB (tronçon 10), arrêt dans la seconde aux runs 11-13 |
| 100 | Thèmes du modèle joueur par motif tactique | **résolue sprint 29** : `chess_coach/motifs.py` (portage cook.py + 11 mats), un classement par motif + « Mats », Global = moyenne des thèmes à ≥ 1 épreuve |
| 101 | Ligne fusionnée du bloc Progression (deux thèmes au même coup) non observée en live, couverte par les tests seuls | ouvert, à observer |
| 102 | Mémoire du service 2,2 Go après 4 analyses (Maia/torch chargé) sur VM 4 Go [1 relevé] | ouvert, à surveiller |
| 103 | `handle_event` synchrone bloque la boucle du bot pendant l'analyse | **résolue sprint 30** : `asyncio.to_thread` + « écrit… » + ⏳ unique, validé live ; reste #112 |
| 104 | Un échec d'envoi de photo interrompt l'envoi du texte qui suit (`images_text`) | **résolue sprint 30** (tests seuls, non provocable en live) |
| 105 | Quarantaine HNSW récurrente de `mempalace_drawers` (`sync_threshold` 50 000) | ouvert. Sprint 30 : baisser le seuil a écrit un pickle `dimensionality: None` → purge de la file + quarantaine `.corrupt-*` par mempalace → index quasi vide (réparé). La quarantaine `.drift-*` actuelle est sans dommage (file intacte) : utilité du correctif à réévaluer ; tout correctif validé par une ouverture mempalace ; run 31 : nouvelle `.drift-*` au démarrage, sans effet |
| 106 | Le LLM écrit « finale » sur une position classée milieu de partie | ouvert (sprint 29) |
| 107 | `context_block` épisodique nourri d'analyses passées (influence sur la légende non mesurée) | ouvert (sprint 29) |
| 108 | Analyse non déterministe : occasions explosives et précision différentes d'un passage à l'autre (86 % → 87 % sur la même partie) | ouvert (sprint 29) ; recoupe #85 |
| 109 | Ligne « Variante : » parfois réduite à 1-2 coups (« 28...Kh7. », « 12.Bd2 ; 12...Nf5. ») : PV coupée à l'avantage clair ou courte | ouvert (sprint 29) |
| 110 | Consignes d / e en tension avec « idée générale seule, 1-3 phrases » : le LLM recopie « face à un humain l'espérance n'est pas meilleure que le meilleur coup » (2 fois sur la partie 2) | ouvert (sprint 29), polish prompt |
| 111 | Message ⏳ « jusqu'à 2 minutes » envoyé sur un `salut` | **résolue sprint 31** : seuil 20 s, aucun ⏳ sur les messages courts au run live (11 s max) |
| 112 | PTB traite les updates en séquence : un message envoyé pendant une analyse n'est pris qu'après elle | ouvert, observé au run 31 [n=1], seulement si gênant (`concurrent_updates`) |
| 113 | Prompts de 319 023 / 161 407 car. envoyés à DeepSeek sur un `salut` après une analyse | **résolue sprint 32** : c'étaient les prompts executor / critic (rediagnostic), disparus au run live ; l'historique restant (≈ 37 000 car.) relève de #37 ; **ramené à ≤ 6 000 car. sprint 33** |
| 114 | `actions_history` des intents stocke les messages entiers (blocs d'analyse ≈ 9 000 car.), `intents.json` à 327 Ko [audit sprint 32] et en croissance ; disque seulement, plus envoyé au LLM | ouvert (sprint 32) |
| 115 | Suivi de partie : « pourquoi mon 12e coup était une erreur ? » → l'analyst accepte la prémisse (l'analyse disait aucune erreur), dit « tu as gagné un pion » sur une reprise, invente 12…Nd3+ « décisif » ; faits moteur et PGN coupés de l'historique par le plafond sprint 33 (cause probable, non prouvée) [n=1] | ouvert (sprint 33) |


Hors dettes (Q4 sprint 27) : rangement des fiches `chess_game` en wing `echecs` / room
par ouverture.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `feat/sprint33-historique` mergé sur `main`, tag `sprint-33` sur le commit de clôture documentaire.
- Branche sprint 34 à créer en conception.
- Prochaine étape : `/conception sprint 34`.
