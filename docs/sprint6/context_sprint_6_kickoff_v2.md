# ARIA — Reprise sprint 6 (v2)
**Mis à jour : 7 mai 2026, fin de session kickoff initiale**
**État : sprint 5 architectural clos (175 tests verts, tag `sprint-5` local non pushé) ; audit T-Z livré ; travaux hors-workflow réalisés sur l'embedder ; taxonomie complétée en V2.**

---

## Workflow de cette session (rappel)

Nico travaille avec **deux instances de Claude en parallèle** :

1. **Architecte (claude.ai)** — analyse, critique, plan, prépare les
   messages destinés à Claude Code, valide les livrables. Toujours
   en français. Esprit critique sur les propositions, y compris
   celles de Nico.

2. **Implémenteur (Claude Code dans la VM Debian)** — exécute, code,
   teste, commit. Il livre du concret : diffs, tests, audits.

**Cycle d'un tour :** Nico colle ici un contexte (ce document +
résultat du dernier livrable Claude Code) → l'architecte analyse,
critique, et rédige un message destiné à Claude Code → Nico copie
ce message dans Claude Code, qui exécute → Claude Code retourne un
livrable (diff, tests, audit, log) → Nico recolle le livrable ici,
retour étape 2.

L'architecte ne touche jamais directement au code. Le sprint se
termine quand l'architecte considère qu'il n'y a plus de décisions
à prendre.

---

## Méthodologie sprint 4-5 à conserver

Sept disciplines validées par les sprints précédents :

1. **Audit avant fix.** Sur tout sujet non-trivial, audit en lecture
   seule avant le fix, dans un tour séparé. T4-A sprint 5 a invalidé
   l'hypothèse "doublons sémantiques" et révélé la racine "espace
   d'embedding plat" — bénéfice direct de cette discipline. T-Z
   sprint 6 a confirmé que la branche `main` existe déjà et n'est
   pas orpheline — bénéfice direct également.

2. **Spot-check préalable au fix.** T2 sprint 5 a évité un fix mort
   en révélant que `mempalace_store` filtre les metadata custom.
   Bascule sur Option A AVANT toute ligne de code modifiée.

3. **Diff réel avant validation.** Ne jamais valider sur le résumé
   que Claude Code donne — toujours demander le diff brut.

4. **Instrumentation avant diagnostic.** Quand un bug silencieux
   apparaît, ne pas spéculer — ajouter un log temporaire, provoquer
   le bug, lire les valeurs réelles.

5. **Run live entre chaque migration/fix.** Tests verts ne suffisent
   pas. Restart `aria.service` + 1-2 messages Telegram + lecture
   `journalctl`. T2 et T3 sprint 5 ont été validés par run live —
   "classifier cache HIT sim=1.000" et "provider cerebras
   rate-limited (429), caching for 300s" sont des preuves prod.

6. **Refus du scope creep.** Pendant le sprint 5, on a découvert
   #22 (intent_naming truncation) et #23 (naming en branche SPLIT).
   Documentés en dette, pas corrigés dans le sprint. Le sprint a
   livré ses 3 commits comme prévu.

7. **Économie de la fenêtre de contexte.** Au-delà de ~60% de
   remplissage, l'architecte propose une clôture intermédiaire.
   Sprint 5 clos à ce seuil avec le fix #18 reporté à sprint 6.
   Sprint 6 même contrainte.

**Discipline ajoutée en cours de sprint 6 — workflow asynchrone.**
Les travaux infra (config GPU, exploration modèles, achats hardware)
peuvent être délégués à d'autres LLM en parallèle de la session
architecte. **Mais toute modification du code ARIA doit revenir
dans le workflow architecte → Claude Code avant commit.** Le
travail embedder réalisé en session parallèle (cf. §6) court-circuite
cette règle et impose un re-check architectural complet avant
intégration. Leçon pour la suite du sprint.

---

## Contexte rapide ARIA

ARIA = kernel cognitif personnel local pour Nico. Single-user.
Bot Telegram + service systemd sur Debian (vDebianIA). VM sur
Proxmox `lemineur` (18 vCPU, 125 Go RAM). **Pas de GPU disponible
pour ARIA** — la GTX 1060 6 Go de l'hôte est en passthrough exclusif
sur la VM Windows 11 (gaming/Moonlight). Réévaluation possible en
septembre si seconde carte ajoutée.

Compte Claude Code : `dodgemyspoon@gmail.com` (Pro), session active
dans `~/Nextcloud/projects/aria` sur la Debian.

Anthropic API : pay-as-you-go, Haiku-4.5, ~0.0007$ par appel.
DeepSeek V4 Flash disponible via clé personnelle, $5 chargés —
intégration en pipeline ARIA réservée à un sprint ultérieur.

---

## Sprint 5 clos — bilan (rappel)

**Trois commits posés sur `feat/sprint2-image-pipeline`, tag
`sprint-5` local non pushé :**

- **b0aaee5 T2** : fix dette #20 (cache classifier). Cache cassé
  depuis sa création — bascule Option A : operation portée par
  room. 3 tests garde-fous + wipe de 199 entrées legacy + run
  live confirmé.
- **3b57136 T3** : fix dette #8 (cache négatif providers LLM).
  Cache RAM par provider, TTL 5 min. Détection 429 via
  `httpx.HTTPStatusError`. 4 tests garde-fous + 1 bonus + run
  live confirmé.
- **b1d78ab T11** : clôture audit intent matching (775 lignes
  finales) + kickoff sprint 6 v1. Découverte en cours de session :
  **dette #23 nouvelle** — pathologie de naming en branche SPLIT
  distincte de #22 (cf. ci-dessous).

**Audit intent matching (dette #18) — racine établie**

Triple cause :

1. Espace d'embedding plat (`all-MiniLM-L6-v2`). Aucune paire
   d'intents > 0.85 sur 1770 comparaisons, top à 0.668. Le seuil
   0.45 capture mécaniquement tout intent vaguement aligné avec
   le centroïde français.
2. Embedding calculé sur le `name` seul (pas de description, pas
   d'extraits d'actions_history).
3. Intents "absorbants" comme `Pourquoi elle ne germent pas`
   attirent massivement des messages sans rapport.

Bugs reproduits :
- "Les carottes en ragoût recette" → 0.642 sur `carottes dans jardin`.
- "Planifier des vacances en Normandie" → 0.466 sur `Pourquoi
  elle ne germent pas` (top 1).
- "Tu vas bien ?" → 0.496 sur `semis en intérieur`.
- Cas 5 (conversation cuisine multi-tour) : 3 intents différents
  matchés sur 4 tours, fil rouge perdu, intent SPLIT créé en T4
  avec naming illisible (`Dans ma cuisine j'ai : Une cocotte, une
  poêle, une planche à`).

**Dettes #22 et #23 (naming illisible) — distinctes**

| Dette | Branche | Mécanisme |
|---|---|---|
| #22 | CREATE | `extract_intent_name` LLM appelé mais (a) prompt mal respecté pour messages longs, (b) slicing `[:60]` brut au caractère |
| #23 | SPLIT | `extract_intent_name` **pas appelé du tout** → `name = message[:60]` direct ; `_find_by_name_semantic` (F4) **pas consulté** non plus |

Sur l'embedder plat actuel, la zone 0.40-0.45 est suffisamment
peuplée pour que SPLIT se déclenche régulièrement → multiplication
d'intents fantômes.

---

## Audit T-Z livré (lecture seule, pré-renommage de branche)

État git complet à fin sprint 5 :

| Branche | Locale | Remote | Note |
|---|---|---|---|
| `feat/sprint2-image-pipeline` | ✅ HEAD b1d78ab | ✅ | **+3 commits non pushés** (T2/T3/T11) |
| `main` | ✅ HEAD 19dae68 | ✅ | 7 commits, ancêtre strict de la feat branch |
| `cognitive-pipeline-refactor` | ❌ | ✅ | **branche par défaut côté origin** |
| `develop` | ❌ | ❌ | n'existe nulle part |

Tag `sprint-5` local uniquement, pas pushé sur origin. Tags
antérieurs (sprint-2, sprint-3, sprint-3.1, sprint-4,
aria-kernel-0.2) tous pushés. Pas de stash, pas de worktree
secondaire, reflog propre.

**Constat clé : `main` existe déjà mais est stagnante.** Elle
n'a rien que la feat branch n'ait pas (`git log feat/...../main`
= vide), et la feat branch est ~30 commits en avance. Le travail
réel a divergé sur `cognitive-pipeline-refactor` puis sur la feat
branch. `main` n'est ni orpheline ni placeholder — c'est un point
mort que personne n'a mis à jour depuis longtemps.

**Décision archi tranchée pour T-Z2 :** la cible est `main`. Pas
besoin de créer `develop`. `main` est ancêtre strict de la feat
branch — fast-forward propre possible. Sortie attendue :

```
1. Push sur origin de tous les commits sprint 5 (b0aaee5 / 3b57136
   / b1d78ab) sur l'ancien nom de branche, pour ne rien perdre.
2. Push du tag sprint-5 sur origin (git push origin sprint-5).
3. Fast-forward main locale jusqu'à HEAD de feat branch.
4. Push origin main forcé en fast-forward (--force-with-lease
   pour sécurité).
5. Bascule de la HEAD origin sur main (action manuelle Nico via
   GitHub Settings → Default branch).
6. Suppression remote de feat/sprint2-image-pipeline ET de
   cognitive-pipeline-refactor (deux branches mortes).
7. Suppression locale de feat/sprint2-image-pipeline.
8. Vérification : `git branch -a` ne montre que main local + remote.
```

Étape 5 reste manuelle Nico. Étapes 6-7 demandent validation
explicite avant exécution (suppressions remotes irréversibles
dans la pratique). Le brief T-Z2 sera rédigé en tour 1 du sprint
6 réel.

---

## ⚠️ Travaux hors-workflow réalisés en session parallèle

Pendant la session kickoff initiale, Nico a délégué à un autre LLM
deux pistes infrastructurelles. Synthèse et critique architecturale.

### 6.1 Tentative GPU — ABANDON

GPU NVIDIA GTX 1060 6 Go déjà en passthrough exclusif vers la VM
Windows 11 (gaming). PCIe passthrough est exclusif, pas de partage
possible. Audit Proxmox confirmé : `qm config 100` montre l'usage
exclusif, tentative d'attribution à VM 110 a échoué proprement.

**Décision actée :** ARIA reste CPU-only jusqu'en septembre minimum.
Le levier "GPU pour embedder en local" sort du périmètre sprint 6.

### 6.2 Changement d'embedder — RÉALISÉ HORS WORKFLOW (à re-arbitrer)

Travail effectué dans une session LLM parallèle, **pas dans le
workflow architecte → Claude Code**. État actuel :

**Ce qui a été fait :**
- Benchmark CPU de 5 modèles sentence-transformers
- Choix : `yilunzhang/all-mpnet-base-v2-onnx` (pré-converti ONNX)
- Réécriture complète de `aria/embedding/embedder.py` (gestion
  ONNX + fallback)
- Modification `config.py` : `EMBEDDING_MODEL` change de
  `all-MiniLM-L6-v2` (dim 384) à `yilunzhang/all-mpnet-base-v2-onnx`
  (dim 768)
- Trois scripts de test ajoutés dans `aria/scripts/`
- Mesures : 23-24 phrases/s en ONNX (vs ~10-15 en MiniLM)

**Statut commit :** non précisé dans le livrable. Probablement
modifications locales non commitées. À CONFIRMER en premier tour
sprint 6.

**Critiques architecturales — quatre points sensibles :**

(a) **Modèle anglais sur assistant français.** `all-mpnet-base-v2`
est un modèle entraîné majoritairement sur de l'anglais. ARIA
fonctionne en français. Le benchmark CPU mesure la **vitesse**,
pas la **qualité sémantique sur du français**. Le choix
optimal pour ARIA serait probablement
`paraphrase-multilingual-MiniLM-L12-v2` (14.5 ph/s, dim 384,
multilingue, drop-in remplacement sans changement de dimension)
ou `intfloat/multilingual-e5-small` (15.6 ph/s, dim 384,
multilingue), ou pour la qualité maximale `BAAI/bge-m3` (4
ph/s, dim 1024, multilingue, le plus moderne). Tous trois
testés dans le benchmark mais écartés au profit du modèle
anglais le plus rapide en ONNX. **Cette décision est à
re-arbitrer.**

(b) **Migration des embeddings existants — pas seulement ChromaDB
et MemPalace.** Le livrable mentionne "re-générer l'intégralité
des embeddings". Vrai mais incomplet — il faut aussi régénérer
les embeddings d'intents (`~/.aria/intents.json`, 61 intents),
le cache classifier (à wiper), et toute autre collection
vectorielle. Audit complet de l'inventaire vectoriel obligatoire
avant migration.

(c) **Changement de dimension 384 → 768 = breaking change majeur.**
Si modèle multilingue conservé en dim 384, la migration est
beaucoup plus simple (les structures de stockage acceptent dim
identique, seul le contenu vectoriel change). Argument
supplémentaire pour reconsidérer le choix.

(d) **Méthode de validation absente.** Aucune mesure de qualité
sémantique sur du français — uniquement de la vitesse. Le bug
#18 a précisément pour cause un espace d'embedding plat sur
français ; on ne saura pas si on l'a résolu sans mesurer
ex-post sur les 4 cas terrain + cas 5 multi-tour.

**Recommandation architecte :**

```
Tour 1 sprint 6 (avant le renommage de branche T-Z2) — AUDIT du
travail embedder hors-workflow :
- État commit (modifs locales ? branche dédiée ? rien commité ?)
- Inventaire complet des collections vectorielles à migrer
- Re-benchmark sur du français : top-5 cosines pour les 4 cas
  terrain + cas 5, comparé entre MiniLM (actuel),
  paraphrase-multilingual-MiniLM-L12-v2 (drop-in dim 384),
  multilingual-e5-small (dim 384), all-mpnet-base-v2 (anglais,
  dim 768) et bge-m3 (dim 1024).
- Décision finale du modèle d'embedder, sur base sémantique,
  pas vitesse.
- Plan de migration des embeddings existants.
```

C'est le levier 1 (changer d'embedder) du fix #18 — qui était
justement prévu pour ce sprint. Le travail parallèle a court-circuité
l'analyse mais n'a pas annulé le besoin d'arbitrer correctement.
En positif : le bench CPU est utile, le code ONNX réutilisable,
la voie technique défrichée.

### 6.3 Audit taxonomie V2 — disponible pour archive

Trois versions disponibles dans `/docs/sprint6/audit_taxonomy.md` :
V1 ChatGPT (initial), V2 DeepSeek (modèle de raisonnement),
V2 Gemini (modèle de raisonnement). D'après Nico, les deux V2 sont
sensiblement similaires.

Décision : **archive au backlog sprint 7+, pas d'implémentation
en sprint 6.** La taxonomie attaque la couche de routing AVANT le
matching d'intent. Tant que la couche matching n'est pas stabilisée,
ajouter une couche au-dessus est prématuré. Le sprint 6 a déjà
9-12 tours pour fixer #18+#22+#23 — pas de bande passante pour
absorber la taxonomie en plus.

À transposer en kickoff sprint 7 ou 8 selon avancement.

---

## Dettes hiérarchisées pour sprint 6

### Priorité 1 — Bloquant pour usage quotidien

**Dette #18 — Intent matching erratique.** Couvert par les leviers
1+4+3 décidés en kickoff (cf. §8). Le levier 1 a été partiellement
préparé en travail parallèle mais doit être re-arbitré (cf. §6.2).

### Priorité 2 — Bloquant pour lisibilité

**Dette #22 — `extract_intent_name` truncation au caractère** (branche
CREATE). Renforcer le prompt namer + tronquer au dernier espace
avant 60 chars.

**Dette #23 — Naming en branche SPLIT** (NOUVELLE, sprint 5). Soit
appeler `extract_intent_name` aussi pour SPLIT, soit retirer SPLIT
et défaulter à CREATE. Décision couplée au choix d'embedder (sur
embedder dense, SPLIT pourrait redevenir utile).

#22 et #23 traitées ensemble dans le sprint, en amont de #18 pour
que les logs T-D soient lisibles.

### Priorité 3 — Vocabulaire ARIA (architectural)

**Taxonomie message** — V1 ChatGPT + V2 DeepSeek + V2 Gemini
disponibles dans `/docs/sprint6/audit_taxonomy.md`. Trop gros pour
sprint 6 (cf. §6.3). À transposer en sprint 7+.

### Priorité 4 — Dettes techniques structurelles (rappel sprint 5)

- **Dette #2** — Cosine recalculé O(N) dans
  `_find_by_name_semantic` (négligeable à 60 intents).
- **Dette #3** — Deux mécanismes de matching d'intent en parallèle.
  Audit sprint 5 : ils sont séquentiels, pas concurrents. À nettoyer
  si le fix #18 ne les unifie pas.
- **Dette #4** — Marge fragile sur scoring nu (test_intent_dedup,
  0.4889 vs seuil 0.45). Sera réévalué après changement d'embedder.
- **Dette #5** — Suivi des opérations sur la donnée. Logger les
  IDs supprimés.
- **Dette #10** — Audit IMAGE_INPUT.
- **Dette #14** — Tension architecturale `MemoryStack` (4 couches
  L0/L1/L2/L3) vs architecture ARIA actuelle.
- **Dette #15** — Tests `memory/writer.py` incomplets.
- **Dette #16** — Tests `test_llm_execution_router.py` ne couvrent
  pas l'écriture mémoire post-T4 sprint 4.
- **Dette #17** — Bloc-note explicite (`store_semantic_fact`
  triggéré par marqueurs explicites). Couvre le cas "code Jonas
  9041" (cf. taxonomie mémoriel pur).
- **Dette #19** — Restructuration doc.
- **Dette #21** — Aria invente sur sujets pointus. Mitigation
  attendue : DeepSeek V4 Flash en validation croisée ou web search.
- **Dette : 32 entrées résiduelles `mempalace_closets wing=aria`**.
  Non migrées sprint 4.
- **Dette : `IntentCompressionEngine` inactif.** Seuil 0.78 jamais
  atteint sur l'espace plat actuel. Devient pertinent SI nouvel
  embedder dense.
- **Dette : aucun log des scores d'intent en prod.** Indispensable
  pour T-D sprint 6.
- **Dette : doublon `RecallDecision` vs `IntentRecallDecision`.**
  Dead code candidat.

### Priorité 5 — Features post-stabilisation

- Intégration DeepSeek V4 Flash dans `llm/llm_router.py`.
- Knowledge graph (vision long-terme).
- Mining contraint, agent diaries, métacognition (`aria_self`).

---

## Décisions arbitrées en kickoff sprint 6

### 1. Nom de la branche cible : `main`

`main` existe déjà côté origin (HEAD 19dae68), ancêtre strict de
la feat branch. Pas besoin de créer `develop`. Fast-forward propre
possible. Suppression remote de `feat/sprint2-image-pipeline` ET
de `cognitive-pipeline-refactor` (deux branches mortes après
bascule). Bascule de HEAD origin sur main par Nico via GitHub.

### 2. Ordre des dettes : #22 + #23 (couplées) avant #18

Naming illisible perturbe la lecture des logs T-D. #22 et #23
partagent le même périmètre logique (canonisation du naming d'intent
quel que soit le chemin), traitement conjoint plus efficace.

### 3. Combinaison de leviers pour #18 : 1 + 4 + 3

| Levier | Statut |
|---|---|
| 1. Changer d'embedder | OBLIGATOIRE — racine de la pathologie. À re-arbitrer en T-Embedder car le choix parallèle (mpnet anglais) est suboptimal pour un assistant français. |
| 4. Embedder sur name + description | OBLIGATOIRE — quasi gratuit, densifie le signal. |
| 3. Continuité conversationnelle | OBLIGATOIRE — seul levier qui adresse le cas 5. |
| 2. Seuil ATTACH | À ajuster ex-post une fois 1+4 en place. |
| 5. Re-rank LLM sur top-3 | Reporté. |

Décision finale combinée à valider en T-E avec données prod.

### 4. Taxonomie message : archive, pas d'implémentation sprint 6

V1 + 2×V2 dans `/docs/sprint6/audit_taxonomy.md`. Implémentation
reportée à sprint 7 ou 8.

---

## Plan de tours révisé sprint 6

```
T-Z1   Audit git pré-renommage              ✅ LIVRÉ
T-Z2   Renommage branche feat → main         (1 tour)
       + push commits sprint 5 + tag sprint-5
       + suppression branches mortes (avec validation Nico)

T-Embedder1  Audit embedder hors-workflow    (1 tour, lecture seule)
             - état commit/branche
             - inventaire collections vectorielles
             - benchmark qualité multilingue sur 4 cas terrain
             + cas 5
T-Embedder2  Décision modèle final + plan migration (1 tour, pas
             de code)
T-Embedder3  Implémentation embedder + script migration (1-2 tours)
T-Embedder4  Run live + validation reproductibilité bugs #18 (1 tour)

T-Naming1    Audit + décision SPLIT garder/supprimer (1 tour, lecture
             seule, couplé au nouveau embedder dense)
T-Naming2    Fix #22 + #23 selon décision T-Naming1 (1-2 tours)

T-Match1     Instrumentation logs scores prod (1 tour)
↓ Run live Nico 2-3 jours collecte données ↓
T-Match2     Analyse données + ajustement seuil + levier 4 (1 tour)
T-Match3     Implémentation levier 3 (continuité conv.) (1-2 tours)
T-Match4     Validation run live finale (4 cas + cas 5) (1 tour)

T-Clôture    Clôture sprint + kickoff sprint 7 (1 tour)
─────────────────────────────────────────────────────────
Total : 11-15 tours
```

**Surveillance fenêtre :** dépasser 60% de remplissage avant
T-Match4 implique clôture intermédiaire avec kickoff sprint 7
portant le résiduel. Découpage possible en deux sprints :
sprint 6 = embedder + naming + instrumentation, sprint 7 =
matching + continuité + validation. À acter à mi-chemin selon
remplissage.

---

## Décisions à acter dès le tour 1 sprint 6

1. **Statut du travail embedder hors-workflow.** Modifs commitées ?
   sur quelle branche ? rien commité ? À confirmer avant de planifier
   T-Embedder1.

2. **Push pré-renommage.** Pusher les commits sprint 5
   (b0aaee5/3b57136/b1d78ab) + tag `sprint-5` AVANT toute opération
   de renommage de branche. Sécurité minimale.

3. **Action manuelle Nico GitHub.** Bascule HEAD origin sur main +
   suppression branches mortes via interface web — ne peut pas être
   automatisée par Claude Code, à séquencer dans le brief T-Z2.

---

## Contraintes techniques connues

ARIA tourne sur une VM Debian (vDebianIA) en single-user, sur
Proxmox `lemineur`. 18 vCPU, 125 Go RAM, **pas de GPU**. Telegram
bot + service systemd. Mémoire vectorielle via MemPalace v3.3.x
(externe, github.com/MemPalace/mempalace). Pour mise à jour :
`pip install --upgrade "mempalace @ git+https://github.com/MemPalace/mempalace.git@develop"`.

Branche de travail : `feat/sprint2-image-pipeline` jusqu'au tour
T-Z2, puis `main`. Pas de push origin avant validation explicite
Nico.

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
- Diagnostic cache classifier : `scripts/archive/diagnose_classifier_cache_similarity.py`
- Audit taxonomie : `/docs/sprint6/audit_taxonomy.md`
- Audit intent matching : `/docs/sprint5/audit_intent_matching.md`
- Scripts embedder hors-workflow : `aria/scripts/bench_cpu.py`,
  `test_onnx.py`, `test_onnx_embedder.py`

---

## Premier message à envoyer dans la nouvelle session

> Reprise sprint 6 (v2). Voici le context [PIÈCE JOINTE].
>
> Sprint 5 clos, audit T-Z livré, mais évolution majeure depuis
> le kickoff initial : du travail embedder a été réalisé hors
> workflow architecte → Claude Code (cf. §6.2). Modèle changé en
> `all-mpnet-base-v2-onnx` (dim 768, anglais), à re-arbitrer car
> ARIA est en français. Audit GPU livré aussi : pas de GPU
> disponible, ARIA reste CPU-only jusqu'en septembre.
>
> Branche `main` existe déjà côté origin et est ancêtre strict de
> la feat branch — décision actée, on bascule sur `main`. Tag
> sprint-5 et 3 commits sprint 5 non pushés, à pusher avant
> renommage.
>
> Premier objectif sprint 6 réel : T-Z2 (renommage branche +
> push tags/commits + suppression branches mortes).
>
> Deuxième objectif : T-Embedder1 (audit du travail hors-workflow,
> lecture seule, benchmark qualité sur français).
>
> Aide-moi à rédiger le brief T-Z2 puis T-Embedder1 dans cet
> ordre. Pas de code dans le tour T-Z2 d'abord — c'est mécanique
> mais irréversible, on sécurise.