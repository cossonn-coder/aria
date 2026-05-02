# ARIA — Reprise sprint 4 architectural
**Mis à jour : 2 mai 2026**
**État : sprint 3.1 clos — 190 tests verts, tag `sprint-3.1` posé**

---

## Workflow de cette session (à mémoriser)

Nico travaille avec **deux instances de Claude en parallèle** :

1. **Architecte (cette session, claude.ai)** — analyse, critique, plan,
   prépare les messages destinés à Claude Code, valide les livrables.
   Toujours en français. Esprit critique sur les propositions.

2. **Implémenteur (Claude Code dans la VM Debian)** — exécute, code,
   teste, commit. Il livre du concret : diffs, tests, audits.

**Cycle d'un tour :**
1. Nico colle ici un contexte (ce document + résultat du dernier livrable Claude Code)
2. L'architecte analyse, critique, et **rédige un message destiné à Claude Code**
3. Nico copie ce message dans Claude Code, qui exécute
4. Claude Code retourne un livrable (diff, tests, audit, log)
5. Nico recolle le livrable ici → retour étape 2

Les fichiers dont l'architecte a besoin pour réfléchir, Nico les fournit
manuellement (copie/collage). Les actions sur le code, Nico les délègue
à Claude Code via le message rédigé. **L'architecte ne touche jamais
directement au code.**

Le sprint se termine quand l'architecte considère qu'il n'y a plus de
décisions à prendre — restitution finale au format identique à celui-ci
(reprise de session) pour la session suivante.

---

## Contexte rapide ARIA

ARIA = kernel cognitif personnel local pour Nico. Single-user.
Bot Telegram + service systemd sur Debian (vDebianIA).

Compte Claude Code : `dodgemyspoon@gmail.com` (Pro), session active dans
`~/Nextcloud/projects/aria` sur la Debian.

Anthropic API : pay-as-you-go, Haiku-4.5, ~0.0007$ par appel.
Plan Pro = Claude Code + claude.ai (séparé de l'API).

---

## Sprint 3.1 clos

Sprint de solidification + diagnostic architectural. Livraisons :

- **Dette #9 fermée** : test garde-fou sur le prompt AnalystAgent
  (`assert "domaine actuel" not in PROMPT`). Empêche la régression
  silencieuse qui avait frappé lors du commit 31c21a4.
- **Dette #6 fermée** : instrumentation memory_write step 10 dans
  `LLMExecutionRouter` (branches OK/SKIPPED/ERROR loggées).
- **Fix F1 livré** : retrait du boost `mem_score` dans
  `IntentRecallEngine.resolve()`. Scoring purement cosine.
  Validé en run live : "Tu te rappelles des choux rouges ?" ne
  mappe plus sur "construire une maison".
- **Diagnostic mémoire** : `scripts/count_memory_by_wing.py` créé.
  Révèle que les écritures vont dans wing `aria` (hardcodé dans
  `llm_router.py` step 10) alors que le retrieval lit `aria_episodic`.
  `aria_episodic` stagne à 143 malgré `memory_write OK` en logs.

190 tests verts. Branche `feat/sprint2-image-pipeline`, tag `sprint-3.1`.

---

## Décision architecturale prise en fin de sprint 3.1

**ARIA devient client de MemPalace via son API publique.**

Architecture 2 retenue sur les 3 envisagées : ARIA-le-système-cognitif-
partageable, avec un palace MemPalace par utilisateur. Cette vision
permet à terme le partage du framework ARIA entre utilisateurs, chaque
instance disposant de son propre palace isolé.

Conséquence directe : le bug `wing='aria'` en dur dans `llm_router.py`
n'est **pas corrigé à l'endroit** — il est absorbé dans la refonte de
la couche mémoire. Nouveau code à côté de l'ancien (strangler pattern),
bascule progressive.

---

## Périmètre sprint 4 — à valider en kickoff

### Objectifs proposés
- **Migration retrieval/storage** de l'accès cargo cult ChromaDB vers
  l'API publique MemPalace (`mempalace.searcher`, `mempalace.writer`,
  etc.). Identifier les APIs disponibles avant de coder.
- **Strangler pattern** : nouveau code à côté de l'ancien, pas de
  réécriture en une passe. Bascule progressive et testable.
- **Corriger wing='aria'** dans le cadre de la migration : les
  écritures doivent pointer vers `aria_episodic`, les lectures
  aussi. Vérifier avec `count_memory_by_wing.py` après chaque étape.

### Non-objectifs proposés (à confirmer en kickoff)
- Knowledge graph → sprint 5
- Mining contraint → sprint 5+
- Agent diaries → sprint 5+
- Métacognition (wing `aria_self`) → sprint 5+

---

## Dettes ouvertes

1. ~~mem_score biaisé par doublons~~ ✅ RÉSOLU sprint 2
2. **Cosine recalculé O(N)** (`intent/intent_engine.py:_find_by_name_semantic`)
   Négligeable à 50 intents, à indexer si croissance.
3. **Deux mécanismes de matching d'intent en parallèle**
   (`intent_recall_engine.resolve` + `intent_engine._find_by_name_semantic`)
   À unifier.
4. **Marge fragile sur scoring nu**
   (`tests/intent/test_intent_dedup.py:test_regression_bug_e_real_embeddings`)
   Score 0.4889 vs seuil 0.45.
5. **Suivi des opérations sur la donnée** (dette de processus)
   Logger chaque ID supprimé dans un fichier audit, mesurer before/after
   par wing+room avec filtre explicite. Script `count_memory_by_wing.py`
   créé pour faciliter ce suivi (sprint 3.1).
6. ~~Écriture mémoire silencieusement skippée~~ ✅ RÉSOLU sprint 3.1
   (instrumentation memory_write step 10)
7. **Pollution contextuelle [Projets actifs] complète**
   Indirectement atténuée par Fix #1 sprint 3.0, mais structure non corrigée.
   À traiter via top-K cosine — dépriorisé par rapport à la refonte mémoire.
8. **Cache négatif des providers LLM en quota**
   Cerebras/OpenRouter free tier reçoivent régulièrement des 429.
   Chaîne fallback fonctionne mais ~2s perdues par message.
   Fix : cacher 429 pendant N minutes pour skipper provider en quota.
9. ~~Test garde-fou prompt AnalystAgent~~ ✅ RÉSOLU sprint 3.1
10. **Audit IMAGE_INPUT**
    Le router n'appelle la pipeline cognitive complète que si la caption
    est interrogative. Profil pathologique potentiel.
11. **Bug wing='aria' hardcodé** *(nouveau, détecté sprint 3.1)*
    `execution/routers/llm_router.py` step 10 écrit dans wing `aria`.
    Le retrieval lit `aria_episodic`. Les interactions récentes ne sont
    jamais retrouvées. Absorbé dans la refonte couche mémoire sprint 4.

---

## Ressources clés

- `.env` : `/home/nico/Nextcloud/projects/aria/.env` (Debian)
- MemPalace : `/home/nico/.mempalace/palace`
- Intents : `~/.aria/intents.json`
- Service : `sudo systemctl restart aria.service`
- Logs : `sudo journalctl -u aria -f -o cat`
- Diagnostic mémoire : `./venv/bin/python scripts/count_memory_by_wing.py`

---

## Premier message à envoyer dans la nouvelle session

> Reprise sprint 4 architectural. Voici le context [PIÈCE JOINTE].
>
> Décision prise en fin de sprint 3.1 : ARIA devient client MemPalace
> via API publique. Cette session est un KICKOFF — on fait l'audit
> complet et le plan AVANT de toucher au code.
>
> Aide-moi à structurer le sprint 4 :
> 1. Audit de l'utilisation actuelle de MemPalace dans ARIA
> 2. Inventaire des APIs MemPalace publiques disponibles
> 3. Plan de strangler pattern
> 4. Critères de succès et non-objectifs
>
> Pas de code dans cette session de kickoff sauf si nécessaire pour
> l'audit (lire les fichiers, pas les modifier).
