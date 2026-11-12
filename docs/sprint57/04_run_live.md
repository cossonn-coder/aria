# Sprint 57 — Tronçon 04 : run live (Nico)

Messages à copier : `docs/sprint57/04_run_live.txt` (un bloc = un message, dans l'ordre).
Aucun nettoyage du palace : pas de sauvegarde nécessaire.

## Préparation

1. Nico : `sudo systemctl restart aria.service`, puis `sudo journalctl -u aria -f -o cat`.
2. Avoir une **partie neuve** (jamais envoyée), idéalement avec plusieurs erreurs des deux camps.

## Critères de succès

| Msg | Attendu |
|---|---|
| 1 (partie neuve) | dernière ligne `🏅 Précision X % : Ne sur M en rapide, partie … (… coups) · …` ; M < nombre total de fiches |
| 1 | si une erreur adverse ≥ 20 pts n'a pas été punie ou si un explosif a été trouvé : ligne `🔎 Occasions manquées : …` dans le bilan ; ces occasions ont une miniature avant les erreurs simples (journal `chess_analysis OK … critical=[b:…, d:…]`) |
| 1 | journal : durée `chess_explosive … duration=` et `chess_analysis OK … duration=` relevées (surcoût accepté, à noter) ; pas de `chess_explosive skipped: … errors fill the budget` sauf ≥ 4 erreurs non punies |
| 2 | réponse fondée sur les vrais chiffres (ex. von Hennig 8/0/0, Göring 20/0/17) ; pas d'ouverture inventée ; journal `chess_games_context` |
| 3 | idem sur les noirs |

Critères 2-3 dépendants du LLM : un écart se note [n=1] ; vérifier alors que la section
`[Statistiques d'échecs …]` était bien dans le prompt (tests / log).
