# Sprint 26 — Tronçon 06 : run live du correctif (Nico)

Pré-requis : tronçon 05 commité, `sudo systemctl restart aria.service`.
Terminal de suivi : `sudo journalctl -u aria -f -o cat`

## Message A — renvoyer le message A de `04_run_live.md` (King_walks_19)

Attendu :
- journalctl : `intent FORCED name=jeux echecs`, puis
  `memory_write OK wing=aria_episodic … intent_name=jeux echecs`.
  Plus de `intent SKIPPED reason=namer_aucun` ni de `memory_write SKIPPED`.
- Telegram : la réponse commence par `Partie contre King_walks_19 2026-10-19`
  (pas d'ouverture : le PGN de test n'a pas d'en-tête ECO).

## Message B — renvoyer le message B de `04_run_live.md` (nojokeloco6789)

Attendu : idem A, réponse commençant par `Partie contre nojokeloco6789 2026-10-19`.

## Message C — question de suivi

`pourquoi la position 1 de cette partie était critique ?`

Attendu : réponse sur la Position 1 de **B** (15…Ce4, partie contre nojokeloco6789),
pas sur 16…Fe6 de A. Pas de log `chess_analysis`.

## Message C2 — suivi sur l'autre partie, par l'ancre

`et dans la partie contre King_walks_19, pourquoi la position 1 était critique ?`

Attendu : réponse sur 16…Fe6 (partie A). Pas de log `chess_analysis`.

## Message F — une partie Chess.com réelle avec en-tête ECO (facultatif)

Coller une partie exportée de Chess.com (avec `[ECOUrl "…"]`).

Attendu : ancre avec l'ouverture lisible, sans tirets
(ex. `Partie contre X 2026.10.19 Scandinavian Defense Mieses Kotrc Variation 3.Nc3`).

## Critère de succès

A et B : `memory_write OK … intent_name=jeux echecs` et ancre en tête de réponse.
C sur B, C2 sur A. Tout écart : noter message, horodatage et extrait journalctl.
