# Sprint 29 — Tronçon 14 : run live 12 (exécuté par Nico)

Prérequis : tronçons 12-13 commités. Messages : les 4 parties de
`run_live_11_parties.txt` (fichier copiable existant).

1. `sudo systemctl restart aria.service`.
2. Envoyer les 4 parties. Journal : `sudo journalctl -u aria -f -o cat`.

| Quoi | Où | Succès |
|------|----|--------|
| Meilleur coup | Telegram (ligne 🎯) | « trouvé par N % des joueurs de ton niveau » ; jamais une reprise ni une parade d'échec ; plus de « défense … 0 % de chances » ; plus de log `chess_best_move` |
| Légende | Telegram | chaque légende explique ≥ 2 coups de la variante par un fait concret (prise, échec, attaque) ; plus de « matériel égal, aucune pièce attaquée » répété ; « avantage » cohérent avec le % |
| Non-régression | Telegram + `chess_caption_split OK` | légendes sous les diagrammes, précision et pire coup présents |

## Critère de clôture
Les 3 lignes OK sur ≥ 3 parties sur 4. Écarts → dettes ou correctif arbitré.
