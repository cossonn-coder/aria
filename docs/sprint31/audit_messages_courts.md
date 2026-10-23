# Sprint 31 — audit : messages courts lents (#111, #73 / #86)

Date : 2026-10-23. Code lu sur `main` (`60288c5`, tag `sprint-30`).
Sources live : `journalctl -u aria` (lisible sans sudo) et `chroma.sqlite3` en lecture seule.

## 1. Symptôme (run live sprint 30)

| Message | Réception → réponse | Détail |
|---|---|---|
| `salut` 19:14:11 (1er après redémarrage, après analyse) | 17 s | chargement mpnet 1 s, **deux** 413 Groq |
| `salut` 23:32:03 (1er après redémarrage) | 12 s | chargement mpnet 6 s, un 413 Groq |
| `salut` 18:49:40 | 6 s | un 413 Groq |
| `salut` 18:55:46 | 5 s | un 413 Groq |

Au-delà de 10 s, le message « ⏳ Je travaille dessus, ça peut prendre jusqu'à 2 minutes. »
part (`WAIT_NOTICE_SECONDS = 10`, `interfaces/telegram_interface.py:49`).

## 2. Le message d'attente (#111)

`interfaces/telegram_interface.py:163-197` : `_handle_with_waiting` lance `_keep_typing`
(« écrit… » toutes les 4 s) et `_notice_after_delay` (sommeil 10 s puis un message). Les
deux tâches sont annulées quand `kernel.handle_event` rend la main. L'interface ne sait pas
quelle opération tourne : l'événement n'est classé qu'ensuite, dans le kernel.

Durées connues : analyse de partie 50-110 s (run live 13 sprint 29) ; 41-82 s au run live 30.
Messages courts : 5-17 s [n=4, run live 30].

## 3. Pourquoi Groq répond 413 (#73 / #86)

### 3.1 Chaîne CHAT

`llm/llm_router.py:40-96` : CHAT, PLANNING, REFLECTION = groq ×3 (même modèle, 3 clés) →
DeepSeek → Anthropic. REASONING et DIGEST excluent déjà Groq. Palier Groq : ITPM 7000.

`complete()` (`llm/llm_router.py:185-260`) : un 413 Groq pose `groq_too_large` et saute
`groq_2` / `groq_3` (sprint 25, piste A), puis `time.sleep(1)` avant l'entrée suivante.
Coût par appel concerné : aller-retour Groq + 1 s de sommeil, avant que DeepSeek démarre.

### 3.2 Ce qui grossit la requête

L'analyse de partie écrit en historique (`aria_conversation`) le **bloc enrichi** Stockfish
comme tour `user` (`execution/routers/llm_router.py:288-296`, `write_conversation_turn(…,
"user", message)`). Mesure sur le palace prod (sqlite, lecture seule, 20 derniers messages) :

| Tour `user` | Taille |
|---|---|
| analyse AaronDias16 | 9 107 car. |
| analyse Falestinhurra | 9 616 car. |
| analyse « Adversaire » | 8 453 car. |
| analyse Mu7saad | 9 621 car. |
| analyse YouGotMyRook | 4 969 car. |
| `salut`, questions | 5-47 car. |

Les réponses d'analyse font 770-1 400 car. Soit ≈ 47 000 car. dans la fenêtre de 20 messages.

Deux appels CHAT portent ce poids sur un message ordinaire :
1. **AnalystAgent** (`agents/analyst_agent.py:37-49`) : system + **tout** l'historique
   (`max_history_turns = 10` → 20 messages, `config.py:72`) + message.
2. **Namer d'intent** (`execution/routers/llm_router.py:180-189`) : reçoit
   `previous_message` = dernier tour `user`, donc un bloc enrichi de 9 000 car. juste après
   une analyse. C'est le second 413 de 19:14.

Le classifier (`cognition/cognitive_classifier.py`) ne lit l'historique que pour la reprise
d'URL (n=2) : il passe sur Groq (vu « groq a répondu » avant chaque 413).

Conséquence : pendant les 10 tours qui suivent une analyse, chaque message ordinaire
paie un ou deux allers-retours Groq perdus + 1 s de sommeil chacun.

### 3.3 Pistes déjà jugées (sprint 25, `docs/sprint25/audit_groq_413.md`)

- B. Budget tokens sur l'historique : **écartée par Nico** (DeepSeek perdrait du contexte).
- C. Stocker le message brut au lieu de l'enrichi : **écartée** (casse la reprise de lecture
  d'URL, et les questions de suivi sur une partie lisent ce bloc).

La taille exacte refusée par Groq est inconnue : le corps de l'erreur est tronqué à 200 car.
juste avant le nombre (« Requested 1… »).

## 4. Pistes

### #73 / #86

| Piste | Effet | Coût |
|---|---|---|
| **D. Saut préventif de Groq** : dans `complete()`, si la taille totale du payload (prompt ou somme des `content`) dépasse un seuil en caractères, sauter les entrées `groq*` sans appel HTTP, comme après un 413 | plus d'aller-retour perdu ni de sommeil ; DeepSeek garde tout l'historique ; Groq garde les petites requêtes (classifier, conversations légères) | ~10 lignes dans `llm/llm_router.py` ; seuil estimé (car./token ≈ 2,5-4 selon PGN ou français) ; une sous-estimation retombe sur le 413 actuel, sans régression |
| E. Retirer Groq de CHAT | idem D pour les gros appels | classifier et namer perdent Groq sur les petits messages aussi |

Règles inviolables : D touche `llm/llm_router.py` seul ; aucune lecture ni écriture mémoire.

### #111

| Piste | Effet | Coût |
|---|---|---|
| **a. Seuil à 20 s** | aucun message court mesuré ne l'atteint (max 17 s, et moins avec D) ; l'analyse garde son ⏳ (≥ 41 s) | une constante |
| b. ⏳ réservé à l'analyse de partie | exact | l'interface devrait reconnaître un PGN avant le classifier (logique en double) ou recevoir un signal du kernel : plus de code, couches touchées |
| c. Préchargement du modèle d'embedding au démarrage | retire 1-6 s au 1er message après redémarrage | touche le démarrage ; 1 message par redémarrage |

## 5. Hors périmètre (constats)

- #74 « Prochaine action : … » : la 3e occurrence (19:14:27) suit une analyse ; le LLM a
  20 messages dont un bloc enrichi plein de consignes. Corrélation, pas de preuve.
- Troncature à 200 car. du corps d'erreur HTTP : cache la taille refusée.
