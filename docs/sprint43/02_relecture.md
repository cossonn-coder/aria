# Sprint 43 — tronçon 02 : relecture d'un document en mémoire

Lire d'abord : `CLAUDE.md`, `docs/sprint43/00_etat.md`, `docs/sprint43/01_fiche_document.md`
(format de fiche et `REREAD_PROPOSAL`, livrés au tronçon 01).

## Objectif

Relire un document déjà lu **depuis le palace** (texte intégral en `aria_documents`,
sans fichier, sans Tavily, sans OCR) et répondre par une synthèse orientée par la question.
Deux déclencheurs, détectés **sans LLM** :

1. **explicite** : le message contient `relis`, `relire` ou `rouvre`
   (ex. « relis l'inventaire, où est la perceuse ? ») ;
2. **sur proposition** : réponse d'acceptation (même ensemble que `_URL_RESUME_EXACT` :
   « oui », « vas-y »…) alors que le **dernier tour `assistant`** contient `REREAD_PROPOSAL`
   (« Veux-tu que je relise « X » ? », posé par la consigne du tronçon 01).

## Fichiers à toucher

### `cognition/cognitive_context.py`
`CognitiveOperation.DOC_REREAD = "doc_reread"` (commentaire : relecture d'un document
en mémoire, sprint 43).

### `core/kernel.py`
Table de routage (l. 55-69) : `DOC_REREAD` → `"web_router"`.

### `cognition/cognitive_classifier.py`
`detect_doc_reread(message, metadata, bridge) -> bool`, sur le modèle de
`detect_url_resume` (l. 172-189). Placée dans `classify_operation` **juste après** la règle
2b (reprise de lecture partielle) et avant la règle 3 (recherche web) ; ajouter la ligne au
commentaire de pipeline en tête du fichier. Cas explicite : pas de lecture d'historique.
Cas acceptation : lit `load_conversation_history(chat_id, n=2)` via le bridge.

### `memory/mempalace_bridge.py`
`load_document_text(source: str) -> dict | None` : lecture non vectorielle
(`get_by_metadata`, filtre `wing == "aria_documents"` et `source == source`), rend
`{"title", "text"}` ou `None`. Même idiome que `load_chess_games` (RuntimeError si
`get_by_metadata` non injecté).

### `execution/routers/web_router.py`
Branche `DOC_REREAD` dans `execute` → `_handle_doc_reread(payload)` :

1. **Requête et question** :
   - acceptation (dernier tour assistant porte `REREAD_PROPOSAL`) : requête = nom entre
     `« »` extrait de la proposition ; question = dernier tour `user` de l'historique (la
     question restée sans réponse) ;
   - explicite : requête = question = le message.
2. **Fiche** : `self.mempalace_bridge.retrieve_memories(requête, room="documents", n=1)`
   (wing par défaut `aria_episodic`, seuil 0,8 inchangé). Source = ligne `Source : …` de la
   fiche (format du tronçon 01, regex `^Source : (\S+)$` multiligne).
3. **Texte** : `load_document_text(source)`.
4. **Réponse** : réutiliser la synthèse de `_read_slice` (tranche à partir de 0, orientée par
   la question) en lui fournissant le titre et le texte du palace au lieu d'extraire ;
   **ne pas** réécrire la fiche. Log `doc_reread OK source=… chars=…`.
5. **Rien trouvé** (pas de fiche ou pas de texte) : log `doc_reread NOT_FOUND query=…`,
   puis délégation au `llm_execution_router` avec la consigne
   « [Aucun document correspondant en mémoire : dis-le à Nico en une phrase.] » + message,
   comme les autres échecs du router (`skip_intent`).

## Tests à ajouter (cas nominal)

- `tests/cognition/` : `relis l'inventaire…` → `DOC_REREAD` ; `oui` après un tour assistant
  contenant `REREAD_PROPOSAL` → `DOC_REREAD` ; `oui` sans proposition → pas `DOC_REREAD`.
- `tests/memory/` : `load_document_text` rend titre et texte d'un faux `get_by_metadata`.
- `tests/execution/test_web_router.py` : `DOC_REREAD` avec bridge factice (fiche + texte)
  → prompt de synthèse contenant le texte du palace et la question, pas d'`extract_text`
  ni de `write_document`.

## Hors scope (ne PAS faire)

- Classifier LLM, prompt `CLASSIFIER_PROMPT`, cache classifier.
- Relecture automatique sans accord (Nico a choisi la proposition).
- « lis la suite » après une relecture d'un texte > 100 000 car. : reste fondée sur le
  chemin / l'URL (dette).
- Toucher au prompt AnalystAgent ou à `llm_router.py`.

## Critère de fin

`pytest tests/ -q` vert ; tests ci-dessus passants.
