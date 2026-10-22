# Sprint 29 — Tronçon 09 : légende = idée générale + variante expliquée

Lire avant : `CLAUDE.md`, `docs/sprint29/00_etat.md`, `docs/sprint29/audit_retours_run_live.md` §2.

## Objectif (décision Nico)
Chaque entrée « Position N » (légende du diagramme N) contient, pour **toutes** les sortes :
1. l'idée générale de la position en une phrase (plan, pièce faible, roi exposé…) d'après
   les données fournies (pièces, matériel, attaquées, motifs) ;
2. la variante du meilleur coup (lignes fournies) expliquée coup par coup ;
3. au plus un chiffre ultra-succinct « 50 % → 37 % », ou rien.

## Fichier
`execution/routers/chess_router.py`, consigne de `_build_enriched` (l. ~570-584) :
remplacer « de 1 à 3 phrases : le coup, l'idée, le chiffre clé » par la structure
ci-dessus, jusqu'à ~5 phrases, entrée ≤ ~900 caractères (légende Telegram 1024 avec la
ligne factuelle). Les consignes e et d existantes restent (variante punitive, variante
du piège) ; pour a/b : la variante est celle du meilleur coup (`ligne :`).
Garder les interdits (n'inventer aucun coup, pièce ou évaluation).

## Tests
Le test garde-fou existant de la consigne s'il y en a un (`grep -n "1 à 3 phrases" tests/`)
adapté ; sinon un test que la consigne contient « variante » et « idée générale ».

## Hors-scope
Pas de changement de `_split_entries` / `_fit_entry` ni du prompt AnalystAgent.

## Critère de fin
`pytest tests/ -q` vert.
