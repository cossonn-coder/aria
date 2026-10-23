# Sprint 33 — audit : historique trop lourd sur un `salut` (#37 / #38)

Date : 2026-10-23. Code au commit `15969bd` (tag `sprint-32`).
Sources : code lu intégralement (chemins ci-dessous), `journalctl -u aria` du run live 32,
lecture **sqlite en lecture seule** (`mode=ro`) du palace prod, sans ouvrir de client
chromadb (risque de drift HNSW, #105).

## 1. Symptôme (run live sprint 32, 11:08)

```
11:08:00 conversation_history loaded key=6895898630 messages=20
11:08:02 [LLM] provider groq skipped (payload 36813 chars > 12000)
11:08:04 [LLM] deepseek (deepseek-flash) a répondu.
11:08:06 pipeline done → 29 chars          ← « Salut. On enchaîne sur quoi ? »
```

36 813 car. envoyés pour répondre 29 car. à `salut`. Groq est sauté (seuil sprint 31,
`GROQ_MAX_PAYLOAD_CHARS = 12_000`, `llm/llm_router.py:104`), donc DeepSeek répond.

## 2. Chemin de données

### 2.a Lecture : `execution/routers/llm_router.py:118-141` (étape 1b)

```python
conversation_key = str(metadata.get("chat_id", "default"))
if metadata.get("skip_history"):
    conversation_history = []
    log.info("conversation_history SKIPPED reason=skip_history")
else:
    conversation_history = self.mempalace_bridge.load_conversation_history(
        conversation_key, n=config.max_history_turns * 2,
    )
```

- `config.max_history_turns = 10` (`config.py:72`) → 20 messages.
- `MempalaceBridge.load_conversation_history` (`memory/mempalace_bridge.py:213-272`) : filtre
  `wing=aria_conversation, room=<chat_id>`, tri Python par timestamp, `turns[-n:]`. Aucune
  limite de taille : les contenus sont rendus tels qu'ils ont été écrits.

### 2.b Consommation : `agents/analyst_agent.py:37-42`

```python
history = ctx.extra.get("conversation_history", [])
messages = (
    [{"role": "system", "content": self._build_system_prompt(ctx)}]
    + [{"role": h["role"], "content": h["content"]} for h in history]
    + [{"role": "user", "content": ctx.message}]
)
```

L'historique part tel quel, en messages natifs. Autre lecteur de `conversation_history`
dans `llm_router.py` : le namer (`llm_router.py:183-184`), qui ne lit que le dernier tour user.

### 2.c Écriture : `llm_router.py:281-288`

```python
write_conversation_turn(conversation_key, "user", message)
write_conversation_turn(conversation_key, "assistant", result)
```

`message` est le **contenu reçu par `LLMExecutionRouter.execute`**, c'est-à-dire le message
**enrichi** quand l'appel vient d'un router spécialisé :

| Caller | Contenu enrichi écrit en tour `user` | Drapeau |
|---|---|---|
| `chess_router.py:619` | ancre + faits Stockfish/Maia en français + PGN original (`_build_enriched`) | `skip_history` (l'analyse ne LIT pas l'historique, mais l'échange y est ÉCRIT) |
| `web_router.py:117` | `[Résultats web …]` + extraits + consigne + message | `skip_intent` |
| `web_router.py:240` | `[Synthèse de la page …]` + marqueur `URL_PARTIAL_MARKER` + consigne + message | `skip_intent` |
| `image_router.py:214` | `[Analyse visuelle : …]` + consignes + légende | `skip_intent` |

### 2.d Lecteurs qui DÉPENDENT du contenu enrichi stocké

- `web_router._handle_url_read` (`web_router.py:163-167`) : reprise « lis la suite » via
  `_PARTIAL_RE` sur le dernier tour `user` (lecture directe `load_conversation_history(n=2)`).
- `web_router._build_query` (`web_router.py:134`) : dernier échange (n=2) pour « source ? ».
- `cognition/cognitive_classifier.py:187` : n=2.
- Questions de suivi (échecs, photo, page) : l'analyst voit les faits enrichis dans l'historique.

Ces trois lecteurs directs passent par le bridge, **pas** par l'étape 1b du router : un
plafonnement à l'étape 1b ne les touche pas.

## 3. Mesure (palace prod, sqlite en lecture seule)

Les 20 messages chargés pour le `salut` de 11:08 (du plus récent au plus ancien) :

| Rôle | Car. | Début |
|---|---|---|
| assistant | 1 089 | Partie contre AaronDias16 … Position 1 — |
| **user** | **8 636** | Partie contre AaronDias16 … [Analyse Stockfish |
| assistant | 237 | Oui. AaronDias16 (1539) vs toi (1622) |
| user | 51 | tu te souviens de la partie que je viens d'envoyer? |
| assistant | 86 | Prochaine action : … (avant sprint 32) |
| user | 5 | salut |
| assistant | 1 116 | Partie contre AaronDias16 … |
| **user** | **8 940** | Partie contre AaronDias16 … [Analyse Stockfish |
| … 8 tours courts (salut / réponses, 5 à 216 car.) | | |
| assistant | 1 415 | Partie contre AaronDias16 … |
| **user** | **9 107** | Partie contre AaronDias16 … [Analyse Stockfish |
| … | | |

- Historique : **31 237 car.**, dont **26 683 (85 %) pour 3 messages user enrichis d'échecs**.
- Reste du payload : 36 813 − 31 237 − 5 = **5 571 car.** (soul 1 466 + user.md 326 +
  bloc `CONTEXTE COGNITIF` + gabarit analyst).
- Sur tout `aria_conversation` (316 tours) : 51 tours > 3 000 car., **tous `user`**, dont
  31 analyses d'échecs (3 056 à 9 621 car.) et quelques résultats web / synthèses de page.
  Aucun tour `assistant` > 3 000 car.

## 4. Diagnostic

1. **Cause** : les routers spécialisés passent un message enrichi (faits moteur, résultats
   web, synthèse de page) à `LLMExecutionRouter`, qui l'écrit comme tour `user`. Relu en
   historique à chaque message suivant, il pèse 3 000-9 600 car. par occurrence, jusqu'à
   ce qu'il sorte de la fenêtre des 20 messages. Deux analyses dans la fenêtre suffisent
   à dépasser 12 000 car.
2. **#37 n'est pas la cause.** #37 dit seulement que `max_history_turns` compte des tours
   alors que l'API compte des messages ; la conversion `× 2` est faite et commentée
   (`llm_router.py:123-124`). C'est une dette de nommage, sans effet sur le volume.
3. **#38 n'est pas la cause.** La section épisodique du `context_block` est bornée
   (budget 2 000 tokens pour tout le bloc, 400 car. par souvenir,
   `cognition/context_builder.py:31,152`) : le doublon existe mais pèse au plus quelques
   milliers de caractères, compris dans les 5 571 car. hors historique.
4. Le drapeau `skip_history` du chess_router protège l'analyse elle-même, pas les messages
   **suivants**.

## 5. Pistes (simulées sur les 20 messages réels de 11:08)

| Piste | Historique | Payload | Groq (≤ 12 000) |
|---|---|---|---|
| Actuel | 31 237 | 36 813 | sauté |
| A. Plafond par message 1 000 car. | 6 934 | 12 510 | sauté (de peu) |
| A'. Plafond par message 1 500 car. | 9 054 | 14 630 | sauté |
| **B. Plafond 1 500 / message + budget total 6 000 car. (du plus récent au plus ancien)** | **5 928** | **11 504** | **répond** |
| C. Dernier échange intact, autres plafonnés 1 500 | — | 21 766 | sauté |
| D. N'écrire que le message original (PGN) en tour `user` côté échecs | dépend du PGN (≈ 1-2 000) | ≈ 12-15 000 | incertain ; casse rien côté web, mais à faire router par router |

- **B** = même idiome que `context_builder` (budget rempli par priorité, ici récence).
  Un seul point de code : l'étape 1b de `llm_router.py`, après la lecture bridge. Le
  bridge reste brut (lecture pure), les lecteurs n=2 (reprise URL, `source ?`, classifier)
  ne sont pas touchés.
- **Coût de B** : une question de suivi juste après une analyse ne voit plus que la tête
  du bloc enrichi (ancre + premières lignes de faits) et la réponse ARIA (≤ 1 500 car.,
  intacte en pratique). Les faits moteur détaillés et le PGN (en fin de bloc) ne sont plus
  dans l'historique. Le contexte épisodique (`retrieve_by_intent` sur `jeux echecs`)
  en garde un extrait de 400 car.
- **C** préserve les suivis d'analyse, mais ne fait pas repasser Groq.
- Le seuil Groq dépend aussi des 5 571 car. hors historique (bloc cognitif variable) : B
  laisse ≈ 500 car. de marge [n=1 cas mesuré].

## 6. Hors scope (dettes à garder)

- #37 (nommage `max_history_turns`) : non traité ; proposer « sans objet pour le volume ».
- #38 (doublon épisodique / conversation) : borné, pas la cause.
- #114 (`actions_history`), #72 (code mort) : inchangés.
- Le contenu enrichi reste écrit en épisodique (`write_interaction`) : borné à 400 car.
  par souvenir à la lecture, pas touché.
