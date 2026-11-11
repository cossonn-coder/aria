# Sprint 56 — Tronçon 05 : le LLM reçoit les vraies parties

À lire d'abord : `CLAUDE.md`, `docs/sprint56/00_etat.md` ; tronçon 04 fait (sections préfixées au
`context_block`). Diagnostic : audit, constat 3.

## Objectif

Sur une question d'échecs en conversation (« mes 3 défaites d'affilée », « analyse mes 47 dernières
parties », « quelle partie contre Amateurspoeler ? »), le LLM reçoit la liste des fiches au lieu
des quelques souvenirs que la recherche vectorielle remonte (il en a inventé ou nié l'existence).

## Comportement attendu

Dans `execution/routers/llm_router.py` `_run_pipeline`, à côté de l'injection du tronçon 04 :

1. **Déclenchement** : le message parle de parties d'échecs — fonction pure, mots sans casse ni
   accent : `partie`, `parties`, `echecs`, `game`, `games`, `defaite(s)`, `victoire(s)`, `nulle(s)`,
   `adversaire`, ou un adversaire connu cité par son pseudo. **Pas** de déclenchement quand
   `metadata.get("skip_history")` est vrai (bilan d'une partie analysée : il a déjà ses données).
2. **Nombre de parties** (décision de Nico, 2026-11-11) : fonction pure sur le message.
   - un nombre suivi de `dernière(s)` / `derniers` / `parties` / `games` → ce nombre (« 3 dernières », « 47 dernières parties ») ;
   - `toutes`, `totalité`, `tout l'historique`, `all` → toutes les fiches ;
   - sinon 20.
3. **Lecture** : `self.mempalace_bridge.load_chess_games()` (déjà trié par timestamp) ; les N plus
   récentes, du plus récent au plus ancien.
4. **Section** préfixée au `context_block`, après les règles et consignes :

```
[Parties de Nico — 20 plus récentes sur 299, fiches du palace]
2026-11-11 · blancs · contre Amateurspoeler (1729) · victoire · French Defense: Alapin Gambit · précision 88 %
…
```

Une ligne par fiche : jour (règle de `_game_day`, `interfaces/meta_commands.py:143`), couleur, adversaire
(Elo), issue (`issue inconnue` si `unknown`), ouverture, précision si présente. La fonction de
formatage vit **hors de `interfaces/`** (pas d'import `interfaces` → `execution`, dette #204) :
par exemple `chess_coach/summary.py`, qui a déjà `_COLOR_FR` / `_OUTCOME_FR` (l. 29-30).
Log : `chess_games_context n=20 total=299`.

Ordre de grandeur : ~130 caractères par ligne → « toutes » ≈ 40 000 caractères [estimation,
299 fiches]. Accepté par Nico ; pas de plafond. Si le fournisseur refuse (taille), la chaîne
de repli de `llm/llm_router.py` s'applique, rien à ajouter.

## Fichiers à toucher

- `execution/routers/llm_router.py`, `chess_coach/summary.py` (ou module `chess_coach` équivalent).
- Tests : `tests/execution/test_llm_execution_router.py`, test du formatage et des deux fonctions pures.

## Tests (cas nominal)

- Nombre : « mes 3 dernières parties » → 3 ; « analyse les 47 dernières parties » → 47 ;
  « toutes mes parties » → toutes ; « ma journée aux échecs » → 20.
- Déclenchement : « j'ai fait 3 défaites d'affilée » → oui ; « quel temps fait-il » → non ;
  `skip_history` → non.
- Router : le `context_block` contient la section avec le bon nombre de lignes.
- `pytest tests/ -q` vert.

## Hors-scope (ne PAS faire)

- Pas de statistiques calculées (taux, moyennes) dans la section : la liste brute suffit ici ;
  un bilan calculé sur N parties = sprint 57 ou suivant.
- Pas de `plies_json` ni de coups dans la section.
- Pas de changement de `/parties`.

## Critère de fin

Tests verts.
