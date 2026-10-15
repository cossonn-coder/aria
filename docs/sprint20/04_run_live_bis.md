# Sprint 20 — tronçon 04 : run live bis, relances sans parasites (Nico)

Prérequis : tronçons 01 (`2359a4f`) et 02 (`07a890c`) commités ; décision
Q7 (`00_etat.md`) appliquée.

## 0. Purge des parasites — FAITE (2026-10-15, ~23:15, service arrêté)

Sauvegarde : `~/.aria/intents.json.bak-sprint20`. Les 4 parasites
(`surface pieds conseils`, `orientation scolaire professionnelle`,
`evaluation position`, `abandon des noirs`) sont en `status: "abandoned"`
(recall filtré sur `status == "active"`, `intent_recall_engine.py:73`).
Actifs restants : `plantation tomates balcon est`, `apprentissage docker`.
Retour arrière : recopier la sauvegarde, service arrêté.

## 1. Démarrage

```bash
sudo systemctl start aria.service
sudo journalctl -u aria -f -o cat
```

## 2. Messages Telegram (dans l'ordre)

| # | Envoi | Attendu (journalctl) |
|---|---|---|
| 1 | photo de l'échiquier sans légende | `conversation_write OK` |
| 2 | « évalue la position » | `intent SKIPPED reason=namer_aucun` ; aucun attach sur un parasite |
| 3 | « pourtant les noirs abandonnent ici » | idem 2 |
| 4 | « il fait beau aujourd'hui » | `intent SKIPPED reason=namer_aucun` |
| 5 | « combien de litres de terreau par pied ? » | `memory_write OK … intent_name=plantation tomates balcon est`, ou à défaut `namer_aucun` |

Non-critère : en 2-3, la réponse dira encore qu'elle ne peut pas évaluer
la position (description sans position = #60).

## 3. Critère de succès

- Aucun `memory_write OK` sur un intent abandonné.
- Aucun intent créé : `grep -c '"status": "active"' ~/.aria/intents.json` → 2.
- Si OK : #57, #59, #61 fermées, #60 reformulée ; clôture du sprint.
- Si le namer crée un intent en 2 ou 3 : son prompt est en cause → `/conception`.
