─────────────────────────────────────────────────────────────────────────
ARIA — Kickoff sprint 36 (ouverture)
─────────────────────────────────────────────────────────────────────────

**Date**                          : 2026-10-23
**Tag de référence sortie**       : `sprint-35`
**État sprint 35**                : CLOS (tronçons 01-02, run live fait par Nico).
  Détail et run live : `docs/sprint35/00_etat.md`.

─────────────────────────────────────────────────────────────────────────

## Acquis sprint 35 (rappel synthétique)

- Échiquier hébergé par ARIA : `http://192.168.1.124:5002`, serveur `http.server` en thread
  dans `aria.service` (`interfaces/board_interface.py`), page chessground + chess.js
  (`interfaces/board/index.html`).
- Analyse continue du camp au trait (`chess_coach/live.py`) : passes ×1 → ×8, un coup joué
  interrompt l'analyse (`Superseded`), flèche orange « explosif », flèche verte « seul
  coup », réponses Maia au survol de la ligne d'état. `explosive.py` inchangé.
- 364 tests verts.

─────────────────────────────────────────────────────────────────────────

## Cible sprint 36 : redéfinir le coup explosif (#121)

Retour run live : « les coups explosifs sont trop rares, on n'a peut-être pas la même
définition ». Pour Nico, sont explosifs : un gambit d'ouverture ; un sacrifice de pièce pour
attaquer le roi en restant correct (Fxf7+ typique) ; le sacrifice grec (Fxh7+) et les motifs
d'attaque de ce genre. Un coup explosif est aussi un piège : si l'adversaire joue le coup
logique, il se retrouve moins bien.

### Diagnostic (lecture de `chess_coach/explosive.py`, 2026-10-23)

1. Meilleur coup exclu d'office (`_search_position`, `move != best`, décision Q4 sprint 35) :
   un sacrifice qui marche est souvent le meilleur coup.
2. Sacrifice mesuré **net** après 6-10 demi-coups (`_line_sacrifice`) : un Fxf7+ ou un pion
   de gambit regagnés comptent 0. Le matériel offert sur le coup (`offered`) est calculé
   mais `_admissible` ne le lit pas.
3. Tolérance : perte ≤ 5 pts de % de gain (≈ 0,55 pion autour de l'égalité), ≤ 15 avec
   piège ≥ 10 (`_WINDOW`, `_TRAP_WINDOW`). Origine : Q5 sprint 27, posée d'emblée (pas
   baissée ensuite) ; le palier 15 est venu du Smith-Morra 8.Cd5 (perte ≈ 12 pts).
4. Fenêtre 35-75 % (`_WIN_MIN`, `_WIN_MAX`) : au-delà de +3 pions environ, aucune recherche.
5. Aucun motif d'attaque sur le roi ; seuls échec / prise / menace / matériel offert.
   Candidats approfondis plafonnés à 3 (`_MAX_DEEP`).

### Arbitrages déjà donnés par Nico (2026-10-23)

- Le meilleur coup est montré s'il est un sacrifice ou un autre motif tactique.
- Le piège humain fait partie de la définition (réponse logique de l'adversaire → il est
  moins bien) : l'espérance Maia reste un critère.
- Tolérance : deux pions (le gambit Göring offre deux pions). **À préciser** : deux pions
  de **matériel offert**, ou deux pions de **perte d'évaluation** ? Le Göring est évalué par
  le moteur bien au-dessus de −2 grâce à la compensation.
- Fenêtre de positions éligibles élargie (borne haute à chiffrer, ex. 90 %).
- Gambits d'ouverture, Fxf7+, Fxh7+ doivent apparaître : cas de test à fournir / choisir.

### Cas de test de Nico et mesure du moteur actuel (2026-10-23)

Mesure : Stockfish 3 s MultiPV 8, puis `_deepen` / `_admissible` de `explosive.py` sur le coup
visé, Maia Elo 1500 [n=1 par cas, Threads=8 : non déterministe].

**Cas A — 1.e4 e5 2.Cf3 Cc6 3.d4 exd4, blancs au trait.** Attendus : 4.c3 (Göring) ou
4.Fc4 (gambit écossais) au lieu de 4.Cxd4.

| Coup | % gain | perte | sacrifice net | offert | piège | E humaine / E meilleur | admis |
|---|---|---|---|---|---|---|---|
| 4.Cxd4 (meilleur) | 53,2 | 0 | 0 | 0 | 0 | 56,0 / 55,3 | non |
| 4.Fc4 | 49,8 | 2,4 | 0 | 0 | 0 | 53,3 / 56,6 | non |
| 4.c3 | 49,0 | 5,1 | 0 | 0 | 0 | 49,4 / 57,1 | non |

Rejet : aucune mesure ne voit le gambit. Le pion n'est pas « offert » sur la case d'arrivée
(4.Fc4 laisse simplement le pion d4 non repris ; 4.c3 offre un pion défendu par Cb1, que
`_natural_capture` écarte) ; le sacrifice net est nul ; Maia ne donne pas de gain d'espérance
(le gambit est moins bon que 4.Cxd4 face à un humain 1500). 4.c3 dépasse aussi la fenêtre 5
de 0,1 pt. → il manque une mesure du type « accepte d'avoir du matériel en moins sur la
suite » (déficit tenu sur la PV), indépendante de la case d'arrivée.

**Cas B — 1.e4 e5 2.Cf3 Cc6 3.d4 exd4 4.c3 dxc3 5.Fc4 Fc5, blancs au trait.** Attendu :
6.Fxf7+ Rxf7 7.Dd5+ (fourchette roi / Fc5, roi déroqué).

| Coup | % gain | perte | sacrifice net | offert | piège | E humaine / E meilleur | admis |
|---|---|---|---|---|---|---|---|
| 6.Fxf7+ (meilleur) | 57,9 | 0 | 2 | 2 | 0 | 60,6 / 60,3 | **oui** |
| 6.Cxc3 | 48,7 | 10,0 | 0 | 0 | 0 | 54,7 / 60,6 | non |

Rejet : uniquement parce que c'est le meilleur coup (`move != best`). Les filtres actuels
l'admettent → lever l'exclusion du meilleur coup (arbitrage Nico) suffit pour ce cas.

### Question ouverte : coût des motifs d'attaque

- Détection : `chess_coach/motifs.py` (portage cook.py, sprint 29) tague déjà `sacrifice`,
  `attraction`, `deflection`, `exposedKing`, mats nommés sur une ligne. Appliqué à la PV du
  candidat : calcul Python sur une ligne déjà fournie par le moteur, coût quasi nul
  [non mesuré]. Un critère plus simple (sacrifice avec échec ou près du roi adverse) l'est
  aussi.
- Ce qui coûte : approfondir plus de candidats (chaque candidat = 2-3 appels moteur à
  0,3-0,6 s + sa part de la passe Maia), sous le budget ≤ 10 s de la passe ×1. Fxh7+ et
  Fxf7+ sont des échecs-prises, donc déjà dans les candidats « par forme » ; un sacrifice
  calme (pièce posée en prise sans échec) aussi s'il atterrit sur une case attaquée.
- À trancher : motifs = critère d'admission, critère de tri, ou les deux ; `_MAX_DEEP`.

### Portée

`explosive.py` sert aussi l'analyse de partie Telegram (`find_explosive`) : la nouvelle
définition s'applique-t-elle aux deux (échiquier live et analyse de PGN) ? À arbitrer.

─────────────────────────────────────────────────────────────────────────

## Dettes ouvertes au 2026-10-23 (post sprint 35)

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
| 94 | Échiquier d'analyse rejouable (chessground) avec flèches meilleur / explosif ; calque Chess.com limité à l'écran d'analyse post-partie (fair-play) | **partiellement résolue sprint 35** : échiquier de jeu hébergé par ARIA (port 5002) avec calque explosif continu ; rejeu d'une partie PGN non traité ; calque chess.com abandonné |
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
| 121 | Coups explosifs trop rares : gambits d'ouverture, Fxf7+, sacrifice grec non signalés ; meilleur coup exclu, sacrifice mesuré net après l'échange, fenêtre 35-75 % [retour run live sprint 35] | ouvert, cible sprint 36 |

Hors dettes (Q4 sprint 27) : rangement des fiches `chess_game` en wing `echecs` / room
par ouverture.

─────────────────────────────────────────────────────────────────────────

## Préalable matériel

- `feat/sprint35-echiquier` mergé sur `main`, tag `sprint-35` sur le commit de clôture documentaire.
- Branche sprint 36 à créer en conception.
- Prochaine étape : `/conception sprint 36`.
