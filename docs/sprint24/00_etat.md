# Sprint 24 — état de conception

**Phase** : CLOS (run live 02 OK, 2026-10-16).
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
| 01 | `01_generation.md` — Pollinations avec clé + secours anonyme, HF hors table, prompt brut, photo → toujours IMAGE_INPUT, mots-clés resserrés | ✅ `2d893ec` (281 verts) |
| 02 | `02_run_live.md` — run live (Nico) | ✅ A, C, D conformes ; B technique OK (clé, 4 s), contenu infidèle — ignoré (Nico) |

## Dettes

- Fermée : #44.
- Ouverte : #77 image-to-image (photo + légende de génération ; Pollinations
  accepte `image=` mais il faut une URL publique de la photo).
- Ouverte : #78 `llm/image_gen/hf_client.py` + `config.hf_image_model` morts.
- Constatée au live : #73 (Groq 413 avec 20 messages d'historique, message C,
  bascule DeepSeek) — déjà ouverte.
- Écartée par Nico : fidélité du prompt FR brut (B : le chat n'arrose pas) [n=1].
- Notée : génération Pollinations = 404 sur un prompt enrichi [n=1, cause
  non isolée] — devient sans objet sans bloc contexte.

## §REPRISE

Sprint clos (tag `sprint-24`). Suite : `docs/sprint25/context_kickoff_sprint_25.md`.
