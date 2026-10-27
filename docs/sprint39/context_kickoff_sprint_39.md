─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 39 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-27
**Tag de référence sortie**       : `sprint-38`
**État sprint 38**                : CLOS (tronçons 01-02 + correctif « joué : X », run live fait par Nico).
  Détail et run live : `docs/sprint38/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 38 (rappel synthétique)

- Route `POST /game` {pgn} → `wins` : % de gain des blancs par position (`analyze_game`).
- Page : PGN collé (avec ou sans en-tête), Elo pré-remplis, navigation ⏮ ◀ ▶ ⏭ + clavier,
  coup hors partie = variante avec « Revenir à la partie », courbe cliquable avec trait
  sur le coup affiché, « joué : X » sous l'échiquier + pièce du coup cerclée de blanc.
- Run live 2026-10-27 : tout OK (navigation jugée « très ergonomique »).
- 370 tests verts.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 39

Choisie par Nico au run live 38 : les demandes #127-#130 (courbe du meilleur coup, chances
de mat sur la courbe, courbe en jeu libre, enregistrement + export PGN). Découpage et
arbitrages en `/conception sprint 39`.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-27 (post sprint 38)

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
| 39 | executor/critic (phase `execution`) sans historique | **résolue sprint 34** : code supprimé (#72) |
| 40 | Embeddings inutiles sur `aria_conversation` (latence CPU, HNSW) | ouvert |
| 41 | `executor_agent.py`, `critic_agent.py` absents de l'inventaire des callers de `complete` | **résolue sprint 34** : code supprimé (#72) |
| 43 | `mempalace_mcp` logue en ERROR « No palace found » au 1er message après reset | ouvert, cosmétique |
| 52 | `scripts/check_keys.py` teste des modèles retirés | ouvert |
| 53 | Config morte : `gemini_model`, `sambanova_*`, `cerebras_*`, `mistral_*`, `openrouter_vision_models`, `OpenRouterVisionClient` | ouvert |
| 54 | `LLMRole.REFLECTION` sans caller | ouvert |
| 55 | `CriticAgent` : sortie jamais lue (appel LLM sans effet) | **résolue sprint 34** : code supprimé (#72) |
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
| 72 | Code sans caller apparent : `cognition/cognitive_dispatcher.py`, `execution/execution_plan_builder.py`, `cognition/dispatcher_types.py` ; depuis sprint 32 aussi `agents/executor_agent.py`, `agents/critic_agent.py` et leurs entrées du registre | **résolue sprint 34** : modules supprimés, orphelins (`ExecutionPlan`, `Intent.infer_phase`, `IntentPhase`) retirés, redémarrage sans ImportError |
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
| 94 | Échiquier d'analyse rejouable (chessground) avec flèches ; rejeu d'une partie PGN | **résolue sprint 38** : PGN chargé dans l'échiquier, navigation, variante, « joué : X » + pièce cerclée, courbe du % de gain des blancs (run live 2026-10-27) ; calque chess.com abandonné |
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
| 114 | `actions_history` des intents stocke les messages entiers (blocs d'analyse ≈ 9 000 car.), `intents.json` à 327 Ko [audit sprint 32] et en croissance ; disque seulement, plus envoyé au LLM | **résolue sprint 34** : `save_intents` coupe chaque action à 100 car. ; `intents.json` 343 805 → 13 922 octets au run live |
| 115 | Suivi de partie : « pourquoi mon 12e coup était une erreur ? » → l'analyst accepte la prémisse (l'analyse disait aucune erreur), dit « tu as gagné un pion » sur une reprise, invente 12…Nd3+ « décisif » ; faits moteur et PGN coupés de l'historique par le plafond sprint 33 (cause probable, non prouvée) [n=1] | ouvert (sprint 33) |
| 116 | `intent_compression_engine.py` affecte la property `actions` sans setter (crash si fusion) | ouvert (sprint 34), non vérifié |
| 117 | `print()` dans `intent/intent_store.py` | ouvert (sprint 34), polish |
| 118 | Deux intents `jeux echecs` dans `intents.json` | ouvert (sprint 34) |
| 119 | `ExecutionStatus` sans usage | ouvert (sprint 34), polish |
| 120 | `aria.egg-info/SOURCES.txt` versionné, liste encore les fichiers supprimés au sprint 34 | ouvert (sprint 34), polish |
| 121 | Coups explosifs trop rares : gambits d'ouverture, Fxf7+, sacrifice grec non signalés ; meilleur coup exclu, sacrifice mesuré net après l'échange, fenêtre 35-75 % [retour run live sprint 35] | **résolue sprint 36** : sacrifice = offre acceptée (déficit ≥ 1 pion vs ligne du meilleur coup, perte ≤ 10 pts, avantage clair ou échec), meilleur coup candidat en live, `_WIN_MAX` 85 ; Göring, Fxf7+, Fxh7+ vus au run live |
| 122 | Latence de l'analyse live de l'échiquier : passe ×1 ≈ 4-6 s, ×2 ≈ 8-12 s, ×4 ≈ 30 s [journal 2026-10-23, n=6 à 31 par passe] ; coups joués vite → analyses `superseded` sans flèche | ouvert, accepté par Nico (« finalement ça va ») ; non aggravée par le sprint 36 ; sprint 37 (piège + stratégie) : ×1 1,8-9,5 s, médiane ≈ 6 s [journal 2026-10-26, n=24], ×4 13-49 s [n=4] |
| 123 | Flèche rose sans explication : la page montre le coup et sa suite, pas l'idée stratégique en mots [run live sprint 37] | ouvert (sprint 37), souhait de Nico |
| 124 | « pronostic humain X % (meilleur coup Y %) » illisible : c'est le score attendu du camp au trait d'après la tête de valeur Maia-2, pas une probabilité de jouer le coup [run live sprint 37] | ouvert (sprint 37), libellé à revoir |
| 125 | Section 2 du run live : cyan sur g3 au lieu de h6 attendu, orange Na6 disparu entre deux passes [n=1] | ouvert (sprint 37), recoupe #108 |
| 126 | Code couleur cyan / rose / bleu rationné absent de Telegram (échiquier seul) | ouvert (sprint 37), décision lot 1 |
| 127 | Courbe du meilleur coup à chaque position, en comparaison de la courbe jouée (sens à préciser : la courbe actuelle suppose déjà le meilleur jeu ensuite) [run live sprint 38] | ouvert, cible candidate sprint 39 |
| 128 | Indication des chances de mat sur la courbe [run live sprint 38] | ouvert, cible candidate sprint 39 |
| 129 | Courbe visible en permanence, y compris en jeu libre (aujourd'hui seulement avec un PGN chargé) [run live sprint 38] | ouvert, cible candidate sprint 39 |
| 130 | Partie jouée sur l'échiquier enregistrée au fil des coups, export PGN [run live sprint 38] | ouvert, cible candidate sprint 39 |

Hors dettes (Q4 sprint 27) : rangement des fiches `chess_game` en wing `echecs` / room
par ouverture.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `feat/sprint38-pgn` mergé sur `main`, tag `sprint-38` sur le commit de clôture documentaire.
- Branche sprint 39 à créer en conception.
- Prochaine étape : `/conception sprint 39`.
