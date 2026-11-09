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

## Tronçons

| # | Kickoff | Statut |
|---|---|---|
| 01 | `01_idee_et_oubli.md` — ligne « idée du coup joué » + consigne Pourquoi en 3 temps | ⏳ |
| 02 | `02_run_live.md` — run live Nico (partie de référence avec pendule) | ⏳ |

## Questions ouvertes

(aucune)

## Dettes

Aucune fermée ni ouverte à ce stade ; #115 adjacente, non touchée.

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_pensee_erreur.md`. Prochaine étape :
`/sprint-auto sprint 54` (tronçon 01), puis run live 02 par Nico.
