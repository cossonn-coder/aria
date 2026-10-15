# Sprint 19 — tronçon 03 : run live (Nico)

Prérequis : tronçons 01 et 02 commités sur `feat/sprint19-vision`.

## 0. Préparation (suppression de l'intent artefact, décision Q5)

```bash
sudo systemctl stop aria.service
cp ~/.aria/intents.json ~/.aria/intents.json.bak-sprint19
# retirer l'entrée "name": "maison de montagne"
# (id aecbde4e-a2be-41d9-9b3c-2c97435758a0)
python3 - <<'EOF'
import json, pathlib
p = pathlib.Path.home() / ".aria" / "intents.json"
d = json.loads(p.read_text())
d.pop("aecbde4e-a2be-41d9-9b3c-2c97435758a0")   # dict indexé par id (vérifié 2026-10-15)
p.write_text(json.dumps(d, ensure_ascii=False, indent=2))
EOF
grep -c "maison de montagne" ~/.aria/intents.json   # attendu : 0
sudo systemctl start aria.service
sudo journalctl -u aria -f -o cat
```

## 1. Messages Telegram à envoyer

| # | Envoi | Attendu (réponse) | Attendu (journalctl) |
|---|---|---|---|
| A | Photo **sans légende** | Français, quelques phrases, non coupée | `[VISION] deepseek (deepseek-flash) a répondu.` · `image_write OK` |
| B | Photo paysage + « Paysage savoyard » | Français, rien d'affirmé qui ne soit visible (incertitude dite) | idem A |
| C | Photo + « c'est quoi » | Pas de « c'est ta X » sans justification | `[IMAGE ENRICHED]` (INFO) · `intent SKIPPED reason=skip_intent` · `[LLM] … a répondu.` · `conversation_write OK` |
| D | Photo d'un projet (tomates / jardin) + « tu en penses quoi ? » | Lien au projet si visible et justifié | idem C |
| E | Photo + « What is this? » | Réponse en anglais | idem C (interrogative) ou A |

Après C et D : `grep -c '"name"' ~/.aria/intents.json` inchangé par
rapport à l'étape 0 (aucun intent créé).

## 2. Critère de succès

- Aucune réponse vision en anglais hors E, aucune coupée.
- Fournisseur vision identifiable dans les logs à chaque photo.
- Aucun `[IMAGE ROUTER FALLBACK]` attendu (sinon noter le fournisseur
  et l'erreur).
- Aucun intent créé par les photos.
- Verdict Nico sur la justesse (inventions, lien projet en D).
