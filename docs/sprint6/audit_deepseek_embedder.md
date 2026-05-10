## Analyse des hits

Le fichier `/tmp/audit_384.txt` contient uniquement deux lignes, toutes deux issues du troisième grep (`len(.*embed|len(.*vec`).  
Aucune occurrence du nombre `384` ni des mots‑clés liés à la dimension d’embedding n’a été trouvée dans l’ensemble du scope (`embedding/`, `intent/`, `memory/`, `cognition/`, `execution/`, `agents/`, `core/`, `llm/`, `config.py`, `kernel.py`).

Les deux lignes capturées sont les suivantes :

```
embedding/embedding_contract.py:16:        if len(vec) != self.dim:
embedding/embedding_contract.py:18:                f"Embedding dimension mismatch: got {len(vec)}, expected {self.dim}"
```

| Fichier:ligne | Catégorie | Contexte (3 lignes) | Justification |
|----------------|-----------|---------------------|----------------|
| `embedding/embedding_contract.py:16` | **C_NEUTRE** | `<...>`<br>`if len(vec) != self.dim:`<br>`raise ValueError(` | Cette ligne ne contient aucune valeur fixe `384`. Elle compare la taille du vecteur à un attribut `self.dim` qui est très probablement initialisé dynamiquement (lecture depuis le modèle d’embedding ou depuis la configuration). La migration vers 768 n’impose aucun changement ici, car `self.dim` deviendra 768 automatiquement. |
| `embedding/embedding_contract.py:18` | **C_NEUTRE** | `raise ValueError(`<br>`f"Embedding dimension mismatch: got {len(vec)}, expected {self.dim}"`<br>`)` | Même logique : le message d’erreur utilise `self.dim` – pas de valeur codée en dur. Ce code est générique et s’adaptera à n’importe quelle dimension. |

Aucun autre hit n’a été relevé. Les greps pour `384`, `embedding_dim`, `EMBEDDING_DIM`, `vector_size`, `shape[0]`, etc. n’ont retourné aucun résultat dans les modules ciblés.

## Vérification complémentaire (fichiers non fournis)

Vous avez indiqué que vous alliez coller les fichiers `embedding/embedder.py`, `embedding/embedding_contract.py` et `intent/intent_recall_engine.py`, mais ceux‑ci sont absents du message.  
Sur la base des seuls greps, aucune valeur `384` n’est présente. Il est donc probable que le projet ARIA utilise déjà une dimension d’embedding paramétrée (typiquement lue via `model.get_sentence_embedding_dimension()` pour Sentence‑Transformer, ou via une variable de configuration).

Pour une sécurité absolue, vérifiez néanmoins les points suivants (non couverts par les greps car ne contenant pas `384` explicitement) :

- **Fichiers de configuration** (`config.py`, éventuels `.env`, `yaml`) : une variable comme `EMBEDDING_DIM = 384` serait un **bloqueur** (modification nécessaire).
- **Initialisation de l’embedder** : si le modèle est chargé avec `SentenceTransformer('all-MiniLM-L6-v2')` et que la dimension est déduite du modèle, c’est sûr. Si une constante `384` est utilisée ailleurs pour créer des tableaux (ex. `np.zeros(384)`), elle apparaîtrait dans les greps – ce n’est pas le cas.
- **Couche de mémorisation / persistence** : les vecteurs existants en base ont une dimension 384. Après migration vers 768, les anciens vecteurs ne seront plus compatibles. Prévoyez un recalcul ou un stockage distinct.

## Conclusion

| Catégorie | Nombre |
|-----------|--------|
| **A_BLOCKER** | 0 |
| **B_OBSERVATION** | 0 |
| **C_NEUTRE** | 2 |

> **La migration de la dimension d’embedding de 384 vers 768 est sûre** du point de vue du code source analysé, car aucune valeur fixe `384` n’est utilisée.  
> **Prérequis fonctionnels** :  
> - Vérifiez dans `config.py` ou l’initialisation de l’embedder qu’aucune constante dimension n’est définie.  
> - Assurez‑vous que la dimension est bien lue dynamiquement depuis le modèle (`model.get_sentence_embedding_dimension()`).  
> - Prévoyez une stratégie de migration pour les embeddings déjà stockés (recalcul, double index, ou rétrocompatibilité).