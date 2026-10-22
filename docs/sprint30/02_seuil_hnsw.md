# Tronçon 02 — script ponctuel : plus de quarantaine HNSW au démarrage (#105)

Lire d'abord : `CLAUDE.md`, `docs/sprint30/00_etat.md`, `docs/sprint30/audit_fiabilite_analyse.md` §#105
(dont « Vérification du correctif sur copie »).

## Constat (résumé de l'audit)

`mempalace_drawers` (475 entrées, tout le palace prod) a `sync_threshold = 50000` : l'index
HNSW n'est jamais persisté (`index_metadata.pickle` absent), donc mempalace le met en
quarantaine (`.drift-*`) à chaque démarrage. Vérifié sur copie : `col.modify(configuration=
{"hnsw": {"sync_threshold": 100, "batch_size": 100}})`, puis ouverture **par un nouveau
process** + une requête → pickle écrit, `embeddings_queue` purgé, plus de quarantaine.

## Objectif

Créer `scripts/mempalace_sync_threshold.py` (style des autres scripts de `scripts/`, logger,
pas de `print()` sauf si les scripts voisins en usent — suivre leur usage), qui, sur
`config.mempalace_path` par défaut (argument optionnel pour un autre chemin, utile aux tests) :

1. refuse de tourner si `aria.service` est actif (`systemctl is-active --quiet aria.service`
   code 0 → message clair et sortie non nulle) ; ce garde ne s'applique pas quand un chemin
   explicite est passé ;
2. sauvegarde `chroma.sqlite3` en `chroma.sqlite3.bak-<AAAAMMJJ-HHMMSS>` à côté ;
3. applique `modify(configuration={"hnsw": {"sync_threshold": 100, "batch_size": 100}})`
   sur `mempalace_drawers` (accès chromadb direct : opération de configuration ponctuelle,
   pas une écriture de données ; la règle 1 vise les écritures de drawers) ;
4. fait ouvrir la collection par un **nouveau process** (sous-processus Python) avec une
   requête, puis vérifie la présence de `<segment>/index_metadata.pickle` ; absent → erreur
   claire, sortie non nulle, `.drift-*` non supprimés ;
5. pickle présent → supprime les dossiers `<palace>/*.drift-*` et journalise combien.

Idempotent : relancé, il ne casse rien.

## Tests

Un test sur une copie miniature : créer un palace temporaire via
`mempalace.palace.get_collection(tmp)` (qui pose le seuil 50000), y ajouter quelques entrées
avec embeddings explicites, créer un faux dossier `<uuid>.drift-x`, lancer le script sur ce
chemin → seuil relu à 100, pickle présent, `.drift-*` supprimé, sauvegarde créée.
Si le pickle ne se matérialise pas sur une collection minuscule, ajuster le test (nombre
d'entrées) plutôt que le script, et le noter.

## Interdit

- **Ne jamais exécuter le script sur `~/.mempalace/palace`** : c'est Nico qui le lance au run live.
- Pas de modification du fork `mempalace-fork`, ni de `memory/writer.py`, ni du bridge.

## Critère de fin

`pytest tests/ -q` vert ; script prêt à être lancé par Nico (tronçon 03).
