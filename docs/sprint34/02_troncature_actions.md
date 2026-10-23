# Tronçon 02 — tronquer `actions_history` à la sauvegarde (#114)

Lire d'abord : `CLAUDE.md`, `docs/sprint34/00_etat.md`. Détail : `audit_rangement.md` §2.

## Objectif

`~/.aria/intents.json` pèse 344 Ko, dont 95 % de messages entiers stockés dans
`actions_history` (bloc enrichi d'analyse ≈ 9 000 car. à chaque partie). Plus aucun lecteur
prod n'en lit le contenu (le tronçon 01 a supprimé executor). On borne chaque action à
**100 caractères au moment de l'écriture disque**, dans `save_intents` : le fichier existant
redescend dès la première sauvegarde, sans migration.

## Fichier

`intent/intent_store.py`, fonction `save_intents` : la valeur `"actions_history"` devient la
liste des actions coupées à 100 car. (`a[:100]`), même idiome que
`created_from_message:{message[:100]}` dans `intent_engine.py`. Une constante de module
(`ACTION_MAX_CHARS = 100`) avec un commentaire français d'une ou deux lignes (pourquoi :
#114, aucun lecteur du contenu, seul le nombre d'entrées sert aux scripts).

Ne pas modifier l'objet `Intent` en mémoire (`intent.actions_history` reste tel quel) : on
tronque la copie sérialisée. Pas de suffixe, pas de plafond sur le nombre d'entrées.

## Test (cas nominal)

Nouveau fichier `tests/intent/test_intent_store.py` : un `Intent` dont `actions_history`
contient une action de 9 000 car. et une courte ; `save_intents({intent.id: intent})` puis
lecture JSON de `intent_store.STORE_PATH` → la longue fait 100 car., la courte est intacte,
2 entrées. La fixture autouse `isolate_storage` (`tests/conftest.py:95-101`) redirige déjà
`STORE_PATH` vers `tmp_path` : relire `intent_store.STORE_PATH` au moment du test (attribut
de module), ne jamais écrire dans `~/.aria/`. Pas de `mkdir` à prévoir : `save_intents` le
fait.

## Hors scope (ne PAS faire)

- `Intent.add_action`, `intent_engine.py` : ne pas toucher.
- `load_intents` (dont son `print()` ligne 44) : ne pas toucher, dette.
- Pas de script de migration, pas de modification manuelle de `~/.aria/intents.json`.
- `intent_compression_engine.py` (property `actions` affectée) : dette, ne pas toucher.

## Critère de fin

- Test ajouté vert ; `pytest tests/ -q` vert (référence : nombre après tronçon 01, + 1).
