# Sprint 25 — état de conception

**Phase** : CLOS (2026-10-19) — run live 02 OK.
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
| 01 | `01_saut_groq_413.md` — 413 Groq saute les autres Groq de la requête + corps HTTP dans le log de fallback | ✅ `3daaa45` (pytest 282 verts) |
| 02 | `02_run_live.md` — run live (Nico) | ✅ 2026-10-19 |

## Dettes

- #73 partiellement résolue : Groq ne répond toujours pas aux conversations
  chargées (413, `Limit 7000`), on cesse juste de le retenter 3 fois.
- #31 : nouvelle quarantaine HNSW au run live (2026-10-19 08:31:46).

## Run live 02 (2026-10-19, 20 messages d'historique)

- Une seule ligne `[LLM FALLBACK] groq failed: … 413 …` avec le corps
  (`ITPM): Limit 7000, Requested 7…`, tronqué). ✅
- `groq_2` / `groq_3` : `skipped (413 sur groq)`, aucun `failed`. ✅
- `deepseek` a répondu 3 s après le 413 [horodatage à la seconde, n=1]
  (attendu ~1-2 s, ~4 s au run live 24-02) : l'écart restant est la
  latence propre de DeepSeek (skips à :57, réponse à :59).
- Réponse Telegram pertinente (progression Docker en 4 phases).

## §REPRISE

Sprint clos. Suite : `docs/sprint26/context_kickoff_sprint_26.md`.
