# Sprint 29 — Tronçon 16 : run live 13 (exécuté par Nico)

Prérequis : tronçon 15 commité. Messages : les 4 parties de `run_live_11_parties.txt`.

1. `sudo systemctl restart aria.service`.
2. Envoyer les 4 parties. Journal : `sudo journalctl -u aria -f -o cat`.

| Quoi | Où | Succès |
|------|----|--------|
| Historique coupé | journalctl | `conversation_history SKIPPED reason=skip_history` à chaque partie (plus de `loaded … messages=20`) |
| Variante | légendes Telegram | chaque légende a une ligne « Variante : » avec les faits (prend, échec, attaque) |
| Idée générale | légendes Telegram | plus de « maintient N % », plus de « aucune pièce attaquée » ; texte différent d'une position à l'autre |
| Toutes les positions | journalctl | `chess_caption_split OK` 4/4 |
| Non-régression | Telegram | ligne 🎯 (précision, meilleur coup « trouvé par N % », pire coup), bloc Progression |

## Critère de clôture
Les 5 lignes OK sur ≥ 3 parties sur 4. Écarts → dettes ou correctif arbitré.
