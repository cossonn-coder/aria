# Sprint 26 — Audit du correctif 05 (suite au run live 04)

Date : 2026-10-19. Code lu : `execution/routers/llm_router.py` (intégral),
`execution/routers/chess_router.py` (intégral), `llm/intent_namer.py` (intégral),
`intent/intent_engine.py` (`apply`), `memory/mempalace_bridge.py`
(`load_conversation_history`, `retrieve_memories`), `agents/analyst_agent.py`,
`cognition/context_builder.py` (`build_context_block`).

## Run live 04 — résultat

| Msg | Verdict | Preuve journalctl |
|---|---|---|
| A | analyse/fiche/images OK, échange NON écrit | `intent SKIPPED reason=namer_aucun` → `memory_write SKIPPED reason=no_intent_resolved` |
| B | idem A ; 3 positions (a) OK ; récit LLM partiellement inventé | idem |
| C | pas de moteur OK ; répond sur la Position 1 de **A** au lieu de B | `memory_write SKIPPED` |
| D | même hash `0d215f56916d8393` OK ; meilleurs coups différents de B (15…g5→Fc7, 17…f4→Fc7) | idem |
| E | conforme, écrit (`intent_name=jeux echecs`) | `memory_write OK` |

Durées d'analyse : 8,1 / 7,1 / 7,0 / 2,1 s [1 run par message]. Groq 413 (ITPM 7000)
sur chaque réponse échecs → fallback deepseek-v4-pro (le saut du sprint 25 marche).

## Bug 1 — échange non écrit en épisodique (contredit Q4)

Chemin : `ChessExecutionRouter.execute` → `LLMExecutionRouter.execute` avec
`content = enriched` (bloc `[Analyse Stockfish …]` + consigne + PGN brut), `metadata`
inchangé. Dans `_run_pipeline` :

1. `intent_engine.resolve(message=enriched, …)` → action `create`/`split` (le namer
   est appelé, donc ce n'est ni attach ni noop).
2. `extract_intent_name(enriched, previous_message=<dernier tour user>, …)` → « aucun ».
3. `skip_apply = True` → `intent = None` → étape 10 : `memory_write SKIPPED`.

Pourquoi « aucun » : le `NAMER_PROMPT` classe « question ponctuelle » en « aucun », et
son exemple `"évalue la position" (précédent : photo d'un échiquier) → aucun` pousse
explicitement tout ce qui est échiquier vers « aucun ». Une analyse de partie ressemble
à une demande ponctuelle. E est passé parce que « je joue les noirs » en tête de PGN
ressemble à un sujet personnel durable → `jeux echecs` créé.

Conséquence : sans intent, rien n'est écrit en `aria_episodic` (seule la fiche
`chess_game` l'est, par le chess_router). Le tour est quand même écrit en
`aria_conversation` (`conversation_write OK`, écrit même sans intent).

Effet de bord à noter : l'intent `jeux echecs` existe désormais ; `resolve` pourrait
rattacher les prochaines parties (attach) sans passer par le namer. Ce n'est pas
garanti (decay, seuils de recall) → pas une correction.

Point d'injection vérifié : `metadata` de l'appel délégué arrive tel quel dans
`_run_pipeline` (déjà utilisé pour `skip_intent`, #51) et est étalé dans
`AgentContext.extra` (`**metadata`, sans effet de bord). `IntentEngine.apply` en
`CREATE` avec `intent_name` fourni cherche d'abord un intent actif du même nom
(`_find_by_name`), puis sémantique (`_find_by_name_semantic`, seuil 0,55), sinon crée.

Correctif possible (déterministe) : le chess_router pose `metadata["intent_name"]`
(nom fixe) ; dans `_run_pipeline`, en `create`/`split`, si ce nom est présent on
l'utilise sans appeler le namer. Alternative : retoucher `NAMER_PROMPT` (dépend du
LLM, non déterministe, touche tous les messages).

## Bug 2 — C répond sur la partie A

Reproduction sur une **copie** du palace (scratchpad, prod non touché) :

- `load_conversation_history(key, n=20)` : tri Python par `timestamp`, `turns[-n:]`.
  Au moment de C, l'historique contient bien, dans l'ordre : …, A (user enrichi +
  réponse « je regarde la position 1 »), B (user enrichi + réponse 3 positions).
  B est le dernier échange avant C. **Pas de bug d'ordre ni de troncature.**
- `AnalystAgent` : `system` (base + CONTEXTE COGNITIF + règles), puis l'historique
  dans l'ordre, puis le message. Aucune troncature côté `llm/llm_router.py`.
- Mémoire globale pour la requête C (`retrieve_memories`, n=8 en REASONING) : parmi
  les hits antérieurs à C, la fiche `chess_game` de B (distance 0,696) est plus proche
  que celle de A (0,750) ; les échanges A/B ne sont pas en épisodique (bug 1). Le
  contexte mémoire ne pousse donc pas vers A [reconstitution approximative : le palace
  a reçu des écritures après C].

Diagnostic : pas de défaut de code identifié. C'est une erreur de lecture du LLM
(deepseek-v4-pro, fallback) sur une référence ambiguë « cette partie » dans un
historique chargé de deux analyses dont l'une (A) parlait exclusivement d'une
« position 1 ». [n=1 occurrence, non reproduite]

Pistes si ça se reproduit : ancrer chaque analyse sur un identifiant lisible (« Partie
contre <adversaire> ») dans le bloc enrichi et en tête de réponse ; ou réduire le bruit
d'historique (blocs enrichis volumineux). Les deux touchent au prompt et à l'historique.

Note technique : la copie à chaud du palace a déclenché la quarantaine d'un segment
HNSW (`.drift-*`) **dans la copie** (sqlite plus récent que l'index). Sans effet sur le
prod ; la copie est supprimée après l'audit.

## Autres constats → dettes

- Récit LLM inventé autour de coups corrects (« tu as perdu ta dame pour une tour »,
  « ta dame h5 attaquée par la dame d3 ») : le bloc enrichi ne donne ni le matériel ni
  les menaces, le LLM les invente.
- Meilleur coup instable entre deux analyses de la même partie (15…g5 vs 15…Fc7) :
  limite de temps/threads du moteur → non-déterminisme [hypothèse non vérifiée].
- 413 Groq systématique sur les requêtes échecs : bloc enrichi + 20 messages
  d'historique (eux-mêmes enrichis) > ITPM 7000.
