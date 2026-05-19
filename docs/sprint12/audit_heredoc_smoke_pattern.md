# Sprint 12 — Item #25 — Audit heredoc smoke runbook (pré-fix)

**Date** : 2026-05-19
**Branche** : `feat/sprint12-chroma-hnswlib-pin`
**Mode** : lecture seule du runbook et du code fork, aucune mutation
ni exécution live.

---

## Section 1 — Localisation du runbook smoke

Grep des mots-clés (`heredoc|smoke|<<EOF|fumée|sentence-transformers.*smoke`)
sur `.md`, `.sh`, `.py` de la repo (hors `.git/` et `venv/`) :

| Candidat | Portée |
|---|---|
| `docs/sprint7/runbook_t_mempalace_live.md` § 6 (lignes 300-392) | « [GÉNÉRIQUE] Smoke test ouverture palace + query — valide deux choses : (1) palace s'ouvre sans crash, sans quarantine de segment HNSW ; (2) embedding function est bien SentenceTransformer-based (mpnet), pas l'ONNX MiniLM par défaut. » |
| `docs/sprint6/runbook_t_embedder3.md` § 7 « Test fumée Telegram » | Fumée Telegram applicative, pas un heredoc Python sur la couche embedder. Hors périmètre #25. |

**Conclusion** : un seul heredoc Python pertinent, dans
`docs/sprint7/runbook_t_mempalace_live.md` lignes 328-380. Pas
d'autre `<<EOF` dans ce runbook (vérifié par
`grep -nE "<<\s*['\"]?(EOF|PY|BASH)" docs/sprint7/runbook_t_mempalace_live.md`
→ une seule occurrence ligne 328).

---

## Section 2 — Identification du heredoc problématique

### Bloc heredoc intégral (lignes 327-381)

```bash
./venv/bin/python <<'EOF'
"""Smoke test palace post-migration — ouverture + query minimale.

Ouvre le palace via l'API fork (mempalace.palace.get_collection)
qui consomme le marker .mempalace-embedder.json. Court-circuiter
ce point d'entrée invalide le test.
"""
from mempalace.palace import get_collection

# Garde "fork actif" — redondant avec Section 1 check 1, mais
# ferme le trou si un opérateur saute la Section 1 ou si pip a
# réinstallé mempalace upstream entre-temps.
import mempalace
assert "mempalace-fork" in mempalace.__file__, (
    f"fork MemPalace non actif (mempalace.__file__ = "
    f"{mempalace.__file__}). Cf. Section 1 check 1."
)

PALACE_PATH = "/home/nico/.mempalace/palace"
COLLECTION = "mempalace_drawers"

# 1. Ouverture via l'API publique du fork (consomme le marker)
col = get_collection(PALACE_PATH, collection_name=COLLECTION, create=False)

# 2. Inspection basique — count et dim
count = col.count()
got = col.get(limit=1, include=["embeddings"])
embeddings = got.embeddings
dim = len(embeddings[0]) if embeddings else None
print(f"[smoke] count={count} dim={dim}")
assert dim == 768, f"dimension attendue 768, vu {dim}"

# 3. Query minimale (côté lecture, déclenche la EF)
res = col.query(query_texts=["Bonjour"], n_results=3)
top_ids = res.ids[0] if res.ids else []
print(f"[smoke] query 'Bonjour' top_ids={top_ids}")
assert len(top_ids) > 0, "query a retourné zéro résultat"

# 4. Vérification du backend EF effectivement chargé.
#    ChromaCollection (wrapper du fork) expose l'objet ChromaDB
#    sous-jacent via _collection ; on lit son _embedding_function.
ef = col._collection._embedding_function
ef_repr = repr(ef)
print(f"[smoke] embedding_function: {ef_repr}")

# Pattern ATTENDU : la classe doit contenir SentenceTransformer
# (le fork écrit SentenceTransformerEmbeddingFunction quand le
#  marker .mempalace-embedder.json est consommé correctement).
assert "SentenceTransformer" in ef_repr, (
    f"backend EF inattendu (attendu SentenceTransformer-based) : {ef_repr}"
)
print("[smoke] OK — backend sentence-transformers actif")
EOF
```

### Pattern strict identifié

**Ligne 376** : `assert "SentenceTransformer" in ef_repr, …`

Le pattern repose sur la sous-chaîne `SentenceTransformer`
recherchée dans `repr(ef)` (ligne 370). `repr()` d'un objet
Python sans `__repr__` custom retourne par défaut
`<module.ClassName object at 0x…>`. Le test suppose donc que
la classe utilisée a un nom contenant textuellement
« SentenceTransformer ».

### Sortie réelle (non disponible dans cette session)

Aucun log sprint 7-8 stocké dans la repo ne capture la sortie
exacte du `print(f"[smoke] embedding_function: {ef_repr}")`. À
**reproduire par Nico** si besoin de confirmation runtime ; le
diagnostic statique ci-dessous suffit toutefois à localiser la
cause sans la sortie.

---

## Section 3 — Diagnostic

### a) Quelle est la stricture ?

**Stricture textuelle, sur le nom de la classe d'instanciation**.
Le test `"SentenceTransformer" in repr(ef)` suppose que le
nom de classe Python (tel qu'apparaissant dans
`<module.ClassName object at 0x…>`) contient la sous-chaîne
`SentenceTransformer`. C'est une stricture syntaxique sur un
artefact d'implémentation (le nom de classe), pas une stricture
sémantique sur la lignée (héritage) ou sur la configuration
(model_name).

### b) D'où vient le faux négatif ?

Lecture de `mempalace/embedding.py` du fork
(`/home/nico/Nextcloud/projects/mempalace-fork/mempalace/embedding.py`)
ligne 141-150 :

```python
def _build_st_ef_class():
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

    class _MempalaceST(SentenceTransformerEmbeddingFunction):
        def name(self):
            return "default"

    return _MempalaceST
```

Le fork **subclass tactiquement** `SentenceTransformerEmbeddingFunction`
en `_MempalaceST` (pour overrider `name() → "default"`,
probablement pour la compatibilité avec un check chromadb par
nom). L'instance retournée par `get_embedding_function(model_name=…)`
est donc de classe **`_MempalaceST`**, pas `SentenceTransformerEmbeddingFunction`.

Par conséquent, `repr(ef)` ressemble à :

```
<mempalace.embedding._MempalaceST object at 0x7f…>
```

La sous-chaîne `SentenceTransformer` **n'y figure pas**. L'assert
échoue alors même que le backend est, sémantiquement,
parfaitement sentence-transformers (lignée d'héritage correcte,
model_name mpnet, dim 768).

**Origine temporelle** : le subclass `_MempalaceST` existe déjà
au commit `b8caf32` du fork (`feat/configurable-embedder`, version
3.3.5, sprint 7). Le runbook smoke a été rédigé en parallèle
sprint 7 avec l'hypothèse implicite que la classe utilisée
serait `SentenceTransformerEmbeddingFunction` nu — hypothèse
fausse depuis le départ. Le pattern n'a donc **jamais été
correct** pour la version effective du fork ; il aurait fonctionné
contre un chromadb stock sans subclass.

### c) Périmètre du fix

**≤ 5 lignes** : remplacer l'assert textuel par un check
sémantique sur la lignée (isinstance) ou sur la MRO. Aucun
refactoring du runbook au-delà de ce bloc. Pas de mock à
ajuster (pas de tests pytest mocks ici, c'est un smoke
runbook standalone).

**Verdict : TRIVIAL**, faisable en fin de session si Nico le
souhaite.

### d) Pas de bug de fond masqué

Vérifications convergentes contre l'hypothèse « le pattern
masque un bug de fond » :

- `_MempalaceST` dérive bien de `SentenceTransformerEmbeddingFunction`
  (héritage direct, ligne 145 de `embedding.py`).
- `get_embedding_function(model_name=…)` instancie via
  `ef_cls(model_name=model_name)` (ligne 207 de `embedding.py`),
  donc le model_name est bien transmis à la couche
  sentence-transformers.
- L'assert dim 768 (ligne 358 du runbook) **passe** quand le
  smoke est exécuté en prod (sinon la migration sprint 8 aurait
  échoué visiblement) — donc l'embedder produit bien des
  vecteurs mpnet, et la cible runtime du test est atteinte.
- La dette #25 est apparue au sprint 9 (kickoff sprint 9
  ligne 99 : « nouveau »), donc post-migration ; le smoke avait
  servi en sprint 7-8 pour acter la bascule et le pattern textuel
  avait probablement été contourné manuellement à l'œil par
  l'opérateur. La dette est de l'hygiène de runbook, pas un
  signal embedder.

Aucun bug de fond. Pas de stop scope. Discipline du brief
respectée.

---

## Section 4 — Proposition de fix (description, pas de code)

Trois options envisagées :

**Option A (préférée)** — Remplacer l'assert textuel par un
`isinstance(ef, SentenceTransformerEmbeddingFunction)` après
import explicite de la classe ancêtre depuis
`chromadb.utils.embedding_functions`. Justification : check
sémantique sur la lignée d'héritage, robuste à tout subclass
présent ou futur du fork. Aligne le test sur ce que la doc
prétend vérifier (« backend SentenceTransformer-based »). Coût :
+1 ligne d'import, modification du predicate de l'assert,
soit ~3 lignes de diff effectif.

**Option B** — Check MRO textuel :
`"SentenceTransformer" in str(type(ef).__mro__)`. Avantage :
aucun import à ajouter, ne touche qu'une ligne. Inconvénient :
reste un check textuel, fragile si chromadb renomme la classe
parente dans une future release. Refusée pour cette fragilité
résiduelle.

**Option C** — Vérification par attributs internes (`ef.name()`,
`ef._model_name`). Refusée : trop spécifique à l'implémentation
actuelle, fait reposer le test sur des attributs privés (préfixe
`_`) qui peuvent disparaître sans préavis.

**Préférée : Option A.** Le diff effectif sera de l'ordre de :

- L373-378 du runbook : remplacer le commentaire « Pattern
  ATTENDU » et l'assert textuel par l'isinstance + message
  d'erreur reflétant la classe concrète et son MRO.
- Ajouter dans le bloc heredoc (en haut, vers L335) :
  `from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction`.
- Garder le `print(f"[smoke] embedding_function: {ef_repr}")`
  ligne 371 inchangé : il reste utile pour la trace humaine
  même si l'assert ne s'y appuie plus.

**Note de vigilance opérationnelle** : le runbook touche au
palace prod (T-Mempalace-Live). Le fix proposé ne change pas
le comportement runtime du smoke (mêmes appels, même path
d'ouverture, même query) — il relâche uniquement la condition
de succès. Risque de masquer un incident embedder réel : **nul**
tant que la condition reste un check d'héritage strict (option
A). Un opérateur exécutant le smoke après le fix doit toujours
voir l'embedder mpnet effectif via la ligne `[smoke] embedding_function:
<…_MempalaceST object at …>` qui restera affichée pour
diagnostic visuel.

Estimation totale du fix : **3 à 5 lignes modifiées**, scope
strictement contenu à la section 6 du runbook, sans toucher
au code applicatif ni au fork.
