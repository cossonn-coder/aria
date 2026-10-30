# Sprint 45 — audit : recherche autonome

Date : 2026-10-30. Code lu sur `main` @ `82abf69` (tag `sprint-44`).

## TL;DR

- Aujourd'hui `WEB_SEARCH` = **une** requête (reformulée par LLM CHAT à partir du message
  + 2 derniers messages) → **5 extraits** Tavily tronqués à 500 car. → message enrichi →
  `LLMExecutionRouter` en REASONING + `skip_intent`. Ni mémoire épisodique dans la requête,
  ni lecture des pages, ni trace en mémoire hors `aria_conversation`.
- Toutes les briques d'une recherche autonome existent déjà dans `web_router` :
  `search()`, `extract()`, synthèse LLM DIGEST (`_read_slice`), écriture d'un document lu
  (`write_document`), relecture/rappel des documents (sprints 43-44).
- Aucune règle inviolable n'est menacée si la recherche reste **dans le router web**
  (dépendances injectées : `llm_router`, bridge ; écriture via `writer.write_document`).

## 1. Déclenchement actuel

`cognition/cognitive_classifier.py` :
- règle 3 (heuristique, avant « message court ») : `detect_web_search_intent` —
  sous-chaînes `cherche en ligne`, `cherche sur le web`, `cherche sur internet`,
  `recherche en ligne`, `recherche sur le web`, `donne-moi les sources` ; exact `source(s)`.
- classifier LLM : catégorie `web_search` (« information récente ou externe… météo, score, prix »).
- Ordre : image > PGN > URL > reprise URL > relecture doc > web search > génération image > court.

Routage : `core/kernel.py` `_ROUTING_TABLE` → `web_router` (WEB_SEARCH, URL_READ, FILE_READ,
DOC_REREAD). Ajouter une opération = 1 ligne de table + 1 branche dans `WebExecutionRouter.execute`.

## 2. Pipeline WEB_SEARCH (`execution/routers/web_router.py:120-187`)

1. `_build_query` : `bridge.load_conversation_history(chat_id, n=2)` + prompt « requête courte »
   → `llm_router.complete(role=CHAT, temperature=0.1, max_tokens=40)` ; repli = message brut.
2. `search(query)` (`web/tavily_search.py`) : `search_depth="basic"`, `max_results=5`, timeout 15 s.
3. Enrichi : `[Résultats web pour « q » : 1. titre — url / extrait[:500] …]` + consigne
   « réponds à partir de ces résultats, liste des URL ».
4. Échec (exception ou 0 résultat) → consigne « recherche indisponible ».
5. Délégation `LLMExecutionRouter.execute(op=REASONING, skip_intent=True)` : le pipeline texte
   ajoute mémoire globale (`retrieve_memories`), `find_documents`, historique (plafond 6 000 car.),
   agent analyst ; écrit l'échange dans `aria_conversation`.

Limites constatées au code :
- une seule requête, pas de décomposition du sujet ;
- 5 × 500 car. d'extraits : jamais le texte des pages ;
- la mémoire de Nico (épisodique, documents) n'entre pas dans la requête (seulement dans la
  réponse finale, via le pipeline texte) ;
- rien n'est conservé hors historique de conversation → introuvable quelques jours plus tard
  (même défaut que #137 avant le sprint 43).

## 3. Briques réutilisables

| Brique | Où | Usage possible |
|---|---|---|
| `search(query, max_results)` | `web/tavily_search.py:21` | une requête par sous-question |
| `extract(url)` | `web/tavily_search.py:41` | texte intégral des meilleures pages |
| Synthèse DIGEST (sans Groq) | `web_router._read_slice` (prompt l.301-313) | synthèse orientée par la question |
| `write_document(fiche, text, source, title)` | `memory/writer.py:164` | rapport conservé (fiche `documents` + texte `aria_documents`), clé = sha256(source) |
| `bridge.find_documents` / `load_document_text` | `memory/mempalace_bridge.py:357,388` | rapport retrouvé au rappel global et relu par « relis… » |
| `bridge.retrieve_memories(q, n)` | bridge | souvenirs de Nico sur le sujet pour orienter les requêtes |
| `bridge.load_conversation_history` | bridge | contexte de conversation |

Contraintes à respecter pour la fiche : format `Document « X » lu le …\nSource : <sans espace>\nSynthèse : …`
(`_SOURCE_RE = ^Source : (\S+)$`, parsé par la relecture et le rappel). En relecture,
`_read_slice` traite toute source non `http(s)` comme un fichier (libellés « du fichier ») :
cosmétique pour une source `recherche:…`.

## 4. Latence et interface

`interfaces/telegram_interface.py:50-54` : « écrit… » toutes les 4 s, un seul
`⏳ Je travaille dessus, ça peut prendre jusqu'à 2 minutes.` au-delà de 20 s ; traitement
dans `asyncio.to_thread` (sprint 30). Pas de message intermédiaire possible depuis un router
(contrat de sortie = un seul retour). Une recherche multi-requêtes + lecture de pages +
2 appels LLM longs tient dans ce cadre ; pas besoin de toucher l'interface en v1.
Pendant ce temps, PTB ne traite pas d'autre message (#112).

Timeouts : Tavily search 15 s, extract 30 s, LLM 30 s par appel HTTP (`llm/llm_router.py:359,400`).

## 5. Règles d'architecture

- Règle 1 : écriture du rapport via `writer.write_document` (existant) — conforme.
- Règle 2 : lectures mémoire via le bridge (déjà injecté dans `WebExecutionRouter`) — conforme.
- Règle 3 : la mémoire est lue par le router, pas par un agent — conforme.
- Règle 4 : le router renvoie `{"text"}` via `LLMExecutionRouter` — conforme.
- Règle 5 : kernel inchangé hors 1 ligne de table — conforme.
- Drapeau : une « boucle agent » libre (LLM qui décide d'appeler des outils) ferait entrer
  la décision dans le LLM ; reste acceptable si la boucle est **dans le router**, bornée.

## 6. Coût

Tavily : barème non vérifié dans ce tour [à confirmer sur le compte] ; une recherche
autonome = plusieurs `search` + 1 `extract` par page lue, contre 1 `search` aujourd'hui.
LLM : +1 appel de plan, +1 synthèse par page ou 1 synthèse groupée, + réponse finale.
