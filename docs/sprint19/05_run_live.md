# Sprint 19 — tronçon 05 : run live consignes enrichies (Nico)

Prérequis : tronçon 04 commité sur `feat/sprint19-vision`.

## 0. Préparation

```bash
grep -c '"name"' ~/.aria/intents.json   # noter le compte
sudo systemctl restart aria.service
sudo journalctl -u aria -f -o cat
```

## 1. Messages Telegram à envoyer

| # | Envoi | Attendu (réponse) | Attendu (journalctl) |
|---|---|---|---|
| E' | Photo (ex. le chat) + « What is this? » | **En anglais**, aucune mention des projets | `[VISION] deepseek …` · `[IMAGE ENRICHED]` · `intent SKIPPED reason=skip_intent` · `conversation_write OK` |
| C' | Photo sans lien projet (ex. échiquier) + « c'est quoi » | Français, **pas** de « pas de lien avec tes projets » | idem E' |
| D' | Photo du châssis de forçage + « tu en penses quoi ? » | Français ; lien au projet tomates seulement s'il est justifié | idem E' |

Après les trois : `grep -c '"name"' ~/.aria/intents.json` inchangé.

## 2. Critère de succès

- E' répond en anglais.
- C' et E' ne mentionnent pas les projets.
- Aucun intent créé par les photos, aucun `[IMAGE ROUTER FALLBACK]`.
- Si OK : #45-#51 fermées, clôture du sprint 19.
