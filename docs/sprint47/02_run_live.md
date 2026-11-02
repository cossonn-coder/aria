# Sprint 47 — tronçon 02 : run live (exécuté par Nico)

Service relancé sur le code du sprint (`/reboot`). Messages à copier : `docs/sprint47/run_live_messages.txt`.

Surveiller : `sudo journalctl -u aria -f -o cat | grep ouvertures`

Chiffres attendus au 2026-11-02 ; ils bougent si tu as analysé des parties de cette ouverture depuis.

| Envoi | Attendu sur Telegram |
|---|---|
| `/ouvertures` | Liste habituelle par ouverture et couleur, inchangée |
| `/ouvertures göring gambit` | `Göring Gambit (blancs) : 8 V, 3 D — 73 % [11 parties]`, coups 27,5, Elo, coup 10, coup 20, `5 dernières : 4 V, 1 D — 80 %` |
| `/ouvertures goring` | Même réponse |
| `/ouvertures dutch` | `Dutch Defense (noirs) : 5 V, 1 D — 83 % [6 parties]`, avec une ligne « 5 dernières » |
| `/ouvertures scandinavian` | Deux sections, blancs et noirs, sans ligne « 5 dernières » |
| `/ouvertures gambit` | Une ligne qui liste plusieurs ouvertures, sans statistiques |
| `/ouvertures hollandaise` | Aucune ouverture ne correspond, renvoi à `/ouvertures` |

**Succès :** réponses immédiates et conformes au tableau ; au journal, une ligne `meta_command name=ouvertures` par envoi, sans erreur.
