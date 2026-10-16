# Sprint 22 — Audit : accès au monde extérieur

Date : 2026-10-16. Base : `main` @ `ea845e2` (tag `sprint-21`).

## 1. Constat : ARIA n'a aucun accès au monde extérieur

Grep exhaustif (`tavily|brave|duckduckgo|ddg|serper|searx|web_search|trafilatura|bs4`)
hors `venv/` : **aucune occurrence dans le code**. Seule trace : la taxonomie
du sprint 6 (`docs/sprint6/audit_taxonomy.md:392,598`) qui listait déjà
`WEB_SEARCH` comme comportement souhaité (« RESPOND + WEB_SEARCH si
nécessaire »), jamais implémenté.

Les seuls appels HTTP sortants sont les providers LLM (`llm/llm_router.py`,
`httpx.post`), la vision et la génération d'images. Dépendances disponibles
dans le venv : `httpx 0.28.1`, `requests 2.32.5`. Aucune lib de recherche ni
d'extraction HTML.

Clés présentes dans `.env` (noms seuls) : GROQ, TELEGRAM, FAL, GEMINI,
CEREBRAS, SAMBANOVA, OPENROUTER, MISTRAL, HF, ANTHROPIC, DEEPSEEK. Aucune clé
de moteur de recherche.

## 2. Chaîne actuelle (où s'insère un effecteur web)

```
TelegramInterface (TEXT & ~COMMAND, PHOTO)
  → AriaKernel.handle_event
      1. CognitiveEngine.classify → classify_operation (texte)
           heuristique image_gen → court (≤10 car.) → CONFIRMATION
           → cache aria_classifier (sim ≥ 0.92) → LLM CLASSIFIER_PROMPT → UNKNOWN
      2. ExecutionOperation(type=op.value, payload{op_type, content, metadata})
      3. ExecutionDispatcher.dispatch → _ROUTING_TABLE[op] → router.execute(payload)
      4. _normalize → str | {"type":"image",…}
```

- `core/kernel.py:46-57` : `_ROUTING_TABLE` ; commentaire : « Ajouter une
  capacité = ajouter 1 ligne + 1 router. Le kernel ne change pas. »
- `core/kernel.py:60-91` : `_build_dispatcher` construit `LLMExecutionRouter`
  en premier et l'injecte dans `ImageExecutionRouter`.
- `cognition/cognitive_context.py` : enum `CognitiveOperation` + `MEMORY_TOP_K`
  + `LLM_ROLE_MAP`.
- `cognition/cognitive_classifier.py:156-174` : `CLASSIFIER_PROMPT` (8
  catégories), `_parse_operation` → UNKNOWN si valeur inconnue.
- `interfaces/telegram_interface.py:55` : `filters.TEXT & ~filters.COMMAND` →
  **les commandes `/xxx` sont ignorées aujourd'hui** (un `/web …` explicite
  demanderait un `CommandHandler` en plus).

## 3. Précédent directement réutilisable : le mode vision enrichi

`execution/routers/image_router.py:159-218` (`_handle_input_enriched`) :

1. l'effecteur obtient un texte externe (description vision) ;
2. il construit un message enrichi `[Analyse visuelle : …]` + consignes +
   question originale ;
3. il délègue à `self.llm_execution_router.execute({"op_type": REASONING,
   "content": enriched, "metadata": {…, "skip_intent": True}})`.

Effets côté `LLMExecutionRouter._run_pipeline`
(`execution/routers/llm_router.py`) avec `skip_intent=True` :
- mémoire globale + historique conversationnel chargés (étapes 1, 1b) ;
- ni résolution ni création d'intent (#51) ;
- `write_interaction` **sauté** (`intent is None`) → rien dans `aria_episodic` ;
- `write_conversation_turn(user=message enrichi, assistant=réponse)` → le
  bloc externe est stocké dans `aria_conversation` et réinjecté sur les
  `max_history_turns` tours suivants.

Un `WebExecutionRouter` calqué sur ce schéma respecte d'office les règles
inviolables :
- R1 écriture : aucune écriture propre, tout passe par `LLMExecutionRouter` →
  `memory/writer.py` ;
- R2 lecture : pas de lecture mémoire dans le router web ;
- R3 agents : la recherche est faite par le router (effecteur), l'agent reçoit
  le résultat dans son `ctx.message` pré-assemblé — il ne fait aucune requête ;
- R4 : retour `{"text": str}` (celui de `LLMExecutionRouter`) ;
- R5 kernel : 1 ligne de routing + 1 enregistrement dans `_build_dispatcher`.

## 4. Points d'attention

1. **Déclenchement.** Le classifier LLM a tendance à ranger beaucoup de choses
   en `reasoning`/`unknown`. Une catégorie `web_search` définie largement
   (« question de culture générale ») déclencherait la recherche à tort ; définie
   étroitement (actualité, prix, météo, horaires, « cherche sur internet »)
   elle reste rare. Le cache `aria_classifier` mémorisera les verdicts
   `web_search` à confiance ≥ 0.65 comme les autres.
2. **Volume dans `aria_conversation`.** Le message enrichi (résultats web)
   est stocké tel quel et rechargé sur 10 tours [valeur config
   `max_history_turns`]. Même comportement que la vision ; à borner par la
   taille des extraits injectés.
3. **Fragilité fournisseur.** Leçon #44 : les services gratuits sans clé
   (Pollinations, HF) sont morts. Un scraping sans clé (DuckDuckGo) est le
   plus exposé à ce risque.
4. **Échec de la recherche.** Sans traitement, l'exception remonte au
   dispatcher → « Une erreur s'est produite, réessaie. » (`kernel._normalize`).
5. **Synchrone.** Tout le pipeline est synchrone (`httpx.post`, timeout 30 s
   côté LLM). Une recherche ajoute sa latence avant l'appel LLM.

## 5. Dettes adjacentes repérées (hors scope)

- `core/kernel.py:205` : `print(f"[KERNEL] execution error: …")` en prod
  (viole « jamais `print()` »).
- `cognition/cognitive_dispatcher.py`, `execution/execution_plan_builder.py`,
  `cognition/dispatcher_types.py` : code sans caller apparent (non vérifié en
  détail, à confirmer).

## 6. Idées « monde extérieur » trouvées dans le backlog (grep `docs/`)

| Idée | Source | Remarque |
|------|--------|----------|
| Recherche web pour les questions techniques (anti-hallucination) | `docs/sprint5/context_sprint_5_kickoff.md:212-221` (ex-« dette #21 » : « Aria invente sur sujets pointus », incident binning Bayer) | Le n° 21 a ensuite été réattribué (closets, sprint 10-11) : l'idée d'origine a **disparu du tableau** sans être fermée. |
| Demande informative → WEB_SEARCH / RAG (« infos Vercors randonnées ») | `docs/sprint6/context_sprint_6_kickoff.md:225`, `docs/sprint6/audit_taxonomy.md:598,798,878` | Persistance « transitoire, cache de session » : rejoint `skip_intent`. |
| Rappels différés (« rappelle-moi demain de tailler les rosiers ») | `docs/sprint6/audit_taxonomy.md:46-48,618,829` | Exige un envoi **proactif** (scheduler + push Telegram) : rien de tel aujourd'hui. |
| Calendrier | `docs/sprint6/audit_taxonomy.md:797` | Lié aux rappels. |
| SYSTEM_EXEC (commande à effet système immédiat) | `docs/sprint6/audit_taxonomy.md:392,529,603` | Sens « commande ARIA », pas forcément shell. |
| Article / lien collé sans instruction | `docs/sprint6/audit_taxonomy.md:665` | Base de la lecture d'URL. |
| Météo | messages réels de Nico cités `docs/sprint6/audit_embedder_benchmark.md:172` (« météo locale saison », « météo des prochains jours ») | Demande déjà formulée en usage réel. |
| Validation croisée par un 2ᵉ LLM | `docs/sprint5/context_sprint_5_kickoff.md:221` | Pas « monde extérieur » ; noté pour mémoire. |

Hors « monde extérieur » dans la même taxonomie : UPDATE_PREF, ROLLBACK,
STORE_FACT (#17).

## 7. Déclencheurs demandés par Nico — conséquences au code

Phrases : « cherche en ligne », « cherche sur le web », « donne-moi les
sources de cette information », « source ? ».

1. Les deux dernières sont des **relances** : la requête à chercher n'est
   pas dans le message mais dans le tour précédent (réponse d'ARIA). Le
   router web doit donc lire l'historique (via `MempalaceBridge.load_conversation_history`,
   règle 2 respectée) et formuler une requête (appel LLM court).
2. « source ? » fait 8 caractères ≤ `MIN_MESSAGE_LENGTH` (10) → aujourd'hui
   classé CONFIRMATION à l'étape 3 de `classify_operation`. L'heuristique web
   doit passer **avant** l'étape 3, au même rang que l'heuristique image (étape 2).
3. « source » seul est ambigu (« source d'eau », « la source de la Seine ») :
   matcher « source ? / sources ? » en message quasi entier et « donne-moi les
   sources », pas le mot nu.

## 8. Fournisseurs gratuits (vérifié web 2026-10-16)

- **Tavily** : 1000 crédits/mois [doc officielle], sans carte bancaire,
  remis à zéro le 1er du mois. Compte + clé nécessaires.
- **DuckDuckGo (`ddgs`)** : sans clé, scraping ; pas de quota documenté,
  blocages « 202 Ratelimit » / résultats vides signalés par des sources tierces.
  Lib non installée dans le venv.
- **Brave** : palier gratuit supprimé en février 2026 [sources tierces
  concordantes], 5 $/mois de crédit avec carte bancaire → exclu (« gratuit »).
