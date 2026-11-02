# Sprint 47 — état vivant

**Phase courante** : tronçon 01 fait, reste le run live (tronçon 02).
**Branche** : `feat/sprint47-topo-ouverture` (depuis `main`).

## Décisions arrêtées

- Sujet : `/ouvertures <nom>`, topo par ouverture (performances, ce qui fait gagner, ce qui fait perdre, pistes). Choix de Nico, 2026-11-02.
- Écarté après mesure : détection « même position, même erreur » (ne remonte que les coups du gambit, voir audit).
- Nico, 2026-11-02 : on garde seulement les stats ; plus de « ce qui fait gagner / perdre », plus de pistes, donc **pas de LLM** : `/ouvertures <nom>` reste une métacommande (pas de kernel, pas de nouvelle opération). Remplace les questions 1 et 2 du premier lot.
- « Pour chaque ouverture » : à la demande, une ouverture à la fois, n'importe laquelle (Nico n'a pas repris le « tout d'un coup »).
- Nico : pas de `[n=…]` dans la sortie ; ajouter coups moyens par partie, % de gain au coup 20 si la donnée existe, tendance sur les 5 dernières parties quand il y en a plus de 5, stats de toute l'ouverture. Aucune donnée inventée : ligne absente si pas de donnée.

- Nico, 2026-11-02 : « stats globales » = toutes les parties enregistrées de l'ouverture, sans plafond ; pas de ligne toutes ouvertures confondues. Réponse prise pour l'OK de figer.
- Par défaut annoncés à Nico : recherche sans accent ni casse, liste si plusieurs correspondances, une section par couleur, partie trop courte exclue de la moyenne du coup N, 5 dernières triées par date de partie, à défaut d'analyse.

- Nico, 2026-11-02 : hors kickoff, marge Stockfish portée à 60 s dans `analyze_game` et `find_explosive` (3 analyses perdues sur `TimeoutError` le 2026-11-02). Cause du gel non prouvée, pression mémoire suspectée.

## Carte des tronçons

- 01 `/ouvertures <nom>` (`01_stats_ouverture.md`) ✅
- 02 run live par Nico (`02_run_live.md`, messages : `run_live_messages.txt`) ⏳

## Questions ouvertes

- (aucune)

## Dettes

- Nouvelles, inscrites au kickoff du sprint 47 : #169 noms français d'ouvertures, #170 aucune horloge dans les fiches.
- #81 (déviations de répertoire) reste ouverte : mesure négative dans l'audit.

## §REPRISE

Tronçon 01 implémenté : `opening_report_text` dans `interfaces/meta_commands.py`, `_cmd_ouvertures` lit ses arguments. Suite : tronçon 02, run live par Nico (`02_run_live.md`, messages : `run_live_messages.txt`).
