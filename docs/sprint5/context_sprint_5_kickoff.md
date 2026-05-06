# ARIA — Reprise sprint 5
**Mis à jour : 2 mai 2026**
**État : sprint 4 architectural clos — 169 tests verts, tag `sprint-4` posé**

---

## Workflow de cette session (à mémoriser)

Nico travaille avec **deux instances de Claude en parallèle** :

1. **Architecte (cette session, claude.ai)** — analyse, critique, plan,
   prépare les messages destinés à Claude Code, valide les livrables.
   Toujours en français. Esprit critique sur les propositions, y
   compris celles de Nico.

2. **Implémenteur (Claude Code dans la VM Debian)** — exécute, code,
   teste, commit. Il livre du concret : diffs, tests, audits.

**Cycle d'un tour :**
1. Nico colle ici un contexte (ce document + résultat du dernier livrable Claude Code)
2. L'architecte analyse, critique, et **rédige un message destiné à Claude Code**
3. Nico copie ce message dans Claude Code, qui exécute
4. Claude Code retourne un livrable (diff, tests, audit, log)
5. Nico recolle le livrable ici → retour étape 2

Les fichiers dont l'architecte a besoin pour réfléchir, Nico les fournit
manuellement. Les actions sur le code, Nico les délègue à Claude Code
via le message rédigé. **L'architecte ne touche jamais directement
au code.**

Le sprint se termine quand l'architecte considère qu'il n'y a plus
de décisions à prendre — restitution finale au format identique à
celui-ci pour la session suivante.

---

## Méthodologie sprint 4 à conserver

Quatre disciplines qui ont prouvé leur valeur sur le sprint 4 :

1. **Audit avant fix.** Sur tout sujet non-trivial, demander à Claude
   Code un audit en lecture seule avant le fix. Le fix arrive dans un
   tour séparé. Cette règle a évité plusieurs faux départs sur des
   migrations où l'audit a révélé moins de callers (ou plus) que
   prévu.

2. **Diff réel avant validation.** Ne jamais valider sur le résumé
   que Claude Code donne — toujours demander le diff brut. T5b a
   attrapé un bug enum→str silencieux qui aurait cassé le cache
   classifier en prod. T6 a révélé 23 mocks au lieu des 2 annoncés
   dans l'audit.

3. **Instrumentation avant diagnostic.** Quand un bug silencieux
   apparaît, ne pas spéculer — ajouter un log temporaire,
   provoquer le bug, lire les valeurs réelles. T7-bis-3 a évité
   plusieurs hypothèses fausses en révélant similarity=0.111
   inattendue.

4. **Run live entre chaque migration.** Tests verts ne suffisent
   pas. Restart aria.service + 1-2 messages Telegram + lecture
   journalctl + count_memory_by_wing.py. Les tests passent sur des
   mocks ; le run live valide sur la vraie base.

5. **Refus du scope creep.** Pendant le sprint 4, on a découvert
   #18 (intent matching cassé), #20 (cache classifier cassé),
   #21 (Aria invente sur sujets pointus). Aucun n'a été corrigé
   dans le sprint. Tous documentés en dette. Le sprint a livré
   ses 7 commits architecturaux comme prévu.

---

## Contexte rapide ARIA

ARIA = kernel cognitif personnel local pour Nico. Single-user.
Bot Telegram + service systemd sur Debian (vDebianIA).

Compte Claude Code : `dodgemyspoon@gmail.com` (Pro), session active
dans `~/Nextcloud/projects/aria` sur la Debian.

Anthropic API : pay-as-you-go, Haiku-4.5, ~0.0007$ par appel.
DeepSeek V4 Flash disponible via clé personnelle, $5 chargés —
intégration en pipeline ARIA en candidature pour ce sprint
(décision Nico : OK, conscient du trade-off données / Chine).

---

## Sprint 4 clos — bilan

**Décision architecturale prise au kickoff sprint 4** : ARIA devient
client de MemPalace via son API publique. Migration en strangler
pattern, code nouveau à côté de l'ancien, bascule progressive.

**7 commits posés sur `feat/sprint2-image-pipeline`, tag `sprint-4` :**

- **65618fa T3** : création `memory/writer.py` (4 fonctions
  d'écriture explicites : write_interaction, write_image_artifact,
  write_semantic_fact, write_classifier_cache. Wing/room/type
  structurels, non surchargeables via metadata. Patron `meta`
  avec spread `extra` PUIS structurels — verrouillage anti-W4).
  10 tests garde-fous.

- **30f0fc5 T4** : migration W4 (LLMExecutionRouter step 10).
  Le bug `wing="aria"` (dette #11) est supprimé par migration vers
  `write_interaction`, pas par patch isolé. Run live confirmé :
  3 messages Telegram → 3 écritures `aria_episodic`, +0 dans
  `aria`.

- **190b522 T5** : migration W5 (CognitiveClassifier `_store_cache`).
  Bug enum→str attrapé en review architecte avant run live —
  `operation.value` ajouté côté caller, garde-fou test ajouté.
  Sans cette review, le cache aurait silencieusement cessé de
  s'écrire (try/except autour avale l'exception).

- **0925272 T6** : migration W2 (ImageExecutionRouter, 2 sites).
  Migration mécanique. 23 mocks de test mis à jour sur 4 fichiers
  (audit T6a en avait identifié 2 — leçon : explicitement demander
  les sites de mock dans les audits futurs).

- **bef4eb3 T7** : migration R5 (CognitiveClassifier `_search_cache`).
  Option A retenue (paramètre `bridge` injecté explicitement
  jusqu'à `classify_operation`). 4 garde-fous test ajoutés.
  CognitiveEngine reçoit maintenant le bridge en constructeur,
  cohérent avec LLMExecutionRouter et ImageExecutionRouter.
  La règle 5 originelle de CLAUDE.md est révisée en conséquence.

- **6cce38f T7-bis** : `MempalaceBridge.retrieve_memories` étendu
  avec `max_distance: float | None = 0.8` (compatibilité
  ascendante). `_search_cache` passe `max_distance=None` pour
  ne pas se faire pré-filtrer ses candidats. Diagnostic
  T7-bis-6 révèle un bug pré-existant dans le cache classifier
  (cf. dette #20 ci-dessous). Scripts de diagnostic conservés
  dans `scripts/`.

- **77ef96c T8** : suppression `mempalace_writer.py` +
  3 sites code mort (`media/image_service.py`,
  `execution/routers/ingestion_router.py`, +2 tests
  ImageService). 5 tests writer ancien supprimés. Q4 trivial :
  `mempalace_store.search` paramètre `wing` rendu obligatoire.
  -907 lignes nettes.

- **290d368 T9** : commit vide ancrant l'exécution du script
  `migrate_wing_aria_to_episodic.py --execute`. 81 entrées
  orphelines `wing=aria` migrées vers `aria_episodic`. Sanity
  check Telegram positif — Aria remonte du contexte historique
  qui était jusqu'ici inaccessible.

**État cible mémoire ARIA après sprint 4** :

- **`aria_episodic`** : événements conversationnels (interactions,
  images reçues, images générées). Indexé par `intent_id` (room).
  ~408 entrées.
- **`aria_semantic`** : faits stables sur l'utilisateur. **0 caller
  prod actuel** — la couche existe en infrastructure mais n'est
  jamais alimentée par le pipeline normal. Cf. dette #17.
- **`aria_classifier`** : cache du classifier d'opérations.
  ~199 entrées, mais **fonctionnellement cassé depuis sa création**
  (cf. dette #20).
- **`aria`** : 0 entrée dans `mempalace_drawers`. **32 entrées
  résiduelles dans `mempalace_closets`** non migrées (hors scope
  sprint 4, à arbitrer si un usage justifie leur migration).

---

## Dettes hiérarchisées pour sprint 5

### Priorité 1 — Bloquantes pour usage quotidien

**Dette #18 — Intent matching erratique.** Symptômes observés en
run live au sprint 4 :
- Message "Donne moi un déroulé pour préparer une marinade soja
  gingembre" → rattaché à intent "Pourquoi elle ne germent pas"
- Message "Quelle variété de tomate j'avais semée déjà ?" →
  rattaché à intent "gestion de la sécurité"
- Message "Tu vas bien ?" → rattaché à intent "semis en intérieur"

Le fix F1 du sprint 3.1 (suppression du boost `mem_score` dans
`IntentRecallEngine.resolve()`) ne couvre pas tous les cas. Très
probablement lié à la dette #3 (deux mécanismes de matching d'intent
en parallèle : `intent_recall_engine.resolve` + `intent_engine._find_by_name_semantic`).
Conséquence utilisateur : ARIA répond parfois complètement à côté
du sujet, mélange des contextes de messages anciens, ne pose pas
de question de clarification quand l'intent est manifestement faux.

**Dette #20 — Cache classifier cassé depuis sa création.** Diagnostic
T7-bis-6 prouvé :
- `write_classifier_cache` indexe le document
  `json.dumps({"message": M, "operation": O})` dans ChromaDB.
- `_search_cache` cherche avec `query=M` (le message brut).
- L'embedder calcule deux vecteurs sémantiquement différents.
- Cosine similarity ~0.47-0.60 sur des strings strictement identiques.
- Jamais ≥ 0.92, jamais de hit cache.
- Embedder cohérent (ONNXMiniLM_L6_V2), métrique cosine confirmée
  via `scripts/diagnose_chroma_metric.py`.

Conséquence : chaque message déclenche un appel LLM classifier.
Coût en tokens et 2-4s de latence en cas de fallback chain
Cerebras→OpenRouter→Anthropic. ~199 entrées `aria_classifier`
sont du déchet jamais lu.

**Fix proposé** : aligner ce qui est embedé en écriture avec ce
qui est cherché en lecture. Stocker `message` brut comme document
ChromaDB et `operation` en metadata. Simple à implémenter, mais
demande de migrer les ~199 entrées existantes (ou les supprimer
et accepter de partir cache vide). Décision à prendre en kickoff.

**Dette #8 — Cache négatif providers LLM en quota.** Cerebras et
OpenRouter (free tier) renvoient régulièrement 429. La fallback
chain fonctionne mais ajoute 2-4s par message vers Anthropic.
Fix : cacher les 429 pendant N minutes (5 min suggéré) pour skipper
directement le provider en quota.

### Priorité 2 — Qualité d'usage

**Dette #21 (nouvelle) — Aria invente sur sujets techniques pointus.**
Incident "binning Bayer" lors d'un entretien : réponse confiante
mais factuellement fausse. Pas un bug ARIA, c'est le LLM qui
hallucine. Mitigations possibles :
- mode "confiance basse" : Aria dit "je ne maîtrise pas assez ce
  sujet pour te répondre correctement" sur certains domaines
- branchement web search pour les questions techniques
- intégration DeepSeek V4 Flash en validation croisée

### Priorité 3 — Dettes techniques structurelles

**Dette #2** — Cosine recalculé O(N) dans
`intent_engine._find_by_name_semantic` (négligeable à 50 intents,
à indexer si croissance).

**Dette #3** — Deux mécanismes de matching d'intent en parallèle.
À unifier. Probablement lié à #18.

**Dette #4** — Marge fragile sur scoring nu
(`tests/intent/test_intent_dedup.py:test_regression_bug_e_real_embeddings`),
score 0.4889 vs seuil 0.45.

**Dette #5** — Suivi des opérations sur la donnée. Logger chaque
ID supprimé dans un fichier audit, mesurer before/after par
wing+room avec filtre explicite.

**Dette #10** — Audit IMAGE_INPUT. Le router n'appelle la pipeline
cognitive complète que si la caption est interrogative. Profil
pathologique potentiel à investiguer.

### Priorité 4 — Nettoyage

**Dette #14** — Tension architecturale `MemoryStack` (4 couches
L0/L1/L2/L3 de MemPalace) vs architecture ARIA actuelle. Arbitrer
ou non l'adoption. Hors scope sprint 4 confirmé, à arbitrer plus
tard.

**Dette #15** — Tests `memory/writer.py` incomplets. 4 cas non
couverts dans `test_writer.py` (validate_missing_fields,
idempotence_diff_bucket, image_artifact_skip_empty,
required_fields_constant). Compléter en sprint nettoyage.

**Dette #16** — Tests `test_llm_execution_router.py` ne couvrent
pas l'écriture mémoire post-T4 (mocking au mauvais niveau). À
adapter.

**Dette #17** — Bloc-note explicite. Mécanisme `store_semantic_fact`
triggéré par marqueurs explicites dans le message utilisateur
("à retenir", "rappelle-toi que", "pour info"). Premier vrai
appel à `aria_semantic` depuis le pipeline. Demande utilisateur
explicite (incident "Code Jonas = 9041").

**Dette #19** — Restructuration doc. Convention `docs/sprint_<N>/`
cohérente, déplacement des `context_sprint_*.md` de la racine
vers `docs/`. CLAUDE.md et README.md restent à la racine.

**Dette : 32 entrées résiduelles `mempalace_closets wing=aria`**.
Non migrées au sprint 4. À arbitrer si un usage les justifie.

### Priorité 5 — Features post-sprint

**Intégration DeepSeek V4 Flash dans `llm/llm_router.py`.** Décision
Nico validée : OK pour ses données (pas de mots de passe ni
identifiants). À intégrer comme provider fallback ou comme
premier choix sur certains rôles `LLMRole`. Décider quels rôles.

**Knowledge graph** — vision long-terme.

**Mining contraint** — vision long-terme.

**Agent diaries** — vision long-terme.

**Métacognition (`aria_self`)** — vision long-terme.

**Instrumentation usage CLI DeepSeek** — log dans
`~/.deepseek_usage.log` à chaque appel `ask-deepseek` /
`write-deepseek` pour mesurer l'économie réelle ex-post.

---

## Périmètre proposé pour sprint 5 — à arbitrer en kickoff

Trois pistes possibles. Mon vote architecte : Piste A.

### Piste A — Dettes critiques bloquantes (recommandée)

Sprint focalisé sur ce qui dérange l'usage quotidien.

- **Dette #18** : intent matching erratique. Le plus impactant.
  Probablement 3-5 tours.
- **Dette #20** : cache classifier (fix simple, choix entre
  migrer les 199 entrées ou repartir vide). 1-2 tours.
- **Dette #8** : cache négatif providers. 1 tour.

Total estimé : 5-8 tours. Sprint qui rend ARIA significativement
plus fiable et plus rapide en usage quotidien.

### Piste B — Intégration DeepSeek + restructuration

Sprint orienté infrastructure.

- Intégration DeepSeek V4 Flash dans `llm_router`, choix des rôles.
- Instrumentation usage CLI DeepSeek pour mesurer l'économie.
- Restructuration doc (dette #19).
- Dette #15 + #16 (tests writer.py + llm_execution_router complétés).

Total estimé : 4-6 tours.

### Piste C — Vision long-terme

Sprint ambitieux post-stabilisation.

- Knowledge graph
- Mining contraint
- Agent diaries

Plus risqué, plus lent. À retarder jusqu'à ce que la base soit
solide (donc après Piste A au moins).

**Recommandation forte : Piste A en sprint 5, Piste B en sprint 6,
Piste C en sprint 7+.**

---

## Contraintes techniques connues

ARIA tourne sur une VM Debian (vDebianIA) en single-user. Telegram
bot + service systemd. Mémoire vectorielle via MemPalace v3.3.x
(externe, GitHub.com/MemPalace/mempalace). Pour mettre à jour la
version installée :
`pip install --upgrade "mempalace @ git+https://github.com/MemPalace/mempalace.git@develop"`.

Branche de travail actuelle : `feat/sprint2-image-pipeline` (à
renommer un jour). Pas push origin avant validation explicite Nico.

Vision long-terme : ARIA est un système cognitif partageable, chaque
utilisateur ayant son propre palace MemPalace isolé.

---

## Ressources clés

- `.env` : `/home/nico/Nextcloud/projects/aria/.env`
- MemPalace : `/home/nico/.mempalace/palace`
- Intents : `~/.aria/intents.json`
- Service : `sudo systemctl restart aria.service`
- Logs : `sudo journalctl -u aria -f -o cat`
- Diagnostic mémoire : `./venv/bin/python scripts/count_memory_by_wing.py`
- Diagnostic cache classifier : `./venv/bin/python scripts/diagnose_classifier_cache_similarity.py`
- Diagnostic métrique ChromaDB : `./venv/bin/python scripts/diagnose_chroma_metric.py`

---

## Premier message à envoyer dans la nouvelle session

> Reprise sprint 5. Voici le context [PIÈCE JOINTE].
>
> Sprint 4 architectural clos — 7 commits, tag `sprint-4` posé.
> ARIA est désormais client propre de MemPalace : reads via bridge,
> writes via memory/writer.py. Strangler pattern complet.
>
> Cette session est un KICKOFF — on arbitre le périmètre sprint 5
> AVANT de toucher au code. Trois pistes proposées dans le context :
> A (dettes bloquantes — intent matching + cache classifier + cache
> providers), B (DeepSeek + restructuration), C (knowledge graph +
> long-terme).
>
> Aide-moi à trancher. Pas de code dans cette session de kickoff
> sauf si nécessaire pour relire des fichiers que tu ne peux pas
> retenir précisément (intent_engine, intent_recall_engine).