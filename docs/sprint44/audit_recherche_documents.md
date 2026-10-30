# Sprint 44 — audit : recherche des documents lus (#146, #147)

Date : 2026-10-30. Code au tag `sprint-43` (`main` 1304bbe). Mesures sur une **copie** du palace
prod (`cp -a ~/.mempalace/palace` vers le scratchpad, 2026-10-30) : 6 fiches room `documents`
(1 « Paillis — Wikipédia », 4 « inventaire.txt » en double, cf. #143) [n=6 fiches, 1 palace].

## TL;DR

- **#146** : la fiche Paillis n'est pas perdue, elle est **coupée avant le reclassement**.
  mempalace prend les `n_results` plus proches **par distance vectorielle**, puis seulement
  reclasse ce lot par BM25. Le bridge demande `n × 2` et jette **ensuite** les hits room
  `general` (images) : sur la requête du run live, 9 des 16 candidats sont des images
  [n=8, 1 requête]. La fiche Paillis est ≈ 17e en distance (0,641) : exclue pour tout
  `top_k ≤ 8` (tous les `MEMORY_TOP_K`), présente et classée **1re** à `n = 12`.
- **#147** : deux défauts dans `_handle_doc_reread`.
  1. `retrieve_memories(query, room="documents", n=1)` → le store ne voit que les 2 fiches les
     plus proches en vecteur : les 4 doublons inventaire passent devant toute autre fiche.
  2. Aucun critère de pertinence : dans la room `documents`, la distance vaut 0,42-0,84 quelle
     que soit la question, « impôts » compris (0,654, sous le seuil 0,8). Le seuil ne filtre
     jamais [7 requêtes].
- Cause commune : l'embedder (mpnet) **ne discrimine pas** les fiches entre elles ; c'est le
  signal **lexical** (BM25 de mempalace) qui les départage quand il voit le bon candidat.

## 1. Chemins de code

### 1.1 Rappel global (cas #146)

`execution/routers/llm_router.py:142-143`

```python
top_k = MEMORY_TOP_K.get(operation, 4)
global_memories = self.mempalace_bridge.retrieve_memories(message, n=top_k)
```

`cognition/cognitive_context.py:37` — `MEMORY_TOP_K` : FACT_RECALL 3, MEMORY_QUERY 6,
PLANNING 4, REASONING 8, PROFILE_QUERY 3, UNKNOWN 4 (défaut 4). L'opération de la question du
run live n'est pas journalisée (classification LLM, pas de ligne `op=`) ; quelle qu'elle soit,
`top_k ≤ 8`.

`memory/mempalace_bridge.py:67-136` `retrieve_memories` :

```python
result = self._store(query=query, wing=wing, room=room, n=n * 2)
...
hits = [
    h for h in result.get("results", [])
    if h.get("room", "") != "general"
    and (max_distance is None or h.get("distance", 1.0) < max_distance)
][:n]
```

`memory/mempalace_store.py:9-23` `search` → `mempalace.searcher.search_memories`
(fork `mempalace-fork/mempalace/searcher.py:727`) :

1. `drawers_col.query(n_results = n_results * 3)` (pool vectoriel) ;
2. tri par distance (± boost closets), **`hits = scored[:n_results]`** ;
3. `_hybrid_rank(hits, query)` : 0,6 × similarité + 0,4 × BM25 normalisé, **dans ce lot seulement**.

Le filtre `general` et le seuil 0,8 du bridge s'appliquent après l'étape 3.

### 1.2 Relecture (cas #147)

`execution/routers/web_router.py:221-258` `_handle_doc_reread` :

```python
hits = self.mempalace_bridge.retrieve_memories(query, room="documents", n=1)["hits"]
source_match = _SOURCE_RE.search(hits[0].get("text", "")) if hits else None
doc = self.mempalace_bridge.load_document_text(source_match.group(1)) if source_match else None
if doc is None:
    log.info("doc_reread NOT_FOUND query=%r", query)
```

`n=1` → store `n=2` → pool vectoriel 6, coupé à 2, reclassé. `NOT_FOUND` seulement si la room
est vide ou la distance ≥ 0,8.

### 1.3 Fiche document (écriture, inchangée)

`web_router.py:329-341` : `Document « {nom} » lu le {date}\nSource : {url}\nSynthèse : {digest}`
→ `writer.write_document` (clé `sha256(source)[:16]`). L'URL de la page porte le mot
« Paillage » (`wiki/Paillage`), la synthèse dit « paillis ».

## 2. Mesures (copie du palace)

### 2.1 Rappel global, « que disait la page sur le paillage ? »

| `n` (top_k) | store | dont `general` | Paillis gardé ? |
|---|---|---|---|
| 4 | 8 | 5 | non (3 hits, tous inventaire) |
| 6 | 12 | 7 | non |
| 8 | 16 | 9 | non |
| 12 | 24 | 11 | **oui, 1er** |

[1 requête, 1 palace]. `candidate_strategy="union"` (BM25 sqlite ajouté au pool) : résultat
identique sur 3 requêtes, sans effet.

### 2.2 Room `documents` seule, `n=2` (= ce que voit la relecture)

| requête | 1er hit | distance | BM25 brut |
|---|---|---|---|
| que disait la page sur le paillage ? | inventaire | 0,566 | 1,04 |
| relis le document sur les impôts | inventaire | 0,654 | 1,91 |
| relis le document | inventaire | 0,663 | 0,55 |
| salut | inventaire | 0,703 | 0 |
| quel temps fera-t-il demain ? | inventaire | 0,826 | 0 |
| où est le carton des guirlandes ? | inventaire | 0,587 | 1,46 |
| relis la page sur le paillis | Paillis | 0,600 | 3,33 |

Avec `n=10` (pool = toutes les fiches), « …paillage ? » met Paillis 1re.
Le BM25 brut compte les mots vides (« le », « sur », « document ») : « impôts » score 1,91 sur
l'inventaire sans contenir le mot. Ni la distance ni le BM25 brut ne séparent « trouvé » de
« absent ».

## 3. Diagnostic

1. **Coupe vectorielle prématurée** (#146, #147-1) : tout candidat au-delà des `n × 2` plus
   proches en vecteur est invisible au reclassement lexical, qui est pourtant le seul signal
   discriminant. Les images `general` et les doublons (#143) remplissent ces places.
2. **Pas de critère d'absence** (#147-2) : le seuil 0,8 ne coupe rien entre fiches ; seul un
   critère lexical sur les mots porteurs de la question (hors mots vides) distingue « impôts »
   (absent de toute fiche) de « paillage » (présent dans la fiche Paillis).

## 4. Hors-scope constaté (dettes)

- #143 (doublons d'un même fichier) amplifie le point 1 : 4 places sur 6 dans la room.
- Images en room `general` écartées après la coupe : sous-livraison générale du rappel
  (n=4 → 3 hits) pour toutes les questions, pas seulement les documents.
- L'opération classée et le nombre de souvenirs rappelés ne sont pas journalisés.
