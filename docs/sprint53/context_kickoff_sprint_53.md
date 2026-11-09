─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 53 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-11-09
**Tag de référence sortie**       : `sprint-52`
**État sprint 52**                : CLOS, run live 04 validé par Nico (2026-11-09).
  Détail : `docs/sprint52/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 52 (rappel synthétique)

- Cible d'origine (niveau joué estimé par Maia-2) abandonnée après mesure : Spearman 0,31 brut / 0,21 calibré
  [n=251 camps, 166 fiches] ; piste précision → Elo (calibration Lichess) non exploitable. Voir
  `docs/sprint52/audit_niveau_maia.md`.
- `chess_coach/level.py` : performance Elo (bornée ±800) et rang de précision dans tes parties.
- Bilan : Elo des deux camps sur la ligne 🎯 ; dernière ligne 🏅 « ta Ne meilleure partie sur M ».
- `/parties`, `/ouvertures`, `/ouvertures <nom>` : performance Elo (total + 5 dernières), infos générales en bas.
- Échiquier : Elo sur la ligne précision ; sur PGN chargé, rang de la partie et performance dans l'ouverture
  et la couleur (fiches lues via `bridge.load_chess_games`, injecté par `bot.py`).
- 553 tests verts.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 53

À choisir par Nico en `/conception sprint 53`.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-11-09 (post sprint 52)


| #  | Sujet | Statut |
|----|-------|--------|
| 9, 10, 11, 13, 15, 16, 19, 23 | (legacy < sprint 6) | ouverts, non touchés |
| 17 | Semantic wings non câblées | ouvert, architectural |
| 24 | `_read_collection_dim_count_sqlite` ignore database_id | ouvert, mono-db sans effet |
| 26 | Artefacts résiduels `~/.mempalace/` | partiellement résolue sprint 10 |
| 31 | Drift HNSW mécanique récurrent | **résolue sprint 43** (via #105) |
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
| 81 | Bilan joueur / progression / déviations de répertoire (lecture des fiches `chess_game`) | partiellement résolue sprint 28 (modèle joueur RPG) ; sprint 48 : répertoire détecté pour le choix des miniatures, pas de bilan des déviations |
| 82 | Questions d'ouverture sans PGN (LLM seul, hallucinations constatées) | ouvert ; réobservé sprint 47 : « ouvertures hollandaise » sans `/` part au LLM, qui répond sur « tes stats » [n=1, contenu non vérifié] |
| 83 | Lien de partie Chess.com → PGN via API publique | ouvert |
| 84 | Récit LLM inventé autour des coups (matériel / menaces absents du bloc enrichi) | partiellement résolue sprint 27 (lignes `matériel :` / `attaquées :`) ; résidu → #92 |
| 85 | Positions critiques et meilleur coup instables entre deux analyses de la même partie (A : 16…Fe6 → 3…g6 ; F : 12.e5 → 38.Dc4+) [runs 04 et 06] | **résolue sprint 49** : nœuds fixes sur 8 Stockfish à 1 thread, reproductible [2 parties, 2 rejeux chacune] ; `test_explosive_early_queen_nf6` n'existe plus |
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
| 97 | Renvoyer une ancienne partie la replace en dernier dans la chronologie (timestamp d'analyse) | **résolue sprint 49** : un renvoi ne touche plus la fiche (« déjà envoyée ») ; résidu → #185 |
| 98 | Fiches parasites « Test » ×2 / « Ami » dans le palace prod (ignorées : hors saison) | ouvert (sprint 28) |
| 99 | Arrêt d'`aria.service` > 90 s puis SIGKILL | **résolue sprint 29** : `os._exit(0)` après arrêt PTB (tronçon 10), arrêt dans la seconde aux runs 11-13 |
| 100 | Thèmes du modèle joueur par motif tactique | **résolue sprint 29** : `chess_coach/motifs.py` (portage cook.py + 11 mats), un classement par motif + « Mats », Global = moyenne des thèmes à ≥ 1 épreuve |
| 101 | Ligne fusionnée du bloc Progression (deux thèmes au même coup) non observée en live, couverte par les tests seuls | ouvert, à observer |
| 102 | Mémoire du service 2,2 Go après 4 analyses (Maia/torch chargé) sur VM 4 Go [1 relevé] | ouvert, à surveiller |
| 103 | `handle_event` synchrone bloque la boucle du bot pendant l'analyse | **résolue sprint 30** : `asyncio.to_thread` + « écrit… » + ⏳ unique, validé live ; reste #112 |
| 104 | Un échec d'envoi de photo interrompt l'envoi du texte qui suit (`images_text`) | **résolue sprint 30** (tests seuls, non provocable en live) |
| 105 | Quarantaine HNSW récurrente de `mempalace_drawers` (`sync_threshold` 50 000) | **résolue sprint 43** : cause racine = faux `.corrupt-*` du fork sur un pickle `dimensionality: None` (format normal chromadb 1.5.5) ; correctif amont `e811b6d1` repris (fork `ecf72132`), palace réparé (698/698), plus de `Quarantined invalid HNSW metadata` au run live ; les `.drift-*` restent sans dommage (→ #142) |
| 106 | Le LLM écrit « finale » sur une position classée milieu de partie | ouvert (sprint 29) |
| 107 | `context_block` épisodique nourri d'analyses passées (influence sur la légende non mesurée) | ouvert (sprint 29) |
| 108 | Analyse non déterministe : occasions explosives et précision différentes d'un passage à l'autre (86 % → 87 % sur la même partie) | **résolue sprint 49 pour les parties envoyées** (nœuds fixes) ; échiquier live : → #125 |
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
| 125 | Section 2 du run live : cyan sur g3 au lieu de h6 attendu, orange Na6 disparu entre deux passes [n=1] | partiellement résolue sprint 49 : résultat gardé par position au retour ; pas de nœuds fixes en live, une flèche peut encore changer entre passes (accepté par Nico) |
| 126 | Code couleur cyan / rose / bleu rationné absent de Telegram (échiquier seul) | ouvert (sprint 37), décision lot 1 |
| 127 | Courbe du meilleur coup à chaque position, en comparaison de la courbe jouée (sens à préciser : la courbe actuelle suppose déjà le meilleur jeu ensuite) [run live sprint 38] | **résolue sprint 39** |
| 128 | Indication des chances de mat sur la courbe [run live sprint 38] | **résolue sprint 39** |
| 129 | Courbe visible en permanence, y compris en jeu libre (aujourd'hui seulement avec un PGN chargé) [run live sprint 38] | **résolue sprint 39** |
| 130 | Partie jouée sur l'échiquier enregistrée au fil des coups, export PGN [run live sprint 38] | **résolue sprint 39** |
| 131 | Métacommandes Telegram : `/reboot` et commandes de confort (`/status`…) ; aujourd'hui `filters.TEXT & ~filters.COMMAND` ignore tout `/xxx` sans réponse | **résolue sprint 40** : 11 commandes + menu Telegram, filtre `ALLOWED_USER_ID`, `/reboot` par sortie code 1, `/oublie` = marqueur réversible (run live 2026-10-29) |
| 132 | Échiquier ouvert via `/board` : la 1re passe d'analyse expire pendant le chargement de Maia (`board_analysis error id=1 pass=1`, `TimeoutError`) puis `InvalidStateError` de `chess.engine` (réponse UCI arrivée après annulation) ; 3 tracebacks au journal, sans effet visible [run live sprint 40, n=1] | ouvert (sprint 40) |
| 133 | `/reboot` annonce « ≈ 15 s », relance mesurée ≈ 38 s (arrêt 20:17:11 → démarrage 20:17:46) [n=1] | ouvert (sprint 40), cosmétique |
| 134 | `/status` compte les marqueurs `/oublie` (`conversation_reset`) dans le total `aria_conversation` | ouvert (sprint 40), cosmétique |
| 135 | Un seul `BoardWorker` côté serveur : PC et téléphone ouverts en même temps se volent l'analyse live (la dernière position soumise gagne) | ouvert (sprint 41) |
| 136 | « Exporter PGN » (téléchargement `blob:`) peut ne pas marcher dans la webview Telegram | ouvert (sprint 41), run live « tout bon » global, export non détaillé |
| 137 | Document lu oublié après quelques échanges : la synthèse n'est que dans `aria_conversation` (relue par ordre chronologique, plafond 6 000 car.) ; pas d'écriture épisodique (`no_intent_resolved`) → introuvable par le sens quelques jours plus tard [run live sprint 42] | **résolue sprint 43** : fiche `aria_episodic`/room `documents` + texte intégral `aria_documents`, relecture « relis… » / « oui » ; rappel après `/oublie` et redémarrage OK au run live (inventaire) ; résidus #146-#148 |
| 138 | `pypdf` installé dans le venv mais absent de `requirements.txt` | ouvert (sprint 42), polish |
| 139 | « lis la suite » sur un PDF scanné refait l'OCR de tout le fichier à chaque tranche (rare : > 100 000 car.) | partiellement résolue sprint 43 : la relecture d'un document ne refait plus l'OCR ; « lis la suite » oui |
| 153 | Relecture d'une recherche (`source=recherche:…`) libellée « synthèse du fichier » par `_read_slice` (toute source non http = fichier) | ouvert (sprint 45), cosmétique |
| 154 | `web_research OK … pages=` compte les pages en échec d'extraction (`read=2 failed=1` → `pages=3`) | ouvert (sprint 45), cosmétique |
| 155 | Rappel épisodique hors sujet : « quel temps demain à Grenoble ? » → `document_recall source=…inventaire.txt` [n=1, run live 02] | ouvert (sprint 45) ; réobservé sur des analyses d'échecs : `inventaire.txt` à 10:41:32 et une recherche web à 09:59:25 le 2026-11-02 [n=2 relevés, pas de décompte], injection dans le prompt non vérifiée |
| 156 | Réponse Telegram > 4096 car. découpée au milieu d'une ligne (URL coupée en deux messages au run live 03) | ouvert (sprint 45), cosmétique |
| 140 | `retrieve_memories(type_filter=…)` filtrerait tout : les hits mempalace n'ont pas de champ `type` | ouvert (sprint 43), 0 caller prod |
| 141 | « lis la suite » après la relecture d'un texte > 100 000 car. repart du fichier / de l'URL | ouvert (sprint 43) |
| 142 | Ménage du palace : `.drift-*` (7, dont l'ancien segment orphelin `cc7e6b6a.drift-20261030-170109`), `.corrupt-*` (1), sauvegarde `~/.mempalace/palace.pre-repair-20261030` | ouvert (sprint 43) ; + 2 sauvegardes `palace.pre-sprint46-*` (2026-11-02) |
| 143 | Même fichier envoyé plusieurs fois → plusieurs fiches : la source contient l'identifiant Telegram unique (4 fiches `inventaire.txt` au run live) | ouvert (sprint 43) |
| 144 | Synthèse à l'envoi de l'inventaire : « carton 115, grenier » au lieu de garage [1er run live, n=1] | ouvert (sprint 43), non réobservé au 2e run |
| 145 | `aria_documents` absente de `/status` (`count_by_wing`) | ouvert (sprint 43), cosmétique |
| 146 | Page web lue introuvable par le sens : « que disait la page sur le paillage ? » → fiche « Paillis — Wikipédia » à distance 0,641, derrière les fiches inventaire (0,55-0,59) et des souvenirs d'images, hors des 10 premiers [1 requête, copie du palace] | **résolue sprint 44** : `bridge.find_documents` (room `documents` entière + filtre par mots porteurs), fiche en tête de la section épisodique ; retrouvée au run live (`document_recall`) |
| 147 | `DOC_REREAD` sans seuil propre : « relis le document sur les impôts » relit l'inventaire (seuil par défaut 0,8) au lieu de `NOT_FOUND` ; le LLM répond quand même « aucun document » | **résolue sprint 44** : relecture avec mot porteur → 1re fiche correspondante ou `NOT_FOUND` (run live OK) |
| 148 | Acceptation « oui » d'une proposition de relecture non testée en live (tests seuls) : au run live, l'extrait de la fiche contenait déjà la réponse | ouvert (sprint 43), à observer |
| 149 | Échecs : miniatures du compte rendu centrées sur les coups manqués de Nico | **résolue sprint 46** : 4 places (erreurs → explosifs → beaux coups), dès le coup 4, flèche bleue du coup joué ; résidu → #157 |
| 150 | Rappel épisodique : les hits room `general` (images) sont retirés par le bridge après la coupe de mempalace → moins de souvenirs que `top_k` (n=4 → 3) [1 requête, audit sprint 44] | ouvert (sprint 44) |
| 151 | L'opération classée par LLM et le nombre de souvenirs rappelés ne sont pas journalisés | ouvert (sprint 44) |
| 152 | Recherche de documents : mots présents dans toute fiche (`source`, `synthese`, `https`) non exclus des mots porteurs → une question qui les porte retient la 1re fiche ; seuil de distance 0,8 conservé (fiche à distance > 0,8 invisible, distances observées 0,42-0,84 [audit sprint 44]) | ouvert (sprint 44), non observé au run live |
| 157 | Stratégie rose et piège cyan non calculés sur une partie envoyée : coût ≈ 1 min/partie [estimation] | ouvert (sprint 46) ; sprint 50 : le piège est lu sur les explosifs retenus, sans calcul du piège ni de la stratégie sur toute la partie |
| 158 | Document indexé des fiches migrées non réécrit (« ouverture inconnue » possible), métadonnées seules | ouvert (sprint 46) |
| 159 | 13 fiches `color_source=default`, blancs : camp invérifiable, le nom des blancs n'est pas stocké | ouvert (sprint 46) |
| 160 | `find_explosive` cherche encore sur les coups 1-3, écartés ensuite par `select_critical` | **résolue sprint 49** : pas de recherche avant `first_move` |
| 161 | Pression au temps ignorée par le profil (`errors_low_clock` jamais relu) | **touchée sprint 51** : ligne Temps et coups longs au bilan ; profil inchangé |
| 162 | Recherche explosive lancée même quand 4 erreurs remplissent les places : 51,0 s sur 66,4 s sur la partie 1 [n=1] ; 82 % du temps d'analyse [546,6 s sur 668,9 s, n=8] | **résolue sprint 49** : recherche sautée dans ce cas (`chess_explosive skipped`) |
| 163 | Busch-Gass : accepté et décliné non distingués, la table Lichess n'a aucune ligne pour 3.b4 | ouvert (sprint 46), cosmétique |
| 164 | « Roqué » déduit de la case du roi (le FEN n'a pas d'historique) : un roi venu à pied en g1 est dit roqué | ouvert (sprint 46), cosmétique |
| 165 | Relier ARIA à la suite Nextcloud (mails via Nextcloud Mail + Gmail, notes et listes via l'API Notes) : faisable, arbitrages rendus, reporté par Nico. Étude et reprise : `docs/backlog/etude_applications_smartphone.md` | ouvert (2026-11-02), attend les préalables de Nico (installer Mail, mot de passe d'application) |
| 166 | Route `/send` de l'échiquier sans authentification sur `0.0.0.0:5002` : tout texte est traité comme un message de Nico, sans contrôle PGN. Sans gravité aujourd'hui, **bloquant avant #165** (un mail pourrait partir en son nom) | ouvert (2026-11-02) ; touchée sprint 52 : l'échiquier lit désormais les fiches (lecture seule) |
| 167 | Mot-clé `génère` trop large (sous-chaîne) : « génère une note », « génère une liste », « génère un plan » partent en génération d'image [détection exécutée sur ces 3 phrases, classification complète non lancée] | ouvert (2026-11-02) |
| 168 | Mot de passe Nextcloud en clair dans `~/.config/systemd/user/nextcloud-sync.service` | ouvert (2026-11-02) |
| 169 | `/ouvertures <nom>` : noms de groupes en anglais, `hollandaise` ou `française` ne trouvent rien | ouvert (sprint 47) |
| 170 | Aucune fiche n'avait d'horloge | **résolue sprint 51** : cause = PGN copié sans `%clk` ; un PGN avec horloges réanalyse la fiche |
| 171 | Gel de Stockfish > 10 s : 3 analyses perdues sur `TimeoutError` le 2026-11-02 [n=3, dont 1 pendant un pytest]. Marge portée à 60 s au sprint 47, cause non établie ; piste : mémoire (4,6 Gio de RAM, 5,5 Gio de swap [1 relevé, pendant un pytest]), recoupe #102 | ouvert (sprint 47), à observer |
| 172 | Stockfish de `/board` jamais refermé après usage : 535 Mio en swap [1 relevé] ; sa marge reste à 10 s | ouvert (sprint 47) |
| 173 | Erreur répétée dans le répertoire : dès la 3e fois, plus de miniature ; signalé à Nico, pas d'exception pour les grosses pertes | ouvert (sprint 48), à arbitrer si gênant |
| 174 | Répertoire comparé sur la suite exacte des coups : une transposition compte comme une nouveauté | ouvert (sprint 48) |
| 175 | `/parties` : jour lu dans la date du PGN ; une partie après minuit peut tomber la veille si le site date en UTC [non vérifié] | ouvert (sprint 48), à observer |
| 176 | Coup explosif : une pièce déjà attaquée laissée en prise n'est pas reconnue comme sacrifice (Byrne-Fischer 17...Fe6) ; non couvert non plus par la mesure de rappel du sprint 49 | ouvert (étude AggroChess), `docs/sprint49/audit_aggrochess.md` §7 |
| 177 | Coup explosif : un seul coup par position, choisi au gain d'espérance ; un sacrifice sain peut céder la place à un coup calme (Fxh7+ / Nb3 une passe sur deux) [2 passes] | ouvert (étude AggroChess) ; recoupe #108 |
| 178 | Coup explosif : 27.Qd5!! rejeté de justesse, recherche partagée à 15,7 pts pour une limite de 15 (`1q3kr1/2r1b1pp/p2NPn2/1pQ3N1/8/5PP1/PPP4P/3R1RK1 w`), cas de test si le sujet revient ; recherche à part mesurée : 1 coup utile sur 553 [58 positions, 1 passe] | ouvert (étude AggroChess) |
| 179 | Échiquier : la recherche live ne s'interrompt pas pendant un appel moteur (jusqu'à 4,8 s à ×8 [calcul]) | ouvert (sprint 49) |
| 180 | Texte LLM variable d'une analyse à l'autre de la même partie, malgré une analyse moteur stable | ouvert (sprint 49), hors périmètre du sprint |
| 181 | `/eval` et le worker de l'échiquier donnent deux meilleurs coups de profondeurs différentes | ouvert (sprint 49) |
| 182 | Aucun moyen de réanalyser une partie déjà envoyée : le doublon est refusé | partielle sprint 51 : réanalyse seulement sur apport d'horloges |
| 183 | Échiquier : meilleur coup publié sans attendre la fin de passe à la 1re passe seulement ; ensuite, il change en fin de passe (pour éviter le mélange avec l'explosif de la passe précédente). Condition dans `_publish_head` | ouvert (sprint 49), à arbitrer si gênant |
| 184 | Miniatures : les pastilles numérotées de deux coups de même trajectoire finale peuvent se chevaucher | ouvert (sprint 49), non observé au run live [validation globale, sans détail par point] |
| 185 | « déjà envoyée » : pour une partie renvoyée avant le sprint 49, la date affichée est celle du dernier envoi (`timestamp` réécrit par l'ancien upsert) | ouvert (sprint 49), cosmétique |
| 186 | Échiquier : `TimeoutError` Stockfish dans `_deepen` (`board_analysis error id=33 pass=1`, 22:53:52 le 2026-11-04) précédé d'un `board_eval` à 13,88 s [n=1, pendant un pytest, cause non établie] ; flèches revenues sur les coups suivants d'après Nico. Recoupe #171, #172 | ouvert (sprint 49), à observer |
| 187 | Le LLM peut mal raconter un coup joué (« Qxf1+ échange ta dame contre un cavalier », alors qu'il gagne le cavalier) : il ne reçoit pas ce que le coup joué capture [n=1] | ouvert (sprint 50) |
| 188 | Variantes d'un seul coup (34.Qa4, 33...Qa6) [n=2], cause non cherchée | ouvert (sprint 50) |
| 189 | Analyse de 211,6 s dont 197,7 s de recherche d'explosifs [n=1, 31 positions], alors que le message annonce « jusqu'à 2 minutes » | ouvert (sprint 50) |
| 190 | Fait « cloue X » seul refusé par Nico : à ajouter pour toutes les tactiques ou pas du tout (« décloue X » existe depuis le sprint 50) | ouvert (sprint 50) |
| 191 | `/parties <ouverture>` sans partie de cette ouverture le jour même : renvoie le message de `/ouvertures` (« Liste : /ouvertures »), trompeur | ouvert (sprint 50), cosmétique |
| 192 | Pire coup arrondi deux fois : 78 % au bilan (`worst_win_after` arrondi à 0,1 puis à l'unité) contre 79 % en légende [n=1] | ouvert (sprint 50), cosmétique |
| 193 | Coup brillant (règle chess.com) jamais observé sur une partie réelle ; partie de Légal prête dans `docs/sprint50/04_run_live_5.txt` | ouvert (sprint 50), à observer |
| 194 | Fiches des parties envoyées sous `BaguetteChaussette` avant son ajout (2026-11-06) : camp supposé, peut-être faux | ouvert (sprint 50), à vérifier |
| 195 | Compteur inter-parties des idées de conversion manquées (« roi pas activé dans 3 parties ») | ouvert (sprint 51) |
| 196 | Plan adverse répété non exploité (g5 proposé 9 fois à dusha28) | ouvert (sprint 51) |
| 197 | Thème « Convertir l'avantage » du profil aveugle aux conversions lentes (`_is_trial` exige une perte ou un écart ≥ 10 et `win_before ≤ 90`) | ouvert (sprint 51) |
| 198 | Échiquier web : palette de la liste des coups non alignée sur les pastilles 🔵 🟢 ⚪ | ouvert (sprint 51) |
| 199 | Fiche tronquée en palace prod : BaguetteChaussette – luismota32 du 2026-11-06, `hash=2d5aed504532ea89`, 76 plies sur 107, comptée dans la progression ; suppression à arbitrer | ouvert (sprint 51) |
| 200 | Concept d'une idée de conversion : ordre roi > pion passé > pion > prise > pièce ; une prise par un pion devient « avancer le pion », par le roi « activer le roi » | ouvert (sprint 51), à trancher si gênant |
| 201 | Coup brillant aussi explosif compté deux fois dans 🟠 (somme simple, pas de dédoublonnage) | ouvert (sprint 51), cosmétique |
| 202 | Run live 05 non joué : réanalyse dusha28 (réécriture d'une fiche prod), lignes Conversion / Temps sur le cas de référence, recollage corrigé (`cde22c0`) non revus en live | ouvert (sprint 51), clos par Nico sans run live complet |
| 203 | Échiquier, rang de précision : une partie collée qui n'est pas une fiche n'est pas comptée dans le total (« sur 140 » au lieu de 141) | ouvert (sprint 52), cosmétique |
| 204 | `interfaces/board_interface.py` importe `RECENT_GAMES` et la fonction privée `_game_date_key` de `interfaces/meta_commands.py` (même règle d'omission que `/ouvertures`) : couplage échiquier → module Telegram | ouvert (sprint 52), rangement |

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `feat/sprint52-niveau` mergé sur `main`, tag `sprint-52` sur le commit de clôture documentaire.
- Branche sprint 53 à créer en conception.
- Prochaine étape : `/conception sprint 53`.
