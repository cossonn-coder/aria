# Sprint 58 — audit #211 : contexte échecs trop lourd

Date : 2026-11-12. Code lu sur `main` (`1ce1e94`, tag `sprint-57`).

## 1. Chemin de code

`execution/routers/llm_router.py` (router d'exécution), étape 4b :

```python
consignes = self.mempalace_bridge.load_consignes()
head = _rules_block(consignes)
if not metadata.get("skip_history"):
    games = self.mempalace_bridge.load_chess_games()
    if games and mentions_chess_games(message, [g.get("opponent") for g in games]):
        n = requested_games_count(message)
        head += "\n\n" + games_context_section(games, n)
        head += "\n\n" + games_stats_section(games)
        log.info("chess_games_context n=%d total=%d", ...)
context_block = head + "\n\n" + context_block
```

- `mentions_chess_games` : regex `_CHESS_WORDS` = `parties?|echecs|games?|defaites?|victoires?|nulles?|adversaires?|ouvertures?`
  sur le message sans accents, **ou** pseudo d'un adversaire connu (303 pseudos distincts).
- `requested_games_count` : « N dernières » → N, « toutes » → toutes, sinon 20.
- `games_context_section` / `games_stats_section` : `chess_coach/summary.py:349` et `:361`.
- `load_chess_games` (`memory/mempalace_bridge.py:325`) : appelé à **chaque** message non-analyse,
  avant la détection.

Saut groq : `llm/llm_router.py:254`, `GROQ_MAX_PAYLOAD_CHARS = 12_000` (sprint 31, palier ITPM
7 000 tokens). Concerne la chaîne des rôles CHAT et PLANNING : groq ×3 → deepseek-flash → Haiku.
Le rôle REASONING exclut déjà groq (deepseek-v4-pro).

## 2. Mesures (palace prod, lecture seule, 2026-11-12)

| Élément | Taille |
|---|---|
| Fiches de parties | 313 |
| Règles d'Aria (0 consigne) | 851 car. |
| Liste des 20 parties | 2 293 car. |
| Liste de toutes les parties (« toutes ») | 34 745 car. |
| Section statistiques (31 ouvertures ≥ 3 parties) | 2 118 car. |
| **Ajout échecs total (défaut)** | **≈ 4 400 car.** |
| `soul.md` + `user.md` | 1 792 car. |
| `context_block` (budget du builder) | ≤ 8 000 car. [2 000 tokens estimés × 4] |
| Historique (`HISTORY_BUDGET_CHARS`) | ≤ 6 000 car. |
| `load_chess_games` | 0,3 s à chaud [n=2], 17 s à froid [n=1, process neuf] |

Journal depuis le 2026-11-01 (sauts groq) : 3 messages, payloads 14 313 / 14 560 / 16 070 car.,
tous le 2026-11-11, tous avec `chess_games_context n=20` (avant les statistiques du sprint 57).
Réponse alors par deepseek-flash en 1-2 s. Réponses finales groq hors échecs :
`in=3 752` et `in=3 863` tokens [n=2].

## 3. Diagnostic

1. **La liste des parties n'est pas la cause principale de la taille.** Au sprint 56, elle pesait
   ≈ 2 300 car. sur 14 000-16 000. Le reste vient du `context_block` (≤ 8 000) et de
   l'historique (≤ 6 000) : un message ordinaire tourne déjà autour de 11 000 car.
   [estimé : 3 800 tokens × ≈ 3 car./token, n=2]. L'ajout échecs fait basculer au-dessus de 12 000.
   Depuis le sprint 57 l'ajout vaut ≈ 4 400 car. : toute question d'échecs en CHAT saute groq
   [déduit, non observé : aucune question d'échecs en CHAT au journal depuis le sprint 57].
2. **Conséquence réelle du saut : faible.** La réponse part sur deepseek-flash (1-2 s, payant
   mais quelques fractions de centime par message), au lieu de qwen 27b gratuit. Aucune erreur,
   aucune latence ajoutée, qualité non comparée.
3. **« toutes » (34 745 car.) est le seul cas qui pèse vraiment** : il fait > 40 000 car. de payload,
   saute groq, passe à deepseek-flash. Pas observé au journal.
4. **Détection trop large, constatée** : `partie de foot ce soir`, `les victoires de Napoléon`,
   `mon adversaire politique` → vrai (exécuté). Effet : 4 400 car. de parties dans une
   question hors échecs, saut groq, risque que le LLM parle d'échecs. `BaguetteChaussette` seul
   → faux aujourd'hui (pseudo de Nico, pas adversaire) : cette partie de #211 est périmée.
   `donne-moi un conseil` seul → faux ; `… pour ma prochaine partie` → vrai (attendu).
5. **`load_chess_games` à chaque message** : 0,3 s à chaud, appelé même hors échecs (la
   détection a besoin des pseudos). Coût faible, pas de gêne rapportée.

## 4. Pistes (à arbitrer)

- A. Resserrer la détection : retirer les mots ambigus seuls (`parties?`, `victoires?`,
  `adversaires?`, `nulles?`, `defaites?`) ou les exiger avec un contexte échecs ; garder
  `echecs`, `ouvertures?`, les pseudos, `ma/mes partie(s)`.
- B. Alléger la section : 10 parties au lieu de 20 (−1 100 car.), ouvertures ≥ 5 parties au lieu
  de 3 (−≈ 1 000 car. [estimé]). Ne suffit pas à repasser sous 12 000 de façon fiable (point 1).
- C. Ne rien faire sur la taille : accepter deepseek-flash pour les questions d'échecs
  (éventuellement en le rendant explicite : rôle sans groq quand le contexte échecs est injecté).
- D. Plafonner « toutes » (ex. 100 dernières).
