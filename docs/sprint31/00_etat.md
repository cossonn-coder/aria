# Sprint 31 — état de conception

**Phase** : B figée (2026-10-23) — prêt pour `/sprint-auto sprint 31`.
**Branche** : `feat/sprint31-messages-courts`.

## Décisions arrêtées

- Q1 cible = messages courts : #111 (⏳ sur un `salut`) + #73/#86 (détour 413 Groq). Raison : gain ressenti à chaque message, petit sprint. (2026-10-23)
- Q2 #73 : saut préventif de Groq dans `LLMRouter.complete()` quand le payload dépasse un seuil
  (sans appel HTTP ni sommeil), DeepSeek garde tout l'historique. Raison : B/C écartées au
  sprint 25 ; Groq reste sur les petites requêtes. (2026-10-23)
- Q3 seuil = 12 000 caractères (somme des `content`, ou longueur du prompt). Raison : prudent
  face à ITPM 7000 (2,5-4 car./token). (2026-10-23)
- Q4 #111 : `WAIT_NOTICE_SECONDS` 10 → 20. Raison : message court max 17 s [n=4], analyse ≥ 41 s. (2026-10-23)

## Questions ouvertes

(aucune)

## Tronçons

| # | Kickoff | État |
|---|---|---|
| 01 | `01_saut_groq_seuil_attente.md` — saut préventif Groq > 12 000 car. (#73/#86) + ⏳ à 20 s (#111) | ⏳ |
| 02 | `02_run_live.md` — run live (Nico) | ⏳ |

## Dettes

- Fermées si le sprint passe : #111 ; #73 et #86 (côté latence ; Groq reste exclu des gros payloads).
- Constat noté, hors sprint : #74 corrélé à l'historique chargé (3e occurrence après une analyse).

## §REPRISE

Lire `CLAUDE.md`, ce fichier, `audit_messages_courts.md`, puis le kickoff du premier tronçon ⏳.
Prochaine étape : `/sprint-auto sprint 31`.
