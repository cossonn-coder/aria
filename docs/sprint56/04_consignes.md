# Sprint 56 — Tronçon 04 : consignes durables (`/consigne`) et règles d'honnêteté

À lire d'abord : `CLAUDE.md`, `docs/sprint56/00_etat.md`. Diagnostic : audit, constats 3, 4 et 6.

## Objectif

1. Nico donne à Aria des consignes qui survivent aux conversations et aux redémarrages.
2. Le LLM reçoit, à chaque réponse, des règles fixes qui l'empêchent de prétendre avoir agi
   (« c'est corrigé », « noté », « dès le prochain bilan ») ou de calculer des variantes sans moteur.

## Commandes (Telegram, sans LLM)

- `/consigne <texte>` → enregistre ; réponse `📌 Consigne 3 enregistrée : <texte>`.
- `/consignes` → liste numérotée dans l'ordre d'enregistrement (`1. …`), ou `Aucune consigne.`
- `/consigne retire <N>` → supprime la N-ième de la liste ; réponse `🗑️ Consigne <N> retirée : <texte>`.
  N invalide : `Pas de consigne <N>. Liste : /consignes`.
- `/consigne` seul → rappel de la syntaxe.

Logs : `meta_command name=consigne|consignes`, `meta_consigne add id=…` / `remove id=…`.

Câblage : `COMMANDS["consigne"]` et `COMMANDS["consignes"]` dans `interfaces/meta_commands.py`,
`_cmd_consigne` / `_cmd_consignes` dans `interfaces/telegram_interface.py` (enregistrement auto,
l. 167), même patron que `/oublie` (l. 467) : lecture par le bridge, écriture par `memory.writer`,
textes et analyse des arguments dans `meta_commands.py`.

## Stockage (règles 1 et 2)

- `memory/writer.py` : `write_consigne(text)` → wing `aria_semantic`, room `consignes`,
  type `consigne`, `timestamp`, `source="telegram"`, doc_id `consigne_<uuid8>` ; `delete_consigne(doc_id)`.
  Wing / room / type posés après tout `extra` (invariant W4), comme `write_semantic_fact` (l. 243).
- `memory/mempalace_bridge.py` : `load_consignes()` → lecture **par métadonnées** (pas vectorielle),
  sur le modèle de `load_chess_games` (l. 325) : filtre `wing=aria_semantic` + `type=consigne`,
  tri par `timestamp` croissant, `[{"id", "text", "timestamp"}]` (le texte vient de `documents` :
  vérifier que le `get_by_metadata` injecté les renvoie, sinon passer `include`).

Note : `retrieve_semantic` (recherche vectorielle de toute la wing, appelée par
`cognition/context_builder.py:73`) pourra aussi remonter des consignes dans « [Profil utilisateur
stable] ». Doublon accepté, ne pas modifier `context_builder` pour ça.

## Injection dans le prompt (règle 3)

Dans `execution/routers/llm_router.py` `_run_pipeline`, juste après `build_context_block`
(l. 263-270) : le router lit `self.mempalace_bridge.load_consignes()` et **préfixe** le
`context_block` par deux sections, hors budget de tokens du context builder :

```
[Règles d'Aria — fixées par le code]
- Tu ne peux ni écrire, ni corriger, ni supprimer quoi que ce soit dans ta mémoire ou dans les fiches de parties. Ne dis jamais « c'est corrigé », « je corrige ma mémoire », « c'est enregistré ».
- Pour corriger le résultat d'une partie, Nico tape : /issue <adversaire> victoire|nulle|défaite.
- Pour qu'une consigne dure, Nico tape : /consigne <texte>. Ne réponds jamais « noté » ou « je le ferai désormais » sans le lui indiquer.
- Une nouvelle fonction (ligne de bilan, alerte, calcul) demande du code : dis-le, ne promets pas de la faire.
- Sans analyse moteur fournie dans le contexte, ne calcule pas de variante d'échecs et n'affirme pas qu'un coup gagne du matériel : dis que tu ne peux pas le vérifier et propose de renvoyer la partie.
- Si une donnée manque dans le contexte, dis-le au lieu de l'inventer.

[Consignes de Nico]
1. …
```

La section consignes est omise s'il n'y en a pas. Le texte des règles est une constante nommée
(commentaire : sprint 56, constats 3 à 6 de l'audit). Ces sections passent par le `context_block`
déjà lu par AnalystAgent (`agents/analyst_agent.py:55-63`) : le **prompt AnalystAgent n'est pas
modifié**. Elles s'appliquent à toutes les réponses LLM, bilan de partie compris (chemin
`chess_router` → `llm_execution_router`, intent forcé).

## Fichiers à toucher

- `memory/writer.py`, `memory/mempalace_bridge.py`, `execution/routers/llm_router.py`,
  `interfaces/meta_commands.py`, `interfaces/telegram_interface.py`.
- Tests : writer, bridge, `tests/execution/test_llm_execution_router.py`, meta_commands.

## Tests (cas nominal)

- `write_consigne` : wing/room/type structurels.
- `load_consignes` : filtre et tri.
- Router : le `context_block` transmis à l'agent commence par les règles et contient la consigne.
- Analyse des arguments `/consigne retire 2` et textes de réponse.
- `pytest tests/ -q` vert, dont `tests/agents/test_analyst_prompt_guard.py`.

## Hors-scope (ne PAS faire)

- Pas de détection automatique de consignes dans la conversation.
- Pas de modification de `soul.md`, `user.md`, ni du `PROMPT` de l'AnalystAgent.
- Pas de câblage de `write_semantic_fact` (dette #17).

## Critère de fin

Tests verts.
