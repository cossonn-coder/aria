# Sprint 31 — état de conception

**Phase** : CLOS (2026-10-23) — tronçon 01 validé live, tag `sprint-31`.
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
| 01 | `01_saut_groq_seuil_attente.md` — saut préventif Groq > 12 000 car. (#73/#86) + ⏳ à 20 s (#111) | ✅ (353 tests verts, `1e29e0a`) |
| 02 | `02_run_live.md` — run live (Nico) | ✅ (2026-10-23, validé par Nico) |

## Run live (2026-10-23, 09:46-09:52)

| Message | Durée réception → `pipeline done` | ⏳ | Groq |
|---|---|---|---|
| 1. `salut` (1er après redémarrage) | 11 s (dont ≈ 6 s chargement mpnet) | non ✓ | sauté, 50 394 car. ✓ |
| 2. partie AaronDias16 | 60 s | un seul ✓ | — |
| 3. `salut` | 13 s ✗ (attendu < 10 s) | non ✓ | sauté ×2, 319 023 et 161 407 car. ✓ |
| 4. `tu te souviens…` | 8 s ✓ | non ✓ | sauté, 38 486 car. ✓ ; la réponse cite la partie |

Aucune ligne `413` (la veille, 23:32 : 413 puis détour). Le message 3 dépasse 10 s à cause
de #74 (deux appels DeepSeek), hors sprint : Nico valide le sprint.

Constats :
- #74 reproduit (4e occurrence) : `salut` après l'analyse → « Prochaine action : Partie contre
  AaronDias16 2026.10.22 Dutch Defense Normal Variation » (`agents/executor_agent.py:71`) ;
  journal : intent `jeux echecs` résolu sur le `salut`, deux appels DeepSeek.
- Historique de 20 messages à 319 023 car. envoyé à DeepSeek (nouvelle dette #113).
- #112 observé : le `salut` envoyé pendant l'analyse n'est traité qu'après elle [n=1].
- Quarantaine `.drift-20261023-094909` au démarrage (sqlite 1014 s plus récent), sans effet visible (#105).

## Dettes

- Fermées : #111 ; #73 et #86 (Groq sauté au-delà de 12 000 car., plus de 413 au live).
- Ouvertes par le run : #113 historique lourd ; #74 passe à n=4.

## §REPRISE

Sprint clos. Suite : `docs/sprint32/context_kickoff_sprint_32.md`, puis `/conception sprint 32`.
