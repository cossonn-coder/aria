# Sprint 29 — Tronçon 11 : run live des retours (exécuté par Nico)

Prérequis : tronçons 07-10 commités. Messages : les 4 parties de l'audit
(`run_live_retours_parties.txt`, coups seuls : l.orchestrateur fournit un .txt copiable avec en-têtes White/Black/Elo) ou des récentes.

1. `sudo systemctl restart aria.service` → chronométrer : arrêt < 10 s, aucun
   « State 'stop-sigterm' timed out » ; journal : « ARIA arrêt ».
2. Envoyer les parties. Journal : `sudo journalctl -u aria -f -o cat`.

| Quoi | Où | Succès |
|------|----|--------|
| Occasions explosives | Telegram + `chess_explosive found=` | ≥ 1 flèche orange sur l'ensemble ; idée risquée présentée comme telle |
| Légende | Telegram | idée générale + variante expliquée coup par coup ; pas de pavé de chiffres |
| Précision | Telegram | partie à gaffes (Falestinhurra) nettement < 86 % ; une valeur par partie |
| Meilleur / pire coup | Telegram + `chess_best_move OK` | ligne 🎯 présente ; meilleur coup jamais une prise évidente après faute adverse |

## Critère de clôture
Les 4 lignes OK sur ≥ 2 parties + arrêt < 10 s. Écarts → dettes ou correctif arbitré.
