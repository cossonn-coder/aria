# Sprint 17 — tronçon 01 : isoler les tests du palace et des intents de prod

## Objectif

`pytest tests/ -q` ne doit plus jamais écrire dans `~/.mempalace/palace`
ni dans `~/.aria/intents.json`. Aujourd'hui il le fait : 286 documents
« réponse factice aria » en prod, `intents.json` réécrit à chaque run.

## Cause (vérifiée au code le 2026-10-15)

`tests/conftest.py` a une fixture `autouse` `mock_network` qui mocke
`httpx` et `Embedder`, mais rien côté stockage. Les tests qui construisent
un vrai `AriaKernel()` (ex. `tests/cognition/test_cognitive_scenarios.py`)
utilisent donc les vrais chemins :

- `config.mempalace_path` (objet `config` du module `config.py`,
  ligne 86 : `/home/nico/.mempalace/palace`). Lu **au moment de l'appel**
  par `memory/writer.py` (`get_collection(config.mempalace_path)`),
  `memory/mempalace_store.py:16` et `memory/mempalace_bridge.py:259`.
- `intent.intent_store.STORE_PATH` (global de module,
  `Path.home() / ".aria" / "intents.json"`), lu au moment de l'appel
  par `save_intents` / `load_intents`.

## À faire

Dans `tests/conftest.py`, une fixture `autouse` (nouvelle ou ajoutée à
l'existante, au choix le plus simple) qui, pour chaque test :

- pointe `config.mempalace_path` vers un dossier sous `tmp_path` ;
- pointe `intent.intent_store.STORE_PATH` vers un fichier sous `tmp_path`.

Via `monkeypatch.setattr`. S'applique aussi aux tests marqués `live`
(les tests `live` testent les providers réseau, pas le palace de prod).

Vérifie qu'aucun module prod ne capture ces chemins dans une variable
au chargement (grep `mempalace_path` et `STORE_PATH` hors `scripts/` et
`tests/`). Si c'est le cas, signale-le au point (5) du rapport.

## Tests

- Un test de non-régression : construire `AriaKernel()`, traiter un
  message (helper existant de `test_cognitive_scenarios.py`), vérifier
  que des fichiers sont apparus sous `tmp_path` et que le chemin prod
  n'est pas celui utilisé (ex. `config.mempalace_path` commence par
  `str(tmp_path)`).
- Critère de fin **mesuré** : noter la date de modification de
  `~/.mempalace/palace/chroma.sqlite3` et de `~/.aria/intents.json`
  (`stat -c %y`), lancer `./venv/bin/pytest tests/ -q`, vérifier
  qu'elles n'ont **pas changé**. À consigner dans le rapport.

Note : un palace neuf sous `tmp_path` n'a pas de marker
`.mempalace-embedder.json` → mempalace prend l'embedder ONNX MiniLM par
défaut (modèle en cache dans `~/.cache/chroma/onnx_models`). C'est
acceptable pour les tests. Si des tests cassent pour une question de
dimension de vecteur, corrige au plus simple dans `conftest.py` et
signale-le.

## Ne PAS faire

- Ne pas toucher au code de prod (`config.py`, `intent/intent_store.py`,
  `memory/`). Seul `tests/` change.
- Ne pas nettoyer le palace ni `intents.json` de prod (prévu au tronçon 03,
  par Nico).
- Ne pas refactorer les tests existants au-delà de ce qu'exige la fixture.

## Critère de fin

pytest vert, test de non-régression ajouté, dates de modification des
fichiers prod inchangées après un run complet.
