# Sprint 25 — audit #73 : Groq 413 / poids de l'historique

Date : 2026-10-16. Code lu au commit `5fc1bdd` (main post sprint 24).

## 1. Symptôme (run live)

Run live 24-02, message C (« tu peux afficher la liste des courses ? ») :

```
18:24:33 intent SKIPPED reason=namer_aucun
18:24:35 [LLM FALLBACK] groq failed: 413 Payload Too Large
18:24:36 [LLM FALLBACK] groq_2 failed: 413 Payload Too Large
18:24:37 [LLM FALLBACK] groq_3 failed: 413 Payload Too Large
18:24:39 [LLM] deepseek (deepseek-flash) a répondu.
```

Même motif au run live 23-03 [n=6], avec une synthèse d'URL dans l'historique.
Ici [n=1], présence d'une synthèse d'URL dans l'historique non vérifiée.

## 2. Cause mesurée : limite ITPM de Groq

Sonde directe (2026-10-16, clé `GROQ_API_KEY`, modèle `qwen/qwen3.8-27b`) :

| Requête | Statut | Corps / en-têtes |
|---|---|---|
| ~10,8k tokens d'entrée, `max_tokens=1500` | 413 | `Request too large … on input tokens per minute (ITPM): Limit 7000, Requested 10812` |
| 18 tokens d'entrée, `max_tokens=1500` | 200 | `x-ratelimit-limit-tokens: 8000` |

- Le 413 n'est pas une taille HTTP : c'est une requête dont **l'entrée seule
  dépasse 7000 tokens** (la limite d'une minute entière). `max_tokens` ne
  compte pas (2e ligne).
- Il est **déterministe** pour une requête donnée : retenter sur `groq_2` et
  `groq_3` (même modèle, même palier gratuit) échoue forcément pareil.
- Le corps de l'erreur (limite, taille demandée) n'est pas logué :
  `log.error("[LLM FALLBACK] %s failed: %s", provider, e)` ne montre que le
  statut httpx (`llm/llm_router.py:232`).

## 3. Composition de la requête REASONING

`AnalystAgent.run` (`agents/analyst_agent.py:37-49`) envoie :

| Bloc | Source | Taille estimée |
|---|---|---|
| system : soul + profil | `soul.md` 1466 car. + `user.md` 326 car. | ~450 tokens |
| system : contexte cognitif | `build_context_block(token_budget=2000)` | ≤ 2000 tokens (estimé `len/4`) |
| system : PROMPT analyst | gabarit fixe | ~100 tokens |
| historique | `load_conversation_history(n=max_history_turns*2)` = **20 messages**, sans budget | non borné |
| message courant | message brut ou enrichi | variable |

Ce qui gonfle l'historique, tous écrits tels quels par
`write_conversation_turn` (`execution/routers/llm_router.py:270-271`) :

- réponses assistant : jusqu'à `max_tokens=1500` chacune (ex. réponse de
  1449 car. juste avant le message C) ;
- messages **enrichis** passés comme `content` au `LLMExecutionRouter` :
  résultats web (`web_router.py:104-115`), synthèse d'URL jusqu'à 1000
  tokens (`web_router.py:225-238`), description de photo (image_router).

Ordre de grandeur : ~2550 tokens de system + 20 messages d'environ 300-500
tokens = 8500-12 500 tokens → au-dessus de 7000 dès que la conversation a
un peu de vécu. Le 413 n'est donc pas lié aux URL : c'est l'état normal
d'une conversation chargée.

## 4. Coût actuel

Chaîne `_text_chain` (`llm/llm_router.py:40-78`) : groq → groq_2 → groq_3 →
deepseek → anthropic, avec `time.sleep(1)` après chaque échec
(`llm_router.py:239-240`). Un 413 coûte donc 3 appels perdus + 3 s de
sommeil : ~4 s entre le premier appel Groq et la réponse DeepSeek au
run live (18:24:35 → 18:24:39). Le cache négatif (`_mark_rate_limited`) ne
vise que les 429 : le 413 se reproduit à chaque message.

Rôles touchés : tous ceux qui empruntent `_text_chain` avec une grosse
entrée. En pratique AnalystAgent (REASONING et autres opérations texte), seul
caller qui envoie l'historique. Le classifier (`n=2`) et le namer sont petits.

## 5. Pistes

| Piste | Effet | Coût / risque |
|---|---|---|
| **A. 413 → sauter les autres entrées Groq** pour cette requête | une seule tentative Groq perdue (~0,5 s + 1 s de sommeil) au lieu de 3 ; DeepSeek garde tout l'historique | ~10 lignes dans `complete()` ; Groq ne répond plus jamais aux conversations chargées |
| **B. Budget tokens sur l'historique** (on garde les messages les plus récents tant que l'estimation tient sous un plafond) | Groq répond à nouveau ; plus de 413 | perte du contexte ancien **pour tous les fournisseurs**, DeepSeek compris (128k de contexte) ; plafond calé sur une estimation `len/4` imprécise |
| C. Stocker le message brut au lieu de l'enrichi | historique plus léger | casse la reprise de lecture d'URL (sprint 23 lit la synthèse dans l'historique) — écartée |

Règles inviolables : A touche `llm/llm_router.py` seul ; B touche le router
d'exécution (lecture via bridge déjà en place) ou l'agent (qui ne lit pas la
mémoire, il tronque seulement ce qu'il reçoit). Aucune ne touche l'écriture
mémoire ni le palace.
