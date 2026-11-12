# Audit sprint 57 — évaluer et classer les parties

Date : 2026-11-12. Branche `feat/sprint57-classer-parties` (depuis `main` = `2f51b44`).
Données : copie de `~/.mempalace/palace/chroma.sqlite3` (métadonnées seules, lecture
seule, dans le scratchpad de la session) : **300 fiches `chess_game`**.

Trois sujets : (1) classement 🏅 par longueur × cadence ; (2) occasions manquées avant
les erreurs de Nico (miniatures + bilan) ; (3) dette prioritaire #209 (statistiques du
code absentes du contexte LLM).

---

## 1. Classement 🏅 — code actuel

`execution/routers/chess_router.py:563` `_rank_line(summary, games)` : dernière ligne du
bilan, appelée à `chess_router.py:1186-1187` (après écriture de la fiche, `games` =
`bridge.load_chess_games()`, partie courante incluse).

```
🏅 Précision 86 % : 12e sur 300 · 2e sur 3 aujourd'hui · 5e sur 37 en Göring Gambit (blancs)
```

- Segment 1 : rang sur **toutes** les fiches (`accuracy_rank`, `chess_coach/level.py:37`).
- Segment 2 : fiches du même jour (`_day`), omis si seule.
- Segment 3 : même groupe d'ouverture + même couleur (`game_opening_group`), omis si seule.
- Test : `tests/execution/test_chess_router.py:1046` `test_rank_line_gives_overall_day_and_opening_ranks`.

Autres callers de `accuracy_rank` : `interfaces/board_interface.py:198` (échiquier web,
rang sur toutes les fiches). Hors sujet du sprint (l'échiquier garde le rang global).

### Données disponibles sur les fiches

| Champ | Présent | Remarque |
|---|---|---|
| `n_plies` | 300/300 | longueur fiable sur toutes les fiches |
| `nico_moves` | 146/300 | absent des fiches antérieures au sprint 50 → **ne pas l'utiliser** |
| `time_control` | 300/300 (dont 10 vides) | `"600"` 287 · `""` 10 · `"300"` 2 · `"300+3"` 1 |
| `accuracy` | 300/300 | — |

**Constat : la cadence ne discrimine presque rien aujourd'hui** : 287 parties [sur 300]
en 10 min (rapide), 3 en blitz, 10 sans cadence. L'axe cadence coûte une ligne de code,
mais le classement sera en pratique « par longueur ».

### Longueur → précision (coups = `(n_plies + 1) // 2`)

Précision médiane par catégorie, selon trois jeux de seuils [300 fiches, 1 relevé] :

| Seuils (coups) | courte | moyenne | longue |
|---|---|---|---|
| ≤ 25 / 26-40 / > 40 | 131 parties, 85,5 % | 102, 85,3 % | 67, 82,3 % |
| ≤ 20 / 21-40 / > 40 | 81, 86,9 % | 152, 85,2 % | 67, 82,3 % |
| ≤ 30 / 31-50 / > 50 | 174, 85,5 % | 95, 83,3 % | 31, 82,4 % |

Seuils calculés ici sur les coups de la partie (les deux camps), pas les coups de Nico.
Les longues parties sont moins précises de ≈ 3 points [médianes, 1 relevé] : l'effet
existe mais il est modeste. 14 parties [sur 300] font moins de 10 coups.

---

## 2. Occasions manquées — code actuel

### Sélection des miniatures

`chess_coach/analysis.py:525` `select_critical(plies, nico_color, explosive, first_move)` :
budget 4 (`_CRITICAL_BUDGET`), groupes dans l'ordre **(erreurs a+b mélangées, triées par
perte) → explosifs d → tournants e → coups uniques c**, puis tri chronologique pour
l'affichage (`sorted(selected, key=ply)`).

- (a) erreur de Nico : perte ≥ 10 (≥ 20 jusqu'au coup 10) — `_critical_errors`, `analysis.py:511`.
- (b) même erreur **juste après une erreur adverse** (perte adverse ≥ 20) = **erreur adverse
  non punie**. C'est exactement l'occasion manquée (a) de Nico. Libellé LLM : « occasion
  manquée après erreur adverse » (`chess_router.py:58` `_KIND_FR`).
- (d) occasion explosive : coup explosif non joué, coup joué à perte < 10
  (`chess_coach/explosive.py:406` `find_explosive`). C'est l'occasion manquée (b) de Nico.
- (e) tournant = erreur adverse **punie** (perte de Nico < 10) : pas une occasion manquée.

**Écart sujet / code** : les deux sortes d'occasions manquées existent déjà. Le travail
est un **changement de priorité**, pas une détection nouvelle :
aujourd'hui `a` et `b` sont mélangées et passent avant `d` ; demandé : `b`, `d` avant `a`.

### Effet de bord : la recherche explosive sautée

`chess_coach/analysis.py:690-695` (`analyze`) : si les erreurs a+b remplissent le budget
(≥ 4), `find_explosive` n'est pas lancée (`chess_explosive skipped`, gain de temps du
sprint 49, #162). Avec la nouvelle priorité, ce saut n'est plus juste : un explosif doit
passer devant une erreur simple. Il ne reste légitime que si les **erreurs non punies (b)**
remplissent seules le budget.

Ordre de grandeur [300 fiches, `first_move` approché à 4, pas le vrai `first_shown_move`] :
- recherche aujourd'hui sautée sur 77 parties ;
- avec le nouveau critère, sautée sur 3 parties.
→ ≈ 74 parties sur 300 paieraient en plus la recherche explosive. Coût d'une recherche :
197,7 s sur 31 positions [n=1, #189] ; coût typique non mesuré ici (journal non lisible
sans sudo depuis la session).

### Fréquences [300 fiches, positions retenues stockées dans `plies_json.kind`]

| Sorte retenue | Nombre |
|---|---|
| explosif (d) | 491 |
| erreur de Nico (a) | 443 |
| tournant (e) | 77 |
| erreur adverse non punie (b) | 69 |
| coup unique (c) | 20 |

Erreurs adverses (perte ≥ 20) non punies : 96, dans 69 parties [compteurs de fiche
`opponent_errors` − `opponent_errors_punished`].

### Bilan final

Le bilan écrit par le code (`_moves_line`, `chess_router.py:586`) a : précision, alerte
précision adverse, meilleurs coups, erreurs par gravité, coups brillants, meilleur / pire
coup, clé des pastilles. **Aucune ligne « occasions manquées ».**

Sources disponibles au moment du bilan (`_execute_game`, `chess_router.py:1060`) :
- `analysis.explosive` : **toutes** les occasions explosives trouvées (retenues ou non),
  coups ≥ `first_move` ;
- `analysis.plies` : erreurs adverses non punies recalculables (même règle que
  `summarize` : perte adverse ≥ 20, réponse de Nico à perte ≥ 10).

---

## 3. Dette #209 — statistiques absentes du contexte LLM

Constat (2026-11-11 16:40) : « quelle est ma meilleure ouverture avec les blancs ? » →
Bishop's Opening inventé.

Code : `execution/routers/llm_router.py:332-341` injecte, sur une question d'échecs
(`mentions_chess_games`), `games_context_section(games, n)` (`chess_coach/summary.py:347`) :
la liste brute des N fiches (20 par défaut), une ligne par partie. **Aucun agrégat.**

Les agrégats existent déjà, écrits par le code :
- `chess_coach/player_model.py:160` `opening_stats(games)` → (groupe, couleur) → V/N/D ;
- `chess_coach/level.py:18` `performance(games)` ;
- `interfaces/meta_commands.py:255` `_opening_stat_lines` / `openings_text` (`/ouvertures`) :
  le rendu complet, **4 337 car., 71 lignes** sur le palace actuel [1 relevé].

Contrainte #211 : le contexte avec la liste des 20 parties fait déjà 14 000-16 000 car.,
au-dessus du plafond Groq de 12 000 (repli deepseek-flash) [n=3]. Ajouter tout
`/ouvertures` aggrave. Les ouvertures à 1-2 parties (≈ 25 lignes) n'apportent rien à
« meilleure ouverture ».

Règle d'architecture : `llm_router` → `interfaces/meta_commands` serait un couplage
exécution → interface Telegram (cf. #204). Le rendu doit vivre dans `chess_coach/`
(module pur), comme `games_context_section`.

---

## 4. Règles d'architecture

- Aucune écriture mémoire nouvelle (classement et lignes de bilan = calcul sur fiches lues).
- Lecture : `bridge.load_chess_games()` déjà appelé aux deux endroits.
- Pas de palace prod modifié : calibrage faible.
