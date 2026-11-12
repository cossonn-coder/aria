# Sprint 57 — état (carnet de bord)

**Sujet** : évaluer et classer les parties + dette prioritaire #209.
**Branche** : `feat/sprint57-classer-parties` (depuis `main` `2f51b44`).
**Phase** : B figée (OK de Nico le 2026-11-12) — prêt pour `/sprint-auto sprint 57`.

## Audit

`docs/sprint57/audit_classer_parties.md` (2026-11-12). Points clés :
- Cadence quasi uniforme : 287 parties [sur 300] en 10 min ; le classement sera en pratique par longueur.
- `nico_moves` absent de 154 fiches → longueur prise sur `n_plies`.
- Les deux occasions manquées existent déjà : erreur adverse non punie = sorte b,
  coup explosif non joué = sorte d. Le travail = priorité b, d avant a.
- Le saut de la recherche explosive (≥ 4 erreurs) doit ne compter que les erreurs non punies :
  ≈ 74 parties sur 300 [first_move approché] paieraient la recherche en plus.
- #209 : agrégats déjà calculés (`opening_stats`, `performance`), jamais donnés au LLM ;
  contrainte de taille #211.

## Décisions arrêtées

- 2026-11-12 : 🏅 le rang par catégorie (cadence × longueur) **remplace** le rang global ;
  segments jour et ouverture inchangés. Longueur en coups `(n_plies + 1) // 2` :
  courte ≤ 25, moyenne 26-40, longue > 40. (Catégories équilibrées : 131 / 102 / 67.)
- 2026-11-12 : occasions manquées (erreur adverse non punie, coup explosif non joué)
  prioritaires sur les erreurs de Nico **dans le choix** des 4 miniatures ; affichage
  chronologique inchangé. Surcoût de la recherche explosive accepté, durée mesurée au run live.
- 2026-11-12 : #209 inclus : bilan V/N/D par ouverture × couleur (ouvertures à ≥ 3 parties)
  + performance Elo, dans le contexte LLM sur une question d'échecs.
- 2026-11-12 : format de la ligne 🔎 (erreurs adverses non punies toutes, explosifs 3 plus forts)
  et découpage en 3 tronçons + run live validés par Nico (« ok »).
- 2026-11-12 (figeage) : `ouvertures?` ajouté aux mots-clés d'échecs du llm_router, sinon la
  question de #209 n'injecte rien (constat au code, tronçon 03).

## Carte des tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_classement.md` — 🏅 rang par catégorie cadence × longueur | ✅ |
| 02 | `02_occasions_manquees.md` — priorité b → d → a → e → c, saut explosif sur b seules, ligne 🔎 | ✅ |
| 03 | `03_stats_au_llm.md` — V/N/D ouvertures ≥ 3 parties + performance au LLM, mot-clé `ouvertures?` (#209) | ✅ |
| 04 | `04_run_live.md` + `04_run_live.txt` — run live (Nico) | ⏳ |

## Dettes

- Fermée par le sprint (à confirmer au run live) : #209.
- Touchée : #211 (contexte LLM grossit d'≈ 2 500 car.).
- À ouvrir : l'échiquier web garde le rang de précision global (pas par catégorie).

## §REPRISE

Tronçons 01, 02 et 03 faits. 03 : fonction sœur `games_stats_section(games)` dans
`chess_coach/summary.py` (performance Elo + V/N/D des ouvertures ≥ 3 parties, toutes les
fiches), appelée dans `llm_router.py` juste après `games_context_section` ; `ouvertures?`
ajouté à `_CHESS_WORDS`. Tests : `test_games_stats_section_keeps_openings_with_three_games`
(test_summary.py), phrase #209 dans `test_mentions_chess_games`. pytest 588 verts.
Taille réelle de la section (≈ 2 500 car. visés) non mesurée sur le palace : à voir au run live.
Prochaine étape : run live 04 par Nico (`04_run_live.md`).
