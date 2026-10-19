# Sprint 26 — Tronçon 05 : correctif post-run live 04

Lire d'abord : `CLAUDE.md`, `docs/sprint26/00_etat.md`, `docs/sprint26/audit_correctif_05.md`.
Palace prod : pas de nouveau type, pas de nouvelle fonction d'écriture. Calibrage faible.

## Objectif

1. **Bug 1** : l'échange d'une analyse de partie (message enrichi + réponse) doit être
   écrit en `aria_episodic` sous l'intent `jeux echecs`, de façon déterministe, sans
   passer par le namer (qui répond « aucun » aujourd'hui).
2. **Ancre (Q11 b)** : chaque analyse s'ouvre par « Partie contre <adversaire> <date>
   <ouverture> », dans le bloc enrichi ET en tête de la réponse du LLM, pour qu'une
   question de suivi (« la position 1 de cette partie ») retrouve la bonne partie.

## Comportement attendu

### Bug 1 — nom d'intent imposé (Q9 a, Q10)

- `execution/routers/chess_router.py` : l'appel délégué à `LLMExecutionRouter` (cas
  PGN lisible) ajoute à `metadata` une clé `forced_intent_name` valant `"jeux echecs"`
  (constante du module). Le `metadata` reçu n'est pas muté en place (copie).
  Le cas PGN illisible ne change pas.
- `execution/routers/llm_router.py`, `_run_pipeline`, étapes 2-3 : nouvelle branche
  entre `skip_intent` et le chemin normal. Si `metadata.get("forced_intent_name")` :
  - `resolve` n'est **pas** appelé (pour ne pas rattacher la partie à un autre projet) ;
  - le namer n'est **pas** appelé ;
  - `intent = self.intent_engine.apply(decision=RecallDecision(action="create"),
    message=message, intent_name=<nom imposé>)`. `apply` en CREATE retrouve l'intent
    actif du même nom (`_find_by_name`), sinon sémantique, sinon le crée — vérifié au
    code (`intent/intent_engine.py`, `apply`). `RecallDecision` est dans
    `intent/intent_recall_engine.py` (`action` seul suffit, autres champs par défaut).
    Vérifier que `recall_decision` passé ensuite dans `AgentContext.extra["recall"]`
    reste cohérent (mettre la décision construite).
  - log : `intent FORCED name=<nom>`.
  - La suite (étapes 4-10) est inchangée : avec un intent, `write_interaction` écrit
    (log existant `memory_write OK … intent_name=jeux echecs`).
- Commentaire français en tête de la branche : pourquoi (bug 1, audit 05).

### Ancre « Partie contre … »

- Dans `chess_router.py`, construire l'ancre à partir de `summarize(analysis)` (champs
  `opponent`, `date`, `opening` — déjà calculés au tronçon 03). `summarize` est pur :
  le sortir du `try` de l'écriture de fiche pour le réutiliser (l'écriture reste dans le
  `try/except` non bloquant existant).
  - Format : `Partie contre <adversaire> <date> <ouverture>`.
  - Adversaire absent → `adversaire inconnu` (même libellé que `summary_text`).
  - Date ou ouverture absente → omise (pas de « inconnue »).
  - Ouverture : tirets remplacés par des espaces pour l'affichage
    (`Scandinavian-Defense-Mieses-Kotrc-Variation-3.Nc3` → `Scandinavian Defense …`).
    La fiche (`opening` en métadonnée) ne change pas.
- L'ancre est la **première ligne** du message enrichi (avant `[Analyse Stockfish …`).
- La consigne existante demande en plus : « Commence ta réponse par la ligne exacte
  « <ancre> ». »

## Tests (cas nominal)

- `tests/execution/test_llm_execution_router.py` : avec
  `metadata={"forced_intent_name": "jeux echecs"}` → `resolve` et `extract_intent_name`
  non appelés, `apply` appelé avec `action == "create"` et `intent_name="jeux echecs"`,
  `write_interaction` appelé. S'inspirer de `test_skip_intent_bypasses_resolve_and_apply`.
- `tests/execution/test_chess_router.py` : la métadonnée déléguée contient
  `forced_intent_name == "jeux echecs"` ; le contenu délégué commence par
  `Partie contre <adversaire>` et la consigne mentionne l'ancre. Adapter l'assertion
  existante `"skip_intent" not in delegated["metadata"]` si besoin (elle reste vraie).

## Hors scope (NE PAS faire)

- Pas de retouche de `NAMER_PROMPT` ni du prompt AnalystAgent.
- Pas de déplacement des fiches (`room chess`) — arbitrage sprint 27.
- Pas de touche à l'historique conversationnel ni au 413 Groq (#86), au récit
  halluciné (#84), à la stabilité du meilleur coup (#85).

## Critère de fin

`./venv/bin/pytest tests/ -q` vert (baseline 293). `00_etat.md` : tronçon 05 ✅ + §REPRISE.
