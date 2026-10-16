# Sprint 25 — état de conception

**Phase** : B — conception figée (OK Nico 2026-10-16), prête pour `/sprint-auto sprint 25`.
**Cible** : #73 Groq 413 / poids de l'historique.
**Branche** : `feat/sprint25-groq-413`.

## Décisions arrêtées

- 2026-10-16 — Cible sprint 25 = #73 Groq 413 (choix Nico : effet quotidien, sujet borné).
- 2026-10-16 — Piste A seule : un 413 Groq saute les autres entrées Groq de la
  requête (même modèle, même limite ITPM 7000 → échec certain). Pas de budget
  sur l'historique (B écartée : DeepSeek garderait moins de contexte).
- 2026-10-16 — Le fallback logue le corps des erreurs HTTP (~200 car.).

## Questions ouvertes

_(aucune)_

## Tronçons

| # | Kickoff | Statut |
|---|---|---|
| 01 | `01_saut_groq_413.md` — 413 Groq saute les autres Groq de la requête + corps HTTP dans le log de fallback | ✅ (pytest 282 verts) |
| 02 | `02_run_live.md` — run live (Nico) | ⏳ |

## Dettes

- Fermée par le sprint (si run live OK) : #73 (partiellement : Groq ne
  répond toujours pas aux conversations chargées, on cesse juste de le
  retenter 3 fois).

## §REPRISE

Lire `CLAUDE.md`, `docs/sprint25/audit_groq_413.md`, ce fichier.
Tronçon 01 ✅ (`llm/llm_router.py` + `tests/llm/test_groq_413.py`, non commité).
Prochaine étape : commit du tronçon 01, puis run live 02 par Nico.
