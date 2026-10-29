# Sprint 40 — tronçon 03 : /oublie (marqueur de coupure de la conversation)

Lire d'abord `CLAUDE.md`, `docs/sprint40/00_etat.md`, `docs/sprint40/audit_metacommandes.md` §5,
et `01_socle_reboot.md` (mécanique des commandes). **Palace prod touché** (nouveau type de
document dans `aria_conversation`).

## Objectif

`/oublie` fait repartir ARIA d'une conversation vierge, sans rien supprimer : un marqueur est
écrit, et la lecture de l'historique ignore tout ce qui le précède.

## Fichiers à toucher

| Fichier | Changement |
|---|---|
| `memory/writer.py` | `write_conversation_reset(conversation_key)` : document `"conversation_reset"`, wing `aria_conversation`, room = clé, type `conversation_reset`, `timestamp`, posés après le spread comme `write_conversation_turn` (invariant W4) ; `_validate` |
| `memory/mempalace_bridge.py` | `load_conversation_history` : timestamp du dernier `conversation_reset` de la room → ne garder que les tours **postérieurs**, marqueurs exclus, **puis** les n derniers |
| `interfaces/meta_commands.py`, `interfaces/telegram_interface.py` | `/oublie` : appelle le writer avec `str(chat_id)` (même clé que `llm_router.py:156`), répond « 🧹 Conversation oubliée. Les souvenirs restent. » ; entrée `COMMANDS` ; log `meta_oublie key=<clé>` |
| tests | `tests/memory/test_writer.py`, `tests/memory/test_mempalace_bridge_conversation.py`, test de la commande |

## Comportement attendu

- Tous les lecteurs de l'historique (`llm_router`, `cognitive_classifier`, `web_router`) héritent
  de la coupure sans changement.
- Plusieurs marqueurs : seul le plus récent compte. Aucun marqueur : comportement inchangé.
- Réversible à la main (supprimer le document marqueur) ; rien n'est supprimé par le code.
- Les souvenirs épisodiques (`write_interaction`) ne sont pas touchés.

## Tests (cas nominal)

- Writer : marqueur écrit avec wing / room / type structurels, non surchargeables.
- Bridge : tours avant le marqueur exclus, marqueur exclu, tours après conservés ; `n` appliqué
  après la coupure.

## Hors scope

- Suppression physique (`col.delete`), oubli des souvenirs épisodiques, autres commandes.

## Critère de fin

`pytest tests/ -q` vert ; `grep -n "delete" memory/writer.py` vide.
