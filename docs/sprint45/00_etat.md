# Sprint 45 — carnet de bord

**Sujet** : recherche autonome — ARIA mène une recherche sur un sujet (requêtes construites à
partir de ses LLM, de sa mémoire et de la conversation), va chercher sur internet.
**Phase courante** : CLOS (2026-10-30) — tronçons 01 et 03, runs live 02 et 03 OK par Nico.
**Branche** : `feat/sprint45-recherche-autonome`.
**Audit** : `docs/sprint45/audit_recherche_autonome.md` (lire le TL;DR).

## Décisions arrêtées

- Déclenchement : **nouvelle opération** `WEB_RESEARCH` sur phrases explicites seulement
  (« fais une recherche sur », « renseigne-toi sur », « recherche approfondie »…) ; `WEB_SEARCH`
  reste la recherche rapide, inchangée ; pas de catégorie dans le classifier LLM (Nico, 2026-10-30).
  Raison : pas de recherche de 1-2 min sur « quel temps demain ».
- Profondeur : **une vague** — plan de 3 à 5 requêtes (LLM, à partir de la mémoire et de la
  conversation) → Tavily → lecture intégrale des 3 meilleures pages → rapport avec sources ;
  pas de relance sur les lacunes (Nico, 2026-10-30). Raison : durée bornée, testable.
- Trace : le rapport est **écrit comme un document lu** (`write_document` : fiche room
  `documents` + texte `aria_documents`) → retrouvé par `find_documents`, relu par « relis… »
  (Nico, 2026-10-30). Raison : réutilise les sprints 43-44, évite le défaut #137.

- Pipeline figé (OK Nico) : contexte (4 messages + 4 souvenirs via bridge) → plan LLM CHAT →
  `search` par requête → `extract` de 3 pages sans doublon → rapport DIGEST → `write_document`
  (source `recherche:<date>-<sha8>`, nom « Recherche : <sujet> ») → délégation REASONING +
  `skip_intent`. Détail : `01_recherche_autonome.md`.
- Sujet du run live : rotation des cultures (pas le paillage : la fiche « Paillis — Wikipédia »
  du palace pourrait passer avant le rapport au rappel).

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_recherche_autonome.md` | opération `WEB_RESEARCH` (phrases explicites) + `_handle_research` dans `web_router` + tests | ✅ `da87f6b` |
| 02 | `02_run_live.md` | run live (Nico), messages `run_live/messages.txt` | ✅ critère tenu (2026-10-30), mais rapport tronqué → 03 |
| 03 | `03_correctif_rapport.md` | plafond du rapport 3000 tokens + sujet sans phrase de déclenchement ; run live `run_live/messages_03.txt` | ✅ `f26ea21`, run live 03 OK |

## Dettes

- Ferme : aucune (sujet hors dettes).
- Nouvelles, inscrites au kickoff sprint 46 : #153 à #156.

## §REPRISE

Sprint clos. Run live 02 (18:25) : critère tenu en 36 s, mais rapport tronqué à 1500 tokens (sans
liste d'URL) et nom de document avec la phrase de déclenchement → tronçon 03. Run live 03 (18:35) :
rapport complet terminé par 9 URL, `report_tokens=1297`, pas de `hit max_tokens`, relecture complète
(`doc_reread OK`), aucun `ERROR`. Le rapport du run 03 tenait sous l'ancien plafond : la levée à 3000
n'est pas mise à l'épreuve sur un rapport long [n=1]. 438 tests verts.
Suite : `docs/sprint46/context_kickoff_sprint_46.md`.
