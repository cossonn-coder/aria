# Couches mémoire ARIA — état détaillé

Ce document tient l'archéologie des collections ChromaDB du palace :
compteurs d'entrées, dettes de migration, commits de résolution.
Il complète le résumé compact présent dans `CLAUDE.md` et le layout
filesystem documenté dans `docs/architecture/chromadb_palace.md`.

## État post-sprint-4

- `aria_episodic` : interactions, images reçues, images générées.
  Types `interaction|image_input|image_generated`. ~408 entrées.
  Indexé par `intent_id` (room).
- `aria_semantic` : faits stables sur l'utilisateur (allergies,
  localisation, préférences). 0 caller prod actuellement — couche
  d'infrastructure prête mais pas alimentée par le pipeline normal.
  Cf. dette #17 (bloc-note explicite).
- `aria_classifier` : cache du classifier d'opérations.
  ~199 entrées, fonctionnellement cassé depuis sa création
  (mismatch document indexé vs query) — résolu sprint 5
  (commit b0aaee5, dette #20 close).
- `aria_intentual` : réservé intents sérialisés. Pas implémenté.
- `aria` (legacy) : 0 entrée dans `mempalace_drawers`. 32 entrées
  résiduelles dans `mempalace_closets` non migrées (hors scope
  sprint 4, à arbitrer si un usage justifie leur migration).

## Voir aussi

Layout filesystem du palace, backend chromadb-rust et mécanismes de
quarantine (`.drift-*` / `.corrupt-*`) :
voir `docs/architecture/chromadb_palace.md`.
