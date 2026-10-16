# Sprint 24 — Tronçon 02 : run live (Nico)

Prérequis : tronçon 01 commité, `POLLINATION_API_KEY` présente dans `.env`.

```
sudo systemctl restart aria.service
sudo journalctl -u aria -f -o cat
```

## Messages Telegram à envoyer (dans l'ordre)

| # | Message | Attendu Telegram | Attendu journalctl |
|---|---|---|---|
| A | `dessine un renard qui lit le journal dans la neige` | une photo conforme, **sans filigrane** pollinations.ai, légende = le message | `[IMAGE GEN] pollinations_key a répondu.`, aucun `[IMAGE ROUTER FALLBACK]` |
| B | `génère une image d'un chat roux qui arrose des tomates, style aquarelle` | photo conforme, en < 15 s | idem A |
| C | `tu peux afficher la liste des courses ?` | réponse **texte**, pas d'image | aucune ligne `[IMAGE GEN]` ni `[IMAGE ROUTER FALLBACK]` (le type d'opération n'est pas logué) |
| D | photo quelconque + légende `transforme en aquarelle` | **description** de la photo (texte), pas d'image générée | `[VISION] … a répondu.` + `image_write OK`, aucune ligne `[IMAGE GEN]` |

## Critère de succès

A, B, C, D conformes. Si A sort avec filigrane : la clé n'a pas servi
(chercher `[IMAGE ROUTER FALLBACK] pollinations_key failed: …`).
