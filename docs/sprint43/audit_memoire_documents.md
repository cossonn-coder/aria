# Sprint 43 — Audit #137 : document lu oublié après quelques échanges

Date : 2026-10-30. Code audité : `main` à `d374205` (tag `sprint-42`).

## 1. Symptôme (run live sprint 42)

Un document envoyé sur Telegram est lu et synthétisé. Quelques échanges plus
tard, ARIA ne s'en souvient plus. Quelques jours plus tard, il reste introuvable
quand on en parle par le sujet.

## 2. Chemin d'un document reçu, de bout en bout

1. `interfaces/telegram_interface.py` `_handle_document` (l. 254-321) :
   téléchargement dans `config.file_receive_dir` (`received_files/`), nom
   `<file_unique_id>_<nom_sans_espace>`. Un fichier non image et non `.pgn`
   devient un `Event FILE` `{file_path, file_name, caption}`.
2. `cognition/cognitive_engine.py:106` → `CognitiveOperation.FILE_READ`, sans LLM.
3. `core/kernel.py:67` : `FILE_READ` → `web_router`.
4. `execution/routers/web_router.py` `execute` (l. 85-91) → `_read_slice(file_path, 0, caption, metadata)` :
   - `extract_text(path)` → tranche de 100 000 car. max (`_cut_slice`) ;
   - synthèse LLM `DIGEST`, `max_tokens=1000` (≈ 4 000 car. max) ;
   - message enrichi = `[Synthèse du fichier « <nom> » — <chemin> (caractères a-b sur N) :\n<synthèse>]`
     + consigne + légende ;
   - délégation à `LLMExecutionRouter.execute` en `REASONING` avec **`skip_intent: True`**.
5. `execution/routers/llm_router.py` `_run_pipeline` :
   - `skip_intent` → `intent = None` (l. 189-192) ;
   - étape 10 (l. 303-305) : `intent is None` → `memory_write SKIPPED reason=no_intent_resolved` :
     **rien n'est écrit dans `aria_episodic`** ;
   - l. 325-328 : seuls les deux tours (message enrichi + réponse) partent dans
     `aria_conversation` via `write_conversation_turn`.

Même chemin, même `skip_intent`, pour `URL_READ` (page web lue) : une page lue
est oubliée de la même façon.

## 3. Pourquoi l'oubli « après quelques échanges »

L'historique relu à chaque tour (`llm_router.py` l. 168-179) est
`load_conversation_history(chat_id, n=max_history_turns*2)` puis `_trim_history` :

- chaque message coupé à `HISTORY_MESSAGE_MAX_CHARS = 1 500` car. ;
- total borné à `HISTORY_BUDGET_CHARS = 6 000` car., rempli du plus récent au plus ancien.

Le message enrichi (synthèse) n'apporte donc que ses 1 500 premiers caractères,
et sort de la fenêtre dès que les échanges suivants remplissent 6 000 car.
(2 à 4 échanges selon leur longueur). `/oublie` le coupe immédiatement.

## 4. Pourquoi introuvable « par le sens » quelques jours plus tard

Le seul rappel par le sens est `retrieve_memories(message, n=top_k)`
(`llm_router.py:143`), qui interroge **`aria_episodic` uniquement**
(`mempalace_bridge.py:63-122`, seuil `max_distance=0.8`, room `general` exclue).
`aria_conversation` n'est lue que par ordre chronologique
(`load_conversation_history`, filtre metadata pur). Comme rien n'a été écrit en
épisodique (§2.5), aucune requête ne peut retrouver le document.

## 5. Précédent dans le code : la fiche de partie d'échecs

`chess_router.py:624-630` écrit une fiche `write_chess_game(text, game_hash, extra=summary)`
(`memory/writer.py:139-160`) : wing `aria_episodic`, room `chess`, type `chess_game`,
`doc_id = chess_game_<hash>` (renvoyer la même partie remplace la fiche).
L'échange lui-même reste écrit par `LLMExecutionRouter`. Un router qui écrit sa
fiche via `writer.py` est donc un schéma déjà admis (règle 1 respectée : le
point d'écriture unique est `writer.py`).

Les fiches remontent ensuite par `retrieve_memories` comme n'importe quel
souvenir épisodique.

## 6. Injection d'un souvenir dans le prompt : 400 caractères

`cognition/context_builder.py` `_build_episodic_section` : chaque souvenir est
coupé à **`text[:400]`**, dans un budget global de 2 000 tokens estimés
(≈ 8 000 car.) partagé avec le profil et les projets actifs.

Conséquence pour une fiche document : un en-tête « Document « nom » lu le … (fichier …) »
consomme ≈ 120-150 car. ; il reste ≈ 250 car. de synthèse visibles par le LLM.
Assez pour « je me souviens que tu m'as envoyé X sur tel sujet », pas pour
répondre sur le fond.

## 7. Contraintes de l'embedder

Palace : `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
(`~/.mempalace/palace/.mempalace-embedder.json`), `max_seq_length = 128` tokens :
seuls les ≈ 500 premiers caractères d'une fiche comptent pour la recherche par
le sens. La recherche mempalace ajoute un reclassement BM25 (mots-clés : le nom
du fichier aide).

Mesure bac à sable (fiches fictives écrites à la main, pas le palace prod)
[n=6 questions, 2 fiches] — distance cosinus question → fiche :

| Question | article télétravail | notes potager |
|---|---|---|
| tu te souviens de l'article que je t'ai envoyé sur le télétravail ? | 0,611 | 0,760 |
| que disait le document sur le modèle hybride ? | 0,505 | 0,686 |
| c'était quoi déjà le pdf de l'autre jour ? | 0,607 | 0,709 |
| qu'est-ce que je dois planter en octobre d'après mes notes ? | 0,771 | 0,421 |
| résume-moi le fichier sur le jardin | 0,738 | 0,294 |
| salut ça va ? | 0,914 | 0,854 |

Toutes les questions sur le sujet passent sous le seuil 0,8 ; la bonne fiche est
toujours la plus proche. La concurrence avec les autres souvenirs du palace prod
n'est pas mesurée (à observer au run live).

## 8. Constats annexes (hors scope, pour le tableau des dettes)

- Les hits de `search_memories` (mempalace) ne portent pas de champ `type` :
  `retrieve_memories(type_filter=…)` filtrerait tout. Aucun caller prod ne
  l'utilise aujourd'hui.
- Le commentaire d'en-tête de `web_router.py` (« Ce router n'écrit RIEN en
  mémoire ») deviendra faux si la fiche est écrite là : à mettre à jour dans le
  tronçon.

## 9. Pistes

| Piste | Effet | Coût / risque |
|---|---|---|
| **A. Fiche document en `aria_episodic`** (nouvelle `write_document` dans `writer.py`, appelée par `web_router._read_slice` après la synthèse) | retrouvée par le sens, survit à l'historique et à `/oublie` | faible ; nouvelle room dans le palace prod (ajout seul) |
| B. Recherche par le sens dans `aria_conversation` | retrouve aussi les échanges | change la lecture de l'historique pour tout le monde ; contraire à #40 (embeddings jugés inutiles sur cette wing) |
| C. Écrire l'échange en épisodique malgré `skip_intent` | — | touche photos et recherches web ; texte d'échange bruité (consignes) |
| D. Texte intégral découpé en morceaux (RAG) | réponses de détail | lourd (embeddings CPU, volume HNSW, #105), hors calibrage |

Recommandation : **A**, avec un extrait injecté plus long pour les fiches document (§6).
