# Tronçon 01 — saut préventif de Groq + seuil ⏳ à 20 s (#73 / #86, #111)

Lire d'abord : `CLAUDE.md`, `docs/sprint31/00_etat.md`, `docs/sprint31/audit_messages_courts.md`.

## Constat (résumé de l'audit)

Après une analyse de partie, l'historique contient des tours `user` de 5 000 à 9 600 car.
(bloc enrichi Stockfish). L'AnalystAgent (tout l'historique) et le namer d'intent (tour
`user` précédent) envoient ce poids à Groq en rôle CHAT → 413 (ITPM 7000) → aller-retour
perdu + `time.sleep(1)` avant DeepSeek, une ou deux fois par message ordinaire. Avec le
chargement du modèle au 1er message, un `salut` a pris 17 s et a déclenché le ⏳.

## Objectif

### A. `llm/llm_router.py` — saut préventif

Dans `LLMRouter.complete()` :
- constante de module `GROQ_MAX_PAYLOAD_CHARS = 12_000` (pas de config, pas de paramètre) ;
- taille du payload = `len(prompt)` en mode prompt, somme des `len(m["content"])` en mode
  messages ;
- au-delà du seuil, les entrées `provider.startswith("groq")` sont sautées **sans appel HTTP
  ni sommeil**, avec une ligne
  `log.info("[LLM] provider %s skipped (payload %d chars > %d)", provider, size, GROQ_MAX_PAYLOAD_CHARS)` ;
- le mécanisme 413 du sprint 25 (`groq_too_large`) reste en place (filet si le seuil sous-estime).

Attention au `time.sleep(1)` : il est en fin de `except`, donc un `continue` avant le `try`
n'en déclenche pas. Vérifier qu'un saut n'ajoute aucun sommeil.

### B. `interfaces/telegram_interface.py`

`WAIT_NOTICE_SECONDS = 10` → `20`. Texte du message inchangé.

## Tests

Dans `tests/llm/test_groq_413.py` (même style que `test_groq_413_skips_other_groq`, `fake_call`
monkeypatché) :
- payload > 12 000 car. en rôle CHAT → aucun `groq*` dans les appels, réponse de `deepseek` ;
- payload court → `groq` appelé en premier (cas nominal inchangé).

Les tests du ⏳ (`tests/interfaces/test_telegram_interface.py`) monkeypatchent déjà la
constante : rien à ajouter.

## Interdit

- Pas de budget ni de troncature de l'historique (piste B écartée par Nico au sprint 25).
- Ne pas changer ce qui est écrit en `aria_conversation` (piste C écartée).
- Ne pas toucher à la table de routage, ni au prompt AnalystAgent, ni à #74.

## Critère de fin

`./venv/bin/pytest tests/ -q` vert (baseline 351).
