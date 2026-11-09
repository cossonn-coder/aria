# Sprint 54 — état de conception

**Sujet** : l'analyse d'une erreur de Nico dit à quoi il a pensé (intention du coup) et ce
que cette idée a négligé, au lieu d'une simple comparaison moteur.
**Phase** : CLOS (run live 02 joué par Nico, 2026-11-09).
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
| 01b | `01b_intentions_maia.md` — intentions élargies, trace Maia, consigne « indices » | ✅ (562 verts) |
| 02 | `02_run_live.md` — run live Nico (partie de référence avec pendule) | ✅ (voir ci-dessous) |
| 01c | roque repris comme intention (correctif après le live, sans kickoff, OK Nico) | ✅ (562 verts) |

## Questions ouvertes

(aucune)

## Dettes

Ouverte : #205 (coup cité hors données dans le « Pourquoi : »). #92, #187 inchangées ; #115 non touchée.

## Run live 02 (2026-11-09)

- Partie Ashiki321x321 avec pendule, réanalysée (`reason=clock`) : 9...Qd7 → « mettre Qd6 à
  l'abri de Ba3 et déclouer Nc6 … négligé que Nc6 restait cloué sur Qd7 par Bb5, et Ne5 gagnait
  du temps sur ta dame ». Critère atteint ; temps (14 s) non cité (facultatif).
- Partie Cloclotop (sans pendule) : Maia cité après le coup 10 (« la moitié des joueurs »,
  « 61 % ») ; 19...Rc2+ : oubli « le roi pouvait reculer en d1 » = suite probable Maia.
- Défauts : 10...O-O-O sans aucun fait d'intention → LLM invente « le pion d3 restait prenable »
  (corrigé tronçon 01c, non revu en live) ; 11...Nb4 cite 12.Ne5 absent des données (#205).
- Journal : `chess_router OK` ×2, aucune ERROR, aucun `maia_human_lines FAILED` ; analyse sans
  explosifs 9,4 s.

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_pensee_erreur.md`. Tronçon 01 fait :
`_intent_line` + `_relative_pins` dans `execution/routers/chess_router.py` (ligne « idée du coup
joué » après « suite du coup joué » des sortes a/b, `times` passé à `_build_enriched`), consigne
« Pourquoi : » en 3 temps ; test `test_intent_line_threat_idea_and_self_pin` (position de
référence reconstruite, le PGN réel n'est pas dans le repo).

Tronçon 01b fait : `_intent_line` ajoute développe / attaque / contrôle / vise le roi / active /
libère et un segment « Maia : coup choisi par N % … ; suite probable : … » (coup > 10,
`played_p` non nul) ; nouveau champ `CriticalPosition.human_line_san` (coup joué en tête),
rempli par `assign_human_lines` dans `chess_coach/analysis.py`, appelé APRÈS
`assign_forcing_lines` (les positions critiques n'existent pas encore au moment de
`assign_difficulty` : écart au kickoff) ; consigne « Pourquoi : » en « indices ». Tests
`test_intent_line_broadened_intents_and_maia_trace`, `test_assign_human_lines_two_batched_passes`.
Sprint clos. Suite : `docs/sprint55/context_kickoff_sprint_55.md`, `/conception sprint 55`.
