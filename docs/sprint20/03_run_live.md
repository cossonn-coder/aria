# Sprint 20 — tronçon 03 : run live relances après photo (Nico)

Prérequis : tronçons 01 et 02 commités sur `feat/sprint20-relances`.

## 0. Préparation

```bash
grep -c '"name"' ~/.aria/intents.json   # attendu : 5 (parasites conservés, Q6)
sudo systemctl restart aria.service
sudo journalctl -u aria -f -o cat
```

## 1. Messages Telegram à envoyer (dans l'ordre)

| # | Envoi | Attendu (réponse) | Attendu (journalctl) |
|---|---|---|---|
| 1 | Photo de l'échiquier **sans légende** | description vision | `[VISION] deepseek …` · `image_write OK` · `conversation_write OK` |
| 2 | « évalue la position » | s'appuie sur la description de la photo (plus de « je ne vois pas l'image ») | pas de nouvel intent (`namer_aucun` ou rattachement à un intent existant) |
| 3 | « pourtant les noirs abandonnent ici » | idem 2 | idem 2 |
| 4 | « il fait beau aujourd'hui » | — | `intent SKIPPED reason=namer_aucun` · `memory_write SKIPPED` |
| 5 | « combien de litres de terreau par pied ? » | réponse tomates | `memory_write OK … intent_name=plantation tomates balcon est` |
| 6 | « je veux apprendre docker cet hiver » | — | `memory_write OK … intent_name=<nouveau nom docker>` |

Après les six : `grep -c '"name"' ~/.aria/intents.json` → **6**.

## 2. Critère de succès

- La photo standard est dans l'historique (1 → `conversation_write OK`,
  2 et 3 la citent).
- Un seul intent créé (docker) ; 4 sans intent ; 5 rattaché aux tomates.
- Si OK : #57 et #59 fermées, #61 fermée, #60 reformulée ; clôture.
