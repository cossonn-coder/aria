# ARIA — Reprise sprint 6
**Mis à jour : 7 mai 2026**
**État : sprint 5 architectural clos — 175 tests verts, tag `sprint-5` posé**

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

## Méthodologie sprint 4-5 à conserver

Cinq disciplines qui ont prouvé leur valeur sur les deux derniers
sprints :

1. **Audit avant fix.** Sur tout sujet non-trivial, demander à Claude
   Code un audit en lecture seule avant le fix. Le fix arrive dans un
   tour séparé. T4-A sprint 5 a invalidé l'hypothèse de départ
   (doublons sémantiques) et révélé la vraie racine (espace
   d'embedding plat) — bénéfice direct de cette discipline.

2. **Spot-check préalable au fix.** T2 sprint 5 a évité un fix mort.
   L'audit T1 proposait `metadata.operation` mais le spot-check du
   bridge a révélé que mempalace_store filtre les metadata custom.
   Bascule sur Option A (operation portée par room) AVANT toute
   ligne de code modifiée. Sans le spot-check, le fix aurait été
   commit, mergé, et silencieusement cassé.

3. **Diff réel avant validation.** Ne jamais valider sur le résumé
   que Claude Code donne — toujours demander le diff brut.

4. **Instrumentation avant diagnostic.** Quand un bug silencieux
   apparaît, ne pas spéculer — ajouter un log temporaire, provoquer
   le bug, lire les valeurs réelles.

5. **Run live entre chaque migration/fix.** Tests verts ne suffisent
   pas. Restart aria.service + 1-2 messages Telegram + lecture
   journalctl. T2 et T3 sprint 5 ont été validés par run live —
   "classifier cache HIT sim=1.000" et "provider cerebras
   rate-limited (429), caching for 300s" sont des preuves prod.

6. **Refus du scope creep.** Pendant le sprint 5, on a découvert
   #22 (intent_naming truncation au caractère). Documenté en
   dette, pas corrigé dans le sprint. Le sprint a livré ses 3
   commits comme prévu.

7. **Économie de la fenêtre de contexte (nouveau).** Au-delà de
   ~60% de remplissage, l'architecte propose une clôture
   intermédiaire. Sprint 5 clos à ce seuil avec le fix #18 reporté
   à sprint 6 — meilleur que d'avoir une session qui s'effondre
   au milieu du fix.

---

## Contexte rapide ARIA

ARIA = kernel cognitif personnel local pour Nico. Single-user.
Bot Telegram + service systemd sur Debian (vDebianIA).

Compte Claude Code : `dodgemyspoon@gmail.com` (Pro), session active
dans `~/Nextcloud/projects/aria` sur la Debian.

Anthropic API : pay-as-you-go, Haiku-4.5, ~0.0007$ par appel.
DeepSeek V4 Flash disponible via clé personnelle, $5 chargés —
intégration en pipeline ARIA réservée à un sprint ultérieur (cf.
piste B).

---

## Sprint 5 clos — bilan

**Trois commits posés sur la branche de travail, tag `sprint-5` :**

- **b0aaee5 T2** : fix dette #20 (cache classifier). Le cache
  classifier était cassé depuis sa création — write indexait un
  JSON, search query un message brut, cosine similarity 0.47-0.60
  sur des messages identiques, jamais de hit ≥ 0.92. Spot-check
  bridge a révélé que mempalace_store filtre les metadata custom
  (n'expose que wing/room/similarity/distance/source_file/created_at).
  Bascule Option A : operation portée par room au lieu d'une
  metadata custom. Aucun patch infra requis. 3 tests garde-fous
  ajoutés. Wipe des 199 entrées legacy + run live confirmé :
  `classifier cache HIT sim=1.000 op=fact_recall` sur message
  identique répété.

- **3b57136 T3** : fix dette #8 (cache négatif providers LLM).
  Cache RAM par provider, TTL 5 min (configurable). Détection 429
  via `httpx.HTTPStatusError.response.status_code` — distingue
  proprement 429 (à cacher) de 5xx/timeouts (à laisser passer).
  4 tests garde-fous + 1 bonus. Run live confirmé : Cerebras
  429 → cached 300s → fallback Anthropic OK.

- **T11 (clôture)** : commit doc avec audit intent matching
  (docs/sprint5/audit_intent_matching.md, 644 lignes + cas 5
  multi-tour) et ce kickoff sprint 6. Tag sprint-5 posé sur ce
  commit.

**Audit intent matching (dette #18) — découvertes structurelles**

L'audit T4-A a invalidé deux hypothèses initiales :

- Hypothèse "doublons sémantiques attractifs" : **infirmée**.
  Aucune paire d'intents > 0.85 sur 1770 comparaisons, top à
  0.668 (`intents` ↔ `connaître intents`). L'espace
  d'embedding all-MiniLM-L6-v2 est plat.

- Hypothèse "deux mécanismes de matching en concurrence (dette #3)" :
  **partiellement infirmée**. Les deux mécanismes existent
  (IntentRecallEngine.resolve sur message brut + IntentEngine.
  _find_by_name_semantic sur nom canonique LLM) mais
  s'enchaînent séquentiellement, pas en concurrence. Tous les
  bugs observés franchissent le seuil 0.45 du premier mécanisme,
  donc le second n'est jamais consulté. Le second n'est pas en
  cause.

**Cause racine établie (triple)** :

1. Espace d'embedding plat. Le seuil 0.45 capture mécaniquement
   tout intent vaguement aligné avec le centroïde français.
2. Embedding calculé sur le `name` seul (pas de description, pas
   d'extraits d'actions_history). Pour un nom court FR, le vecteur
   dérive vers le centroïde de la langue.
3. Intents "absorbants" comme `Pourquoi elle ne germent pas`
   (verbe générique + pronom + négation + mot-contenu) attirent
   massivement des messages sans rapport.

**Bugs reproduits à la main avec le vrai embedder** :

- "Les carottes en ragoût recette" → 0.642 sur `carottes dans
  jardin` (ATTACH faux, le mot "carottes" domine).
- "Planifier des vacances en Normandie" → 0.466 sur `Pourquoi
  elle ne germent pas` (top 1). `voyage organisation` (32 actions)
  absent du top 5.
- "Tu vas bien ?" → 0.496 sur `semis en intérieur` (top 1).
  `salutation` < 0.38.
- Cas 5 (conversation cuisine fragmentée multi-tour) : aucun
  signal de continuité conversationnelle utilisé. L'intent fil
  rouge change en cours de conversation, et un message contextuel
  (inventaire cuisine) crée un nouvel intent au lieu de s'attacher
  au fil en cours.

**Cinq leviers de fix identifiés (à arbitrer en kickoff sprint 6)** :

| Levier | Coût | Risque | Bénéfice |
|---|---|---|---|
| Changer d'embedder (mpnet, e5, bge-m3) | Moyen | Faible | Fort, structurel |
| Remonter seuil 0.45 → 0.55-0.60 | Très faible | Moyen (peut empirer la fragmentation) | Modéré, à mesurer |
| Signal de continuité conversationnelle | Moyen | Faible si bien borné | Fort sur multi-tour |
| Embedder sur name + description | Faible | Faible | Modéré |
| Re-rank LLM sur top-3 ATTACH | Plus coûteux (1 LLM/msg) | Moyen | Très fort sur cas pathologiques |

---

## Dettes hiérarchisées pour sprint 6

### Priorité 1 — Bloquant pour usage quotidien

**Dette #18 — Intent matching erratique.** Reprise du chantier
sprint 5. Audit fait, fix à arbitrer + implémenter + valider.
Tours estimés : 5-7 selon la combinaison de leviers retenue.

Si la combinaison choisie inclut le changement d'embedder, prévoir
un tour dédié pour mesurer ex-post l'effet sur les 4 cas terrain
+ cas 5 multi-tour. La discipline "mesurer before/after avec les
mêmes messages" doit être respectée.

### Priorité 2 — Bloquant pour lisibilité

**Dette #22 (nouvelle, sprint 5) — intent_naming illisible.**
`extract_intent_name` produit des noms tronqués au caractère
plutôt qu'au mot. Exemples observés en prod :
- `"Je veux apprendre la validation fonctionnelle sur des capteu"`
- `"Dans ma cuisine j'ai : Une cocotte, une poêle, une planche à"`

Deux dimensions du bug :
- Le LLM n'a pas toujours respecté la consigne "2-5 mots maximum"
  du prompt (cf. `llm/intent_namer.py:18`).
- Le slicing `[:60]` tronque sans respect des mots.

Un nom acceptable serait `"valid fonctionnelle capteur image"` —
court, mots-clés visibles, lisible en lecture rapide.

Fix probable : renforcer le prompt namer (few-shots supplémentaires
sur des messages longs) + tronquer au dernier espace avant 60 chars.
1-2 tours estimés. À traiter probablement avant ou en parallèle
de #18 — la lisibilité du nom impacte aussi la dedup
`_find_by_name_semantic` (mécanisme B).

### Priorité 3 — Vocabulaire ARIA (architectural)

**Dette nouvelle — Taxonomie message à clarifier.** Ce qu'on
appelle aujourd'hui "intent" mélange plusieurs catégories qui
devraient avoir des comportements différents :

| Catégorie | Exemple | Comportement attendu |
|---|---|---|
| Intent actionnable | "recette carottes 6 pers" | Mémorisation longue, attachement persistant, suivi multi-tour |
| Thème conversationnel | "salut" / "tu vas bien ?" | Pas de persistence, intent volatil |
| Demande informative | "infos Vercors randonnées" | Web search/RAG, attachement à un sujet sans plan d'action |
| Mémoriel pur | "code Jonas 9041" | STORE_FACT, pas de réponse, pas d'intent au sens matching |

Une taxonomie en amont peut diviser par 3-4 le périmètre de
bugs #18 — un message catégorisé "mémoriel pur" n'a pas à passer
par le matching d'intent du tout.

Nico va consulter Gemini/ChatGPT avec un prompt préparé pour
compléter la taxonomie (catégories oubliées, sous-catégories
utiles, cas frontaliers). Résultat à apporter en sprint 6 pour
arbitrage.

Trop gros pour être implémenté en sprint 6. Prévoir un sprint
dédié (sprint 7+) une fois la taxonomie validée.

### Priorité 4 — Dettes techniques structurelles (rappel sprint 5)

- **Dette #2** — Cosine recalculé O(N) dans
  `intent_engine._find_by_name_semantic` (négligeable à 60 intents,
  à indexer si croissance > quelques centaines).

- **Dette #3** — Deux mécanismes de matching d'intent en parallèle.
  Audit sprint 5 a précisé : ils sont séquentiels, pas concurrents.
  À nettoyer si le fix #18 ne les unifie pas naturellement.

- **Dette #4** — Marge fragile sur scoring nu
  (`tests/intent/test_intent_dedup.py:test_regression_bug_e_real_embeddings`),
  score 0.4889 vs seuil 0.45.

- **Dette #5** — Suivi des opérations sur la donnée. Logger chaque
  ID supprimé dans un fichier audit, mesurer before/after par
  wing+room avec filtre explicite.

- **Dette #10** — Audit IMAGE_INPUT.

- **Dette #14** — Tension architecturale `MemoryStack` (4 couches
  L0/L1/L2/L3 de MemPalace) vs architecture ARIA actuelle.

- **Dette #15** — Tests `memory/writer.py` incomplets.

- **Dette #16** — Tests `test_llm_execution_router.py` ne couvrent
  pas l'écriture mémoire post-T4 sprint 4.

- **Dette #17** — Bloc-note explicite. Mécanisme `store_semantic_fact`
  triggéré par marqueurs explicites dans le message ("à retenir",
  "rappelle-toi que"). Premier vrai appel à `aria_semantic` depuis
  le pipeline. Couvre le cas "code Jonas 9041" (cf. taxonomie
  mémoriel pur).

- **Dette #19** — Restructuration doc.

- **Dette #21** — Aria invente sur sujets pointus. Mitigation
  attendue : intégration DeepSeek V4 Flash en validation croisée
  ou web search.

- **Dette : 32 entrées résiduelles `mempalace_closets wing=aria`**.
  Non migrées sprint 4. À arbitrer si un usage les justifie.

- **Dette : `IntentCompressionEngine` inactif.** Seuil 0.78 jamais
  atteint sur l'espace plat actuel. Devient pertinent SI on change
  d'embedder en sprint 6 — auquel cas le seuil 0.78 redevient
  réaliste.

- **Dette : aucun log des scores d'intent en prod.** Le call-site
  `IntentEngine.resolve` jette `scored`. Instrumentation
  indispensable pour T-B sprint 6.

- **Dette : doublon de classes `RecallDecision` vs
  `IntentRecallDecision`.** Marche par hasard (héritage `str` sur
  `IntentActionType`). Dead code candidat.

### Priorité 5 — Features post-stabilisation

**Intégration DeepSeek V4 Flash dans `llm/llm_router.py`.** Décision
Nico validée mais reportée — à intégrer comme provider fallback ou
premier choix sur certains rôles.

**Knowledge graph** — vision long-terme.

**Mining contraint** — vision long-terme.

**Agent diaries** — vision long-terme.

**Métacognition (`aria_self`)** — vision long-terme.

**Instrumentation usage CLI DeepSeek** — log dans
`~/.deepseek_usage.log`.

---

## Périmètre proposé pour sprint 6 — à arbitrer en kickoff

Trois pistes possibles. Mon vote architecte : Piste A.

### Piste A — Fermer la dette #18 (recommandée)

Sprint focalisé sur le bug le plus impactant en usage quotidien.

- **T-Z renommage de branche** (1 tour, mécanique) :
  `feat/sprint2-image-pipeline` → `develop` (ou autre nom à
  arbitrer en kickoff).
- **Dette #22** (intent_naming truncation) — fix court avant ou
  en parallèle de #18, parce qu'un nom illisible perturbe la
  lecture des logs T-B. 1-2 tours.
- **Dette #18 T-B** : instrumentation des scores d'intent en prod
  (log top-3 par message, scored complet). 1 tour. Nico fait
  tourner ARIA 2-3 jours en usage normal pour collecter la donnée.
- **Dette #18 T-C** : décision archi sur la combinaison de leviers
  à appliquer (sur base de la donnée T-B). 1 tour, pas de code.
- **Dette #18 T-D** : implémentation. 1-3 tours selon la
  combinaison.
- **Dette #18 T-E** : validation run live + reproductibilité des
  4 cas terrain + cas 5 multi-tour. 1 tour.

Total estimé : 6-9 tours. Sprint qui rend ARIA significativement
plus fiable en usage quotidien.

### Piste B — Stabilisation infra

Sprint orienté nettoyage, à reporter si #18 n'est pas clos.

- Renommage de branche.
- Intégration DeepSeek V4 Flash + instrumentation usage.
- Restructuration doc (dette #19).
- Dette #15 + #16 (tests writer.py + llm_execution_router complétés).
- Nettoyage doublons RecallDecision / IntentRecallDecision.

Total estimé : 5-7 tours.

### Piste C — Vision long-terme

Sprint ambitieux post-stabilisation. À retarder jusqu'à ce que
#18 soit clos.

- Knowledge graph
- Mining contraint
- Agent diaries

**Recommandation forte : Piste A en sprint 6, Piste B en sprint 7,
Piste C en sprint 8+.**

---

## Décisions à acter dès le kickoff sprint 6

1. **Nom de la nouvelle branche.** Reco architecte : `develop`.
   Alternatives : `feat/cognitive-kernel`, `feat/aria-runtime`,
   `main` (si pas pris). Premier tour sprint 6 = renommage local
   + push de la nouvelle branche + suppression côté origin de
   l'ancienne + mise à jour de la branche par défaut sur GitHub
   (action manuelle de Nico via interface web).

2. **Combinaison de leviers pour fix #18.** À arbitrer après
   le retour de l'instrumentation T-B. Une décision prématurée
   sans donnée terrain est risquée — l'audit T4-A a montré que
   les hypothèses peuvent s'invalider.

3. **Ordre #22 vs #18.** Mon vote : #22 d'abord (court), pour
   que les logs T-B soient lisibles. Mais c'est arbitrable.

4. **Taxonomie message (priorité 3).** Nico apporte le résultat
   Gemini/ChatGPT en kickoff. Décision : on inscrit la taxonomie
   dans le sprint 6 (lecture seule, ajout au backlog) ou on reporte
   au sprint 7+ une fois #18 clos.

---

## Contraintes techniques connues

ARIA tourne sur une VM Debian (vDebianIA) en single-user. Telegram
bot + service systemd. Mémoire vectorielle via MemPalace v3.3.x
(externe, GitHub.com/MemPalace/mempalace). Pour mettre à jour la
version installée :
`pip install --upgrade "mempalace @ git+https://github.com/MemPalace/mempalace.git@develop"`.

Branche de travail à renommer en premier tour sprint 6
(actuellement `feat/sprint2-image-pipeline`). Pas de push origin
avant validation explicite Nico.

Vision long-terme : ARIA est un système cognitif partageable, chaque
utilisateur ayant son propre palace MemPalace isolé.

---

## Ressources clés

- `.env` : `/home/nico/Nextcloud/projects/aria/.env`
- MemPalace : `/home/nico/.mempalace/palace`
- Intents : `~/.aria/intents.json` (61 intents, 60 active)
- Service : `sudo systemctl restart aria.service`
- Logs : `sudo journalctl -u aria -f -o cat`
- Diagnostic mémoire : `./venv/bin/python scripts/count_memory_by_wing.py`
- Diagnostic cache classifier : archivé dans `scripts/archive/diagnose_classifier_cache_similarity.py`

---

## Premier message à envoyer dans la nouvelle session

> Reprise sprint 6. Voici le context [PIÈCE JOINTE].
>
> Sprint 5 clos — 3 commits, tag `sprint-5` posé. Cache classifier
> (#20) et cache négatif providers (#8) fixés et validés en run
> live. Audit intent matching (#18) livré : 644 lignes,
> hypothèses initiales invalidées, racine identifiée (espace
> d'embedding plat + name-only embedding + intents absorbants).
> 5 leviers de fix possibles, à arbitrer.
>
> Cette session est un KICKOFF — décisions à arbitrer :
> 1. Nom de la nouvelle branche (reco : `develop`).
> 2. Ordre #22 (intent_naming) vs #18 (matching).
> 3. Combinaison de leviers à appliquer pour #18 (à n'arbitrer
>    qu'après retour de l'instrumentation T-B, donc plus tard
>    dans le sprint).
> 4. Taxonomie message — résultat Gemini/ChatGPT à coller si
>    j'ai eu le temps de la consulter.
>
> Aide-moi à trancher. Pas de code dans cette session de kickoff.