# Sprint 24 — état de conception

**Phase** : B — conception figée (OK Nico 2026-10-16), prête pour `/sprint-auto sprint 24`.
**Cible** : #44 génération d'images.
**Branche** : `feat/sprint24-generation-images`.

## Décisions arrêtées

- 2026-10-16 — Cible sprint 24 = #44 génération d'images (choix Nico).
- Fournisseur : Pollinations avec clé `sk_` de Nico, variable `.env`
  `POLLINATION_API_KEY` (sans S), modèle gratuit `tongyi-mai/z-image-turbo`.
  Pas de fournisseur payant (fal.ai écarté).
- HF retiré de la table de routage.
- Bloc `[Contexte : …]` (intents + souvenirs) supprimé du prompt de génération.
- Secours : Pollinations anonyme (client actuel) derrière la clé.
- Prompt : message FR brut, sans réécriture LLM ; mémoire épisodique = demande brute.
- Heuristiques texte resserrées ; photo + légende de génération → IMAGE_INPUT
  (plus de génération depuis un event photo) ; img2img → dette #77.

## Questions ouvertes

_(aucune)_

## Tronçons

| # | Kickoff | Statut |
|---|---|---|
| 01 | `01_generation.md` — Pollinations avec clé + secours anonyme, HF hors table, prompt brut, photo → toujours IMAGE_INPUT, mots-clés resserrés | ⏳ |
| 02 | `02_run_live.md` — run live (Nico) | ⏳ |

## Dettes

- Fermée par le sprint (si run live OK) : #44.
- Ouverte : #77 image-to-image (photo + légende de génération ; Pollinations
  accepte `image=` mais il faut une URL publique de la photo).
- Ouverte : `llm/image_gen/hf_client.py` + `config.hf_image_model` morts
  après tronçon 01 (numéro à attribuer à la clôture).
- Notée : génération Pollinations = 404 sur un prompt enrichi [n=1, cause
  non isolée] — devient sans objet sans bloc contexte.

## §REPRISE

Lire `CLAUDE.md`, `docs/sprint24/audit_generation_images.md` (§5 = sonde
clé), ce fichier. Prochaine étape : `/sprint-auto sprint 24` (tronçon 01), puis run live 02 par Nico.
