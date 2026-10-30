# Sprint 45 — tronçon 01 : recherche autonome (`WEB_RESEARCH`)

Lire d'abord : `CLAUDE.md`, `docs/sprint45/00_etat.md`, puis le TL;DR de
`docs/sprint45/audit_recherche_autonome.md`.

## Objectif

Sur une demande explicite (« fais une recherche sur… »), ARIA mène une recherche en **une
vague** : plan de 3 à 5 requêtes construit à partir de la conversation et de la mémoire →
Tavily → lecture intégrale de 3 pages → rapport avec sources → rapport conservé comme
document lu → réponse via le pipeline texte. La recherche rapide `WEB_SEARCH` est inchangée.

## Fichiers à toucher (vérifiés au code, `main` @ `82abf69`)

1. `cognition/cognitive_context.py` — ajouter `WEB_RESEARCH = "web_research"` à
   `CognitiveOperation` (après `DOC_REREAD`, commentaire `# recherche autonome (sprint 45)`).
   Pas d'entrée dans `MEMORY_TOP_K` / `LLM_ROLE_MAP` : la réponse est déléguée en REASONING.
2. `cognition/cognitive_classifier.py` — heuristique `detect_web_research_intent(message)`
   (sous-chaînes, minuscules) : `fais une recherche sur`, `fais des recherches sur`,
   `fais une recherche approfondie`, `recherche approfondie`, `renseigne-toi sur`,
   `renseigne toi sur`. Dans `classify_operation`, règle **3a juste avant** la règle 3
   (`detect_web_search_intent`) : « fais une recherche en ligne sur X » contient « recherche en
   ligne » et doit partir en `WEB_RESEARCH`. Pas de catégorie dans `CLASSIFIER_PROMPT`.
3. `core/kernel.py` — `_ROUTING_TABLE` : `CognitiveOperation.WEB_RESEARCH.value : "web_router"`.
4. `execution/routers/web_router.py` — branche dans `execute()` + `_handle_research(payload)`
   (et helpers privés si utile). Mettre à jour l'en-tête du module (pipeline WEB_RESEARCH).

## Comportement attendu de `_handle_research`

Imports déjà présents dans le module : `search`, `extract`, `write_document`, `LLMRole`,
`hashlib`, `date`. Tout passe par `self.llm_router` et `self.mempalace_bridge` (déjà injectés).

1. **Contexte** : `self.mempalace_bridge.load_conversation_history(chat_id, n=4)` (clé =
   `str(metadata.get("chat_id", "default"))`, comme `_build_query`) et
   `self.mempalace_bridge.retrieve_memories(message, n=4)["hits"]` (textes coupés à ~300 car.).
2. **Plan** : `self.llm_router.complete(role=LLMRole.CHAT, temperature=0.2, max_tokens≈200)`,
   prompt : formuler 3 à 5 requêtes web courtes couvrant les angles du sujet, en tenant compte
   de la conversation et des souvenirs de Nico ; **une requête par ligne**, rien d'autre.
   Parse : lignes non vides, nettoyées (puces, numéros, guillemets), 5 max. Exception ou
   liste vide → `[message]`. Log `web_research plan queries=%d %r`.
3. **Recherche** : `search(q)` pour chaque requête, séquentiel. Exception sur une requête →
   `log.warning` et on continue. Aucun résultat au total → même consigne « [Recherche web
   indisponible : …] » que `_handle_search`, délégation, fin.
4. **Lecture** : URL candidates = 1er résultat de chaque requête dans l'ordre, puis les
   suivants, **sans doublon**, 3 max (`_RESEARCH_PAGES = 3`). `extract(url)` ; échec → on
   garde l'extrait Tavily de ce résultat. Texte de chaque page coupé à
   `_RESEARCH_PAGE_MAX_CHARS = 30_000` [arbitraire]. Log `web_research pages read=%d failed=%d`.
5. **Rapport** : un appel `LLMRole.DIGEST` (chaîne sans Groq), `max_tokens≈1500`, prompt :
   rapport fidèle en français sur la demande de Nico, sans rien inventer, à partir des pages et
   des extraits fournis (titre + URL de chacun), terminé par la liste des URL utilisées.
   Exception → consigne « [Recherche web indisponible : …] » et délégation.
6. **Trace** (non bloquante, comme la fiche de `_read_slice`) :
   - `source = f"recherche:{date.today().isoformat()}-{sha256(message)[:8]}"` (sans espace :
     `_SOURCE_RE = ^Source : (\S+)$` doit la parser) ;
   - `doc_name = f"Recherche : {sujet}"` où sujet = le message (coupé à ~80 car.) ;
   - fiche au **même format** que `_read_slice` : `Document « {doc_name} » lu le {date}\n
     Source : {source}\nSynthèse : {rapport}` ;
   - `write_document(fiche, rapport, source, doc_name)` dans un `try/except Exception` +
     `log.exception("document_write ERROR …")` ; succès → `log.info("document_write OK key=%s source=%s chars=%d", …)`.
7. **Réponse** : `self.llm_execution_router.execute({"op_type": REASONING, "content": enriched,
   "metadata": {**metadata, "skip_intent": True}})` avec
   `enriched = "[Rapport de recherche « {sujet} » :\n{rapport}]\n[Consigne : réponds à Nico à
   partir de ce rapport et termine par la liste des URL utilisées.]\n\n{message}"`.
   Log final `web_research OK queries=%d results=%d pages=%d`.

## Tests à ajouter (cas nominal, fakes, pas de réseau)

- `tests/cognition/test_classifier_web_search.py` (ou fichier voisin) : « fais une recherche sur
  le paillage » → `WEB_RESEARCH` ; « fais une recherche en ligne sur X » → `WEB_RESEARCH` ;
  « cherche en ligne la météo » → toujours `WEB_SEARCH`.
- `tests/execution/test_web_router.py` (fixture `write_document_mock` déjà autouse) :
  `search` / `extract` monkeypatchés, `llm_router.complete` renvoyant le plan puis le rapport
  (`side_effect`) → délégation REASONING + `skip_intent`, rapport dans `content`,
  `write_document` appelé une fois avec une source `recherche:…` et une fiche contenant
  `Source : recherche:`.

`pytest tests/ -q` vert.

## À ne PAS faire

- Toucher `_handle_search` / `WEB_SEARCH`, `CLASSIFIER_PROMPT`, l'interface Telegram, le bridge
  ou `memory/writer.py`.
- Relance / 2e vague, boucle agent, parallélisme des requêtes.
- Adapter `_read_slice` aux sources `recherche:` (libellé « du fichier » en relecture :
  dette acceptée, cf. `00_etat.md`).
- Lire la mémoire ailleurs que via le bridge ; écrire ailleurs que via `write_document`.

## Critère de fin

Tests ajoutés verts, suite complète verte, commit local
`feat(sprint45) tronçon 01: recherche autonome WEB_RESEARCH`.
