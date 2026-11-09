# Sprint 54 — état de conception

**Sujet** : l'analyse d'une erreur de Nico dit à quoi il a pensé (intention du coup) et ce
que cette idée a négligé, au lieu d'une simple comparaison moteur.
**Phase** : B — conception figée (OK Nico 2026-11-09), prête pour `/sprint-auto sprint 54`.
**Branche** : `feat/sprint54-pensee-erreur`.

## Décisions arrêtées (Nico, 2026-11-09)

1. Faits d'intention calculés par le code, sans moteur en plus : coup adverse précédent et ce
   qu'il attaquait ; « met à l'abri X » / « défend X » sur le coup joué ; clouage créé par le
   coup joué (pièce clouée sur dame/tour). Pas de Maia (non fiable avant le coup 10).
2. Entrée « Pourquoi : » en 3 temps, 3 phrases max : idée probable (au conditionnel) → ce
   qu'elle a négligé → ce que fait le meilleur coup.
3. Temps passé sur le coup fautif donné au LLM si la pendule est fournie.
4. (Retour Nico après tronçon 01) Intentions élargies (développe, attaque, contrôle, vise le
   roi, active, libère), présentées au LLM comme indices et non liste fermée. Maia réintégré
   (révise la décision 1) : % du coup à l'Elo de Nico + suite humaine probable (2 demi-coups) ;
   seuil du coup 10 gardé.

## Tronçons

| # | Kickoff | Statut |
|---|---|---|
| 01 | `01_idee_et_oubli.md` — ligne « idée du coup joué » + consigne Pourquoi en 3 temps | ✅ (560 verts) |
| 01b | `01b_intentions_maia.md` — intentions élargies, trace Maia, consigne « indices » | ⏳ |
| 02 | `02_run_live.md` — run live Nico (partie de référence avec pendule) | ⏳ |

## Questions ouvertes

(aucune)

## Dettes

Aucune fermée ni ouverte à ce stade ; #115 adjacente, non touchée.

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_pensee_erreur.md`. Tronçon 01 fait :
`_intent_line` + `_relative_pins` dans `execution/routers/chess_router.py` (ligne « idée du coup
joué » après « suite du coup joué » des sortes a/b, `times` passé à `_build_enriched`), consigne
« Pourquoi : » en 3 temps ; test `test_intent_line_threat_idea_and_self_pin` (position de
référence reconstruite, le PGN réel n'est pas dans le repo). Prochaine étape : run live 02 par Nico.
