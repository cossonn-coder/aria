# Sprint 58 — tronçon 01 : détection resserrée des questions d'échecs (#211)

Lire avant : `CLAUDE.md`, `docs/sprint58/00_etat.md`, `docs/sprint58/audit_contexte_echecs.md` (§1, §3.4).

## Objectif

`mentions_chess_games` (`execution/routers/llm_router.py:94`) décide si la liste des parties et les
statistiques d'échecs (≈ 4 400 car.) sont injectées dans le contexte LLM. Elle déclenche aujourd'hui
sur des mots ambigus seuls (« une partie de foot », « les victoires de Napoléon », « mon adversaire
politique »). Le tronçon resserre la règle.

## Règle à implémenter (validée par Nico)

Sur le message sans accents ni casse (`_plain`, déjà présent), vrai si l'un de :

1. `echecs` ou `ouvertures?` n'importe où (mots entiers).
2. `parties?`, `victoires?`, `defaites?`, `nulles?` **précédé** de `ma` / `mes` / `cette` / `ces`
   avec au plus 2 mots entre les deux (« ma prochaine partie », « mes 3 dernières parties »),
   **ou** précédé d'un nombre avec au plus 1 mot entre (« 3 défaites », « 3 dernières parties »).
3. Un pseudo d'adversaire connu (paramètre `opponents`, inchangé) **ou** un pseudo de Nico
   (`config.chess_usernames`, `config.py:89` ; `config` est déjà importé dans le module).

Retirés : `games?` et `adversaires?` comme déclencheurs seuls.

Prototype validé (scratch, à réécrire proprement) :

```python
NOUN = r"(parties?|victoires?|defaites?|nulles?)"
_CHESS_WORDS = re.compile(
    r"\b(echecs|ouvertures?)\b"
    rf"|\b(ma|mes|cette|ces)\s+(\S+\s+){{0,2}}?{NOUN}\b"
    rf"|\b\d+\s+(\S+\s+)?{NOUN}\b"
)
```

La signature de `mentions_chess_games(message, opponents)` ne change pas ; le caller
(`_run_pipeline`, étape 4b) n'est pas modifié.

## Tests à ajouter / adapter

`tests/execution/test_llm_execution_router.py`, `test_mentions_chess_games` (garder ses 4 assertions,
elles restent vraies) + un `parametrize` sur le tableau :

| Message | Attendu |
|---|---|
| analyse mes 3 dernières parties | vrai |
| donne-moi un conseil pour ma prochaine partie | vrai |
| quelle est ma meilleure ouverture avec les blancs ? | vrai |
| j'ai fait 3 défaites d'affilée | vrai |
| gain de BaguetteChaussette sur abandon de l'adversaire (opponents vide) | vrai |
| une partie de foot ce soir | faux |
| les victoires de Napoléon | faux |
| mon adversaire politique | faux |

Ne pas ajouter d'autres cas. `pytest tests/ -q` vert.

## Mise à jour documentaire (même tronçon)

Dans `docs/sprint58/context_kickoff_sprint_58.md`, ligne #211 : statut → « touchée sprint 58 :
détection resserrée ; saut groq accepté par Nico (deepseek-flash) ; mention BaguetteChaussette
périmée ; `load_chess_games` relu à chaque message (0,3 s) laissé tel quel ».

## Hors-scope (ne PAS faire)

- Toucher `games_context_section`, `games_stats_section`, `DEFAULT_CHESS_GAMES`, `requested_games_count`
  (pas d'allègement, pas de plafond de « toutes » : décisions de Nico).
- Toucher `GROQ_MAX_PAYLOAD_CHARS` ou la table de routage LLM.
- Éviter l'appel `load_chess_games` hors échecs.

## Critère de fin

Tests du tableau verts, suite complète verte, commit local
`fix(sprint58) tronçon 01: détection resserrée des questions d'échecs (#211)`.
