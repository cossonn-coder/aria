# Sprint 30 — audit fiabilité de l'analyse (#103, #105)

Date : 2026-10-22. Code lu sur `main` @ `d9f28df`.

## #103 — la boucle du bot est bloquée pendant le traitement

### Chemin réel

`interfaces/telegram_interface.py` `_handle_message` / `_handle_photo` :
```python
async with self.user_locks[user_id]:
    event = Event.create(...)
    result = await self.kernel.handle_event(event)
await self.send(chat_id, result)
```
`core/kernel.py:150` `AriaKernel.handle_event` est `async` mais n'attend rien :
```python
cognitive_result = self.cognitive_engine.classify(event)          # synchrone (LLM possible)
...
exec_result = self.execution_dispatcher.dispatch(exec_op)         # synchrone
return self._normalize(exec_result)
```
Tout le traitement (classification, Stockfish, Maia/torch, LLM, chromadb) tourne donc
dans la boucle asyncio de PTB : pendant ce temps PTB ne reçoit rien et n'envoie rien.

Aucun `asyncio` / `threading` / `get_event_loop` dans le code métier (grep hors tests) :
déporter `classify` et `dispatch` dans un thread (`asyncio.to_thread`) ne heurte rien.
Le verrou par `user_id` continue de sérialiser les messages d'un même utilisateur.

### Durées mesurées (run live 13, 2026-10-22, journalctl)

| Partie | Réception | Fin `chess_router` | Boucle bloquée |
|---|---|---|---|
| 1 | 17:20:24 | 17:22:06 | ~102 s |
| 2 | 17:23:39 | 17:25:10 | ~91 s |
| 3 | 17:25:13 | 17:26:18 | ~65 s |
| 4 | 17:26:21 | 17:28:24 | ~123 s |

### Ce que le blocage coûte aujourd'hui (constaté)

- Aucun retour visible pendant 1 à 2 min : pas d'indicateur « écrit… », Nico ne sait pas
  si le message est pris. Aucun `send_chat_action` dans le code.
- Échecs d'envoi `TimedOut` (3 tentatives épuisées) : 3 occurrences, toutes le 2026-10-20
  14:28 / 14:41 / 14:42, chacune juste après un traitement long (47 s, 46 s, 27 s)
  [n=3, une seule après-midi]. Les 4 analyses du 22 (65-123 s) n'en ont produit aucune.
  Lien causal blocage → TimedOut **non démontré**.
- Un second message envoyé pendant l'analyse : il n'est lu qu'à la fin. Avec le blocage levé,
  il serait lu tout de suite mais attendrait le verrou : **même effet visible** pour Nico.

Conclusion : lever le blocage seul ne change rien de visible. Le gain visible vient de ce
que le déblocage permet : un indicateur « écrit… » tenu pendant tout le traitement.

## #105 — quarantaine HNSW à chaque démarrage

### Constat

- Le palace prod (`~/.mempalace/palace`) n'a qu'une collection avec des données :
  `mempalace_drawers`, 475 entrées (toutes les wings ARIA y vivent). Segment VECTOR
  `dba15bea…`.
- Métadonnées de la collection : `hnsw:sync_threshold = 50000`, `hnsw:batch_size = 50000`
  (posées par mempalace, `mempalace-fork/mempalace/backends/chroma.py:144-147`,
  garde-fou contre le gonflement de `link_lists.bin` sur les mines de dizaines de milliers
  d'entrées).
- 475 < 50 000 : l'index HNSW n'est jamais persisté complètement. Le dossier actuel n'a pas
  d'`index_metadata.pickle` (`data_level0.bin` 321 Ko, `link_lists.bin` 0 octet).
- `embeddings_queue` : 510 lignes, jamais purgé (purge après persistance) : chromadb
  rejoue tout le journal à chaque ouverture.
- `quarantine_stale_hnsw` (`chroma.py:238-335`) : sqlite plus récent de ≥ 300 s **et**
  pickle absent → renommage `.drift-<horodatage>`. Donc quarantaine au premier accès de
  chaque process dès que la dernière écriture date de plus de 5 min.
- 13 dossiers `.drift-*` depuis le 2026-10-15, 4,2 Mo au total.

### Ce que ça coûte aujourd'hui

- Un WARNING par démarrage, 4,2 Mo de dossiers morts qui s'accumulent.
- Pas de perte de données constatée : sqlite est la source de vérité, l'index est
  reconstruit depuis le journal. Exactitude des recherches après reconstruction **non mesurée**.
- Le journal non purgé grossit avec chaque écriture (coût de démarrage proportionnel,
  négligeable à 510 lignes).

### Piste de correction

`collection.modify(configuration={"hnsw": {"sync_threshold": …, "batch_size": …}})`
(chromadb 1.5.x, cité par le commentaire `chroma.py:138-141`) avec un seuil inférieur au
volume réel (ex. 100) : l'index est persisté toutes les 100 écritures, le pickle existe,
`_segment_appears_healthy` passe → plus de quarantaine (le cas « flush-lag » est déjà
prévu, log INFO). **Touche le palace prod** (exception au calibrage faible). Où poser cet
appel (script one-shot vs. code ARIA vs. fork) : à arbitrer, la règle 1 (écriture via
`memory/writer.py`) vise les écritures de données, pas la configuration.

### Vérification du correctif sur copie (scratchpad, 2026-10-22)

Copie de `~/.mempalace/palace` sans les `.drift-*`, chromadb 1.5.5 :
1. `col.modify(configuration={"hnsw": {"sync_threshold": 100, "batch_size": 100}})` : OK,
   persisté (relu à 100 par un nouveau process, et intact après `mempalace.palace.get_collection`).
   Les métadonnées héritées `hnsw:sync_threshold = 50000` restent dans `collection_metadata`
   mais ne sont plus celles appliquées.
2. Le process qui a fait `modify` ne persiste pas forcément l'index tout de suite (3 ajouts
   sans pickle au premier essai, pickle dès le 1er ajout au second).
3. **Process suivant** : ouverture + une requête → `index_metadata.pickle` écrit,
   `embeddings_queue` purgé (510 → 1 ligne), 475 entrées, requête OK.
4. `quarantine_stale_hnsw(copie, stale_seconds=0)` → `[]` (log INFO « flush-lag, not corruption »).

Conséquence pour le script : après `modify`, provoquer l'ouverture par un nouveau process
(ou équivalent) et vérifier la présence du pickle avant de rendre la main, sinon la
quarantaine frappera au prochain démarrage du service (sqlite modifié par `modify`).
