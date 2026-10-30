# Sprint 44 — tronçon 01 : recherche de documents (#146, #147)

Lire d'abord : `CLAUDE.md`, `docs/sprint44/00_etat.md`, TL;DR de
`docs/sprint44/audit_recherche_documents.md`.

## Objectif

Une fiche document (room `documents` d'`aria_episodic`) doit être retrouvée quand la question
porte un de ses mots, et la relecture doit répondre `NOT_FOUND` quand aucune fiche ne correspond.

Rappel du problème (audit §3) : mempalace coupe aux N plus proches en vecteur **avant** son
reclassement BM25 ; la distance ne discrimine pas les fiches (0,42-0,84 pour toute question) ;
le seuil 0,8 ne filtre jamais. Le signal fiable est lexical.

## Fichiers à toucher (vérifiés au code, tag `sprint-43`)

1. `memory/mempalace_bridge.py` — nouvelle méthode publique de lecture, ex.
   `find_documents(query: str) -> list[dict]` :
   - candidats = **toute** la room : `self.retrieve_memories(query, room="documents", n=<constante,
     ex. 20>)` (ordre = classement hybride de mempalace ; seuil 0,8 par défaut conservé) ;
   - mots porteurs de la requête = tokens `\w+` en minuscules, **sans accents**
     (`unicodedata` NFKD), longueur ≥ 4, hors une courte liste de mots vides en constante
     (au minimum : `document(s)`, `page(s)`, `fichier(s)`, `relis`, `relire`, `rouvre`,
     `disait`, `dans`, `pour`, `avec`, `quoi`, `cette`, `etait`, `sont`) ;
   - garde, dans l'ordre, les fiches dont le texte (normalisé de la même façon) contient au
     moins un mot porteur (correspondance de token exacte) ;
   - la requête sans mot porteur doit être distinguable par l'appelant (ex. retour `None`
     vs `[]`, ou fonction auxiliaire publique) : la relecture en a besoin (point 2).
   Lecture seule, aucun import de `mempalace_store` ailleurs que le bridge (règle 2).
2. `execution/routers/web_router.py` `_handle_doc_reread` (l. 221-258) : remplacer
   `retrieve_memories(query, room="documents", n=1)` par :
   - requête avec mots porteurs → 1re fiche de `find_documents`, sinon `NOT_FOUND` (branche
     existante, inchangée) ;
   - requête sans mot porteur (« relis le document ») → meilleure fiche comme aujourd'hui
     (1er candidat de la room).
   La suite (`_SOURCE_RE` → `load_document_text` → `_read_slice(page=…)`) ne change pas.
   Cas acceptation « oui » : la requête est le nom tiré de la proposition (inchangé).
3. `execution/routers/llm_router.py` étape 1 (l. 142-143) : après `global_memories`, appeler
   `find_documents(message)` ; garder la 1re fiche (si la requête n'a pas de mot porteur ou si
   rien ne correspond : aucune). Journaliser une ligne
   `log.info("document_recall source=%s", …)` quand une fiche est retenue.
   La passer à l'étape 4b (`build_context_block`, l. 254-260).
4. `cognition/context_builder.py` `build_context_block` (l. 36) : nouveau paramètre optionnel
   (ex. `document_hit: dict | None = None`). La fiche entre **en tête** des souvenirs de la
   section épisodique, que la session soit pleine (≥ 3 hits) ou non, sans doublon (même
   `text` déjà présent → pas répétée). Le rendu existant des fiches (extrait 1 500 car.,
   `_REREAD_INSTRUCTION`) s'applique tel quel (`room == "documents"`).

## Tests à ajouter (cas nominal)

- Bridge (`tests/memory/test_mempalace_bridge_documents.py` ou `tests/mempalace/`, store fake) :
  « que disait la page sur le paillage ? » garde la fiche dont le texte contient
  `wiki/Paillage` et écarte une fiche inventaire ; « relis le document sur les impôts » → aucune
  fiche ; « relis le document » → cas « sans mot porteur ».
- `tests/execution/test_web_router.py` : « relis le document sur les impôts » avec une fiche
  inventaire en room → `load_document_text` non appelé, consigne « Aucun document
  correspondant ». Adapter `test_doc_reread_synthesizes_palace_text_without_extraction`
  (l. 236) au nouvel appel.
- `tests/cognition/test_context_builder.py` : `document_hit` présent en tête alors que la
  session a 3 hits.
- `pytest tests/ -q` vert.

## Hors-scope (ne pas faire)

- Pas de changement du fork mempalace, de `mempalace_store.search`, du facteur `n * 2` ni du
  filtre `general` de `retrieve_memories` (dette).
- Pas de dédoublonnage des fiches (#143), pas de changement de `write_document` ni du format
  de fiche.
- Pas d'appel LLM pour choisir le document.
- Pas de modification du prompt AnalystAgent ni de `soul.md`.
- Palace prod : aucune écriture, aucun script dessus.

## Critère de fin

Tests ci-dessus verts, `pytest tests/ -q` vert, commit local
`feat(sprint44) tronçon 01: recherche de documents par mots porteurs (#146, #147)`.
