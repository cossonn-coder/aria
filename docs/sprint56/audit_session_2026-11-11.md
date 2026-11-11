# Sprint 56 — Audit de la session Telegram du 2026-11-11 (08:01-08:26) et du 2026-11-10 (19:17-19:19)

Audit avant fix (lecture seule). Sources : transcripts collés par Nico, `journalctl -u aria`
(boot du 2026-11-11 00:27 seulement : le journal antérieur n'est pas lisible), palace prod
lu en direct (`mempalace_drawers`, filtre `wing=aria_episodic, type=chess_game`).

## Constat 1 — Une partie tronquée crée une 2e fiche (doublon)

**Faits.**
- 08:14 : PGN Amateurspoeler complet (`Result "1-0"`, 53 demi-coups) → `chess_game_5d637035095b1e02`, `outcome=win`.
- 08:15 : même partie recollée, coupée au coup 24 (`Result "*"`, 47 demi-coups) → `chess_game_ac268123120a3de5`, `outcome=unknown`.
- Les 47 coups de la 2e fiche sont exactement les 47 premiers de la 1re (vérifié au palace).
- Balayage des 299 fiches [palace prod, 2026-11-11 11:20] : 2 paires « préfixe », les deux avec le même adversaire :
  Amateurspoeler (53 ⊃ 47) et UIALY (`chess_game_65ab47027b3c97cc` 105 ⊃ `chess_game_ed1eca8f1df7568e` 101).
  Le doublon UIALY se voit dans le `/parties` du 10/11 (« contre UIALY (1652) · victoire · Scotch Game » deux fois).

**Cause (code).** `execution/routers/chess_router.py:871` :

```python
def _game_hash(ucis) -> str:
    return hashlib.sha256("".join(ucis).encode()).hexdigest()[:16]
```

L'identité d'une partie est le hash de **tous** ses coups. Un PGN tronqué a donc un autre hash.
`execute` (l. 933) et `_execute_many` (l. 981) ne testent que l'égalité exacte
(`known.get(f"chess_game_{game_hash}")`), puis `_execute_game` (l. 1056) écrit une nouvelle fiche
via `write_chess_game` (`memory/writer.py:141`, upsert sur `chess_game_<hash>`).

**Effets.** `/parties` montre 3 parties au lieu de 2 ; progression, rangs 🏅, 📖 et performance
comptent la partie deux fois (« Aujourd'hui : 1 V — 33 % [1 partie] », « performance 2529 »).

Dette liée : #199 (fiche tronquée luismota32, 76/107, sans fiche complète au palace).

## Constat 2 — L'issue « * » n'est corrigeable par aucun moyen

**Faits.** Tailor4321 : PGN collé avec `Result "*"` et sans `Termination` → `outcome=unknown`
(`chess_coach/summary.py:52` `_outcome` : seul `1-0` / `0-1` / `1/2-1/2` donne une issue).
Nico écrit « gain de BaguetteChaussette sur abandon de l'adversaire » : le message part au
LLM (classifier → pipeline LLM, l. 08:19:23-08:19:38), aucune écriture de fiche.

**Cause.** Aucun chemin d'écriture ne modifie l'issue d'une fiche existante : `writer.py` a
`update_chess_game_opening` et `update_chess_game_accuracy` (scripts de migration), rien pour
`result`/`outcome`. Un renvoi du même PGN est refusé (« déjà envoyée », sauf apport d'horloges, sprint 51).

Note : la 1re version Tailor (08:01) portait `Termination "BaguetteChaussette won because game
was abandoned"` mais **pas d'en-tête `[White]`/`[Black]`** : `detect_pgn`
(`cognition/cognitive_classifier.py:131`) exige un de ces en-têtes, le message est parti au LLM qui a
écrit une « analyse » libre sans moteur (08:01:27, deepseek). Pas de fiche pour cette version.

## Constat 3 — Le LLM affirme des écritures qu'il ne peut pas faire, ou nie un accès qu'il a

**Faits.**
- 08:23 : le LLM invente une 2e partie « Défense Sicilienne, gain par mat, 91 % ».
- 08:25 : « Je corrige ma mémoire immédiatement » ; 08:26 : « C'est corrigé… La base est propre. »
  Journal : `memory_write OK wing=aria_episodic` = écriture de l'**interaction** (souvenir de conversation),
  pas de la fiche. `/parties` à 08:26 : inchangé.
- 10/11 19:18-19:19 : « Je n'ai pas accès au palace ni à tes 47 dernières parties », alors que
  `/parties` venait de les lister.

- 10/11 16:44 : « j'ai fait 3 défaites d'affilée, explique-moi pourquoi » → le LLM annonce un
  « pattern commun » sur trois parties mais n'en cite que **deux** (obeikfad, Mariqn9999) ; la 3e
  (sojdjpao d'après l'ordre de `/parties`, non vérifié) est absente. Récit approximatif (« tu recules
  ton fou (Qe2, g3) »). Lecture : il ne voit que les fiches que la recherche vectorielle lui remonte
  (top-k), et comble le reste.

- 10/11 14:16-14:22 : question de suivi sur une position (« qu'est-ce que je fais après
  l'échange ? ») → le LLM calcule seul, sans moteur ni échiquier : variante fausse (« tu récupères
  la tour a8 »), corrigée par Nico ; puis « Position 3 / 4 » réécrites avec des coups inventés
  (« 43.Ree8 attaque le fou c8 et la tour a8 », « 6.Ng5 que tu avais en mémoire », coup noir
  43...Kc5 attribué à Nico en « position 4 »). Les questions de suivi sur une position ne
  passent par aucun moteur (recoupe #82, #84, #92).
- Même échange : « c'est ça le niveau d'analyse que j'attends » → « Noté. Je vais pousser les
  lignes tactiques jusqu'au bout. » Promesse durable sans aucun stockage : la consigne n'existe
  que dans l'historique de conversation (constat 4).

**Cause (code).**
- Le LLM conversationnel ne reçoit **jamais** les fiches : `load_chess_games` n'a que des callers
  déterministes (`chess_router`, `/parties` `/ouvertures` dans `telegram_interface.py:447,458`,
  échiquier). Il reçoit `soul.md` + `user.md` + top-k souvenirs vectoriels
  (`execution/routers/llm_router.py:144-145`) + historique de conversation.
- Rien dans le prompt système (`llm/llm_router.py:295` `build_base_system_prompt` = `_SOUL` + `_USER`)
  ne dit au LLM ce qu'il peut ou ne peut pas faire. Il improvise dans les deux sens
  (« c'est corrigé » / « pas accès »). Règle d'archi 3 respectée côté code (le LLM n'écrit rien) :
  le mensonge est verbal.
- Dettes liées : #82 (questions d'échecs sans PGN → LLM seul, hallucinations).

## Constat 4 — Aucun moyen de donner une consigne durable à Aria

- `user.md` (6 lignes) et `soul.md` sont lus **au démarrage** (`llm/llm_router.py:25-26`) ; ni
  commande ni chemin pour les enrichir depuis Telegram.
- `aria_semantic` / `writer.write_semantic_fact` (`memory/writer.py:243`) existe, 0 caller prod (dette #17).
- Une consigne dite en conversation ne survit que dans `aria_conversation` (fenêtre glissante,
  plafonnée) et dans un souvenir épisodique remonté au hasard de la distance vectorielle.

## Constat 5 (adjacent, palace prod) — Recherche vectorielle en panne

Chaque message LLM du 2026-11-11 logue :

```
retrieve_memories error wing=aria_classifier room=None: Search error: Error executing plan: Internal error: Error finding id
retrieve_memories error wing=aria_episodic room=None: ... Error finding id
retrieve_memories error wing=aria_episodic room=documents: ... Error finding id
```

37 occurrences du 2026-11-11 00:27 à 11:20 [journal du boot courant seul, début réel inconnu],
encore présentes à 11 h. À 08:22:06 le backend a mis en quarantaine
`64ac86cd-….drift-20261111-082206` (« sqlite 144717s newer than HNSW »). 144 717 s ≈ 40 h avant :
proche de la suppression de la fiche « Ami » (commit `58aa7d5`, 2026-11-09 16:06), **hypothèse non vérifiée**.

Effet : Aria répond sans aucun souvenir épisodique ni cache du classifieur — terrain favorable au
constat 3. Lectures par filtre de métadonnées (fiches, conversation) non touchées.
Recoupe #31/#105/#142 (drift HNSW).

## Constat 6 — Le LLM promet des fonctionnalités qui demandent du code

10/11 13:04-13:07 : Nico demande une alerte « adversaire suspect » dans les bilans. Le LLM
répond « Dès maintenant, dans chaque bilan de partie, je vais ajouter une ligne Alerte
adversaire », fixe des seuils (> 95 % et Elo < 1800 ; > 90 % et Elo < 1600), Nico les ajuste
(au-delà de 20 coups ; une précision haute sur beaucoup de coups pèse plus), le LLM conclut
« C'est noté. Je l'appliquerai dès le prochain bilan. »

Rien n'est stocké, et les lignes 🎯 / 🏅 / ⏱️ du bilan sont écrites par le code
(`chess_router.py`, `chess_coach/summary.py`) : aucune consigne au LLM ne peut y ajouter une ligne
calculée de façon fiable. Deux natures de « consigne » à distinguer :
- consigne de comportement (ton, profondeur, style) → stockable et injectable dans le prompt ;
- demande de fonctionnalité (nouvelle ligne calculée, nouveau seuil) → du code, donc un sprint.
Le LLM ne fait pas la différence et promet les deux.

## Constat 5 — diagnostic (2026-11-11 11:40, lecture seule, copie sqlite au scratchpad)

**Cause racine établie : faux positif du fork, variante « suppressions ».**

| Élément | Valeur |
|---|---|
| Segment VECTOR de `mempalace_drawers` | `64ac86cd-…`, `max_seq_id` = 1701 |
| `embeddings_queue` | seq 1701 → 2078 (378 opérations) : tout ce qui est ≤ 1701 n'existe plus qu'en sqlite |
| Documents (segment METADATA) | 1959 |
| Index mis en quarantaine le **2026-11-09 15:32:56** (`.corrupt-20261109-153256`) | pickle : `dimensionality None`, `total_elements_added` **1619**, `id_to_label` **1608** |
| Index courant (recréé le 11/11 08:22) | 100 places préallouées, `link_lists.bin` vide : seulement la file rejouée |

Code du fork (`mempalace-fork/mempalace/backends/chroma.py:728`, correctif `ecf72132` du sprint 43) :

```python
label_count = len(id_to_label)
if int(total) != label_count or len(label_to_id) != label_count:
    return False          # → index jugé irrécupérable → .corrupt-*
```

`total_elements_added` compte aussi les éléments **supprimés** depuis : 1619 ajoutés, 11
supprimés, 1608 restants. Dès qu'une fiche a été supprimée (`writer.delete_chess_games`, scripts
de rattrapage ; sprint 55 en a supprimé), le prochain process qui ouvre le palace met l'index
sain en quarantaine. 15:32:56 le 09/11 = lancement du script de rattrapage du sprint 55.
chromadb ayant purgé la file jusqu'au seq 1701, les vecteurs antérieurs sont perdus de l'index.

**Effet** : depuis le 2026-11-09 15:32 [≈ 44 h au moment du diagnostic], recherche par le sens
muette sur `aria_episodic`, `aria_conversation` (vectoriel), `aria_classifier`. Lectures par
métadonnées (fiches, historique) intactes, aucune donnée sqlite perdue.

**Le sprint 56 supprime des fiches** (Amateurspoeler-47, UIALY-101) : sans correctif du fork,
la panne se reproduira au premier redémarrage qui suit.

**Réparation proposée** (validée au sprint 43 sur copie : `migrate_embedder.py` mpnet→mpnet,
690/690) : 1) corriger le fork (`total >= label_count`, test) ; 2) arrêt du service, sauvegarde
du palace ; 3) ré-encodage des 1959 documents depuis sqlite ; 4) requêtes sur les 3 wings ;
5) redémarrage, plus de `Error finding id` au journal.
