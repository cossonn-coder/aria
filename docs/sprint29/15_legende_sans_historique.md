# Sprint 29 — Tronçon 15 : légende sans historique, variante racontée par le code

Audit : `audit_run_live_12.md`. Décisions Q1-Q3 A''' (Nico, 2026-10-22).

## Objectif

1. L'analyse de partie n'envoie plus l'historique de conversation au LLM (cause confirmée
   du moule « Position équilibrée … maintient N % »).
2. La variante est racontée par le CODE dans la légende de chaque diagramme ; le LLM
   n'écrit plus que l'idée générale.
3. La consigne donne le nombre exact d'entrées (plus de positions omises).

## 1. Historique coupé (`execution/routers/llm_router.py`, `chess_router.py`)

- `chess_router.execute` ajoute `"skip_history": True` au metadata de l'appel REASONING
  (à côté de `forced_intent_name`, `execution/routers/chess_router.py` ~l. 590).
- `LLMExecutionRouter._run_pipeline` (étape 1b, ~l. 120) : si `metadata.get("skip_history")`,
  ne pas appeler `load_conversation_history` ; `conversation_history = []` ;
  `log.info("conversation_history SKIPPED reason=skip_history")`.
- L'écriture de fin de pipeline (`write_conversation_turn` user + assistant) est **inchangée** :
  l'échange reste en historique pour les questions de suivi de Nico.
- Le chemin « PGN illisible » n'est pas concerné.

## 2. Variante racontée par le code (`execution/routers/chess_router.py`)

Une ligne `Variante : …` ajoutée **à la création de la légende** (dans `_caption` ou juste
après son appel dans `execute`), sous la ligne factuelle. Ainsi elle reste présente même en
repli `chess_caption_split FALLBACK`, et `_split_entries` (inchangé) place l'entrée du LLM
après elle (le budget 1024 tient déjà compte de la longueur de la légende existante).

Légende obtenue :
```
Position 5 — coup 21 (blancs) : tournant après 20...Bxg2?, joué 21.Rhe1 (meilleur 21.Rhe1)
Variante : 21.Rhe1 attaque Qe7 ; 21...Bxf3 prend Nf3 ; 22.Rxe7+ prend Qe7, échec ; 22...Bxe7 reprend ; 23.Qc7 attaque pion c6 ; 23...Kf7.
<entrée du LLM : idée générale>
```

Format : coups séparés par « ; », chaque coup = libellé `_move_label` (noirs numérotés
« 21...Bxf3 ») suivi de ses faits sans parenthèses ; coup sans fait = libellé seul ; point final.
Les faits sont **exactement ceux de `_move_facts`** (tronçon 13) : partager le calcul par coup
entre la ligne `faits :` du message enrichi et cette phrase (pas de seconde implémentation).

Quelle ligne, depuis quelle position :

| Sorte | Coups racontés | Position de départ | Premier coup |
|-------|----------------|--------------------|--------------|
| a (erreur de Nico) | `p.pv_san` (meilleur coup + suite) | `p.fen_before` | `p.move_number`, `p.color` |
| e (tournant), c (seul bon coup) | `critical.line_san` | `p.fen_before` | `p.move_number`, `p.color` |
| d (occasion explosive) | `[e.san] + e.trap_line_san` (coup explosif puis variante si réponse la plus probable) | `p.fen_before` | `p.move_number`, `p.color` |

Ligne vide (aucun coup) → pas de ligne `Variante :`.

## 3. Consigne (`_build_enriched`, consigne principale)

- Entrée par position = **idée générale seulement** : 1 à 3 phrases, ≤ 400 caractères, d'après
  la ligne « évaluation », les motifs et le but du meilleur coup (d'après ses faits).
  Ne pas énumérer les coups de la variante : elle est affichée par le code sous le diagramme.
- Nombre exact : remplacer « dans l'ordre Position 1, 2, 3 » par « une entrée pour chacune des
  N positions, de Position 1 à Position N, aucune omise » (N = `len(analysis.critical)`).
- Garder : 1re ligne ancre, marqueur « Position N — » en début de ligne, ligne « Niveau : »,
  interdits (n'invente rien, notation anglaise, ne paraphrase pas « matériel égal » / « aucune
  attaquée »).
- Consignes tournant (e) et occasion explosive (d) : inchangées.

## Tests (cas nominal)

- `tests/execution/test_llm_execution_router.py` : `skip_history` → `load_conversation_history`
  non appelé, l'agent reçoit un historique vide, `write_conversation_turn` toujours appelé.
- `tests/execution/test_chess_router.py` : la légende d'une position contient la ligne
  `Variante :` attendue (sorte a ou e, avec une prise et un échec) ; le metadata passé au
  LLM contient `skip_history` ; la consigne contient « Position 1 à Position N » avec N exact.
- Tests existants qui figent l'ancienne consigne / l'ancienne légende : ajuster.

## Hors scope

- `context_block` épisodique (extraits d'analyses passées), lignes « matériel » / « attaquées »
  du bloc, non-déterminisme de l'analyse : dettes (`audit_run_live_12.md`).
- Prompt AnalystAgent (`agents/analyst_agent.py`) : ne pas toucher.
- Traduction des pièces en toutes lettres (« le cavalier f3 ») : non, notation `Nf3` comme `faits :`.

## Critère de fin

`./venv/bin/pytest tests/ -q` vert ; `grep -n "Position 1, 2, 3" execution/routers/chess_router.py` vide.
