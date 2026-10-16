# Sprint 23 — état de conception

**Phase** : B — conception figée (OK Nico 2026-10-16), prête pour `/sprint-auto sprint 23`.
**Branche** : `feat/sprint23-lecture-url` (créée).

## Décisions arrêtées

- Cible : **#69 lecture d'URL collée** (Nico, 2026-10-16).
- Q1 : toute URL `https?://` dans le message → `URL_READ`, prioritaire sur
  `web_search` et sur « court → CONFIRMATION » ; heuristique seule, pas de
  catégorie LLM ; première URL seulement ; URL seule = résumé (Nico).
- Q2/Q3 (révisées) : **lire la page entière, en faire une synthèse, et c'est
  la synthèse qui part dans l'historique** (Nico). Mécanique : extract Tavily
  `format: "text"` → appel LLM « synthèse » sur la page complète, orientée
  par la consigne de Nico → message enrichi de la synthèse → délégation
  `LLMExecutionRouter` REASONING + `skip_intent` (le message enrichi, donc
  la synthèse, est écrit dans `aria_conversation` sans toucher
  `LLMExecutionRouter`).
- Groq exclu de l'appel « synthèse » : DeepSeek / Anthropic (Nico).
  Vérifié par appel réel : Wikipédia « Moteur Stirling » en `format: "text"`
  = 36 780 car. = 10 337 tokens prompt, `deepseek-flash` répond en 2,7 s
  [n=1], synthèse correcte.

- Q4 : rôle `LLMRole.DIGEST` → chaîne DeepSeek (`deepseek_model`) →
  Anthropic Haiku, sans Groq (Nico).
- Q5 : tranches de 100 000 car. [arbitraire]. Page plus longue → ARIA dit
  « j'ai lu les 100 000 premiers caractères (sur N), voici la synthèse… »
  et propose de lire la suite ; « oui » / « lis la suite » lit la tranche
  suivante (Nico). Mécanique proposée : marqueur de lecture partielle dans
  le message enrichi (donc dans l'historique), relu au tour suivant via le
  bridge — pas d'état nouveau, pas d'écriture hors `LLMExecutionRouter`.
- Q6 : synthèse `max_tokens=1000` ; feedback **dans les logs seulement**
  (`url_read OK page_chars, sent_chars, digest_tokens` + WARNING si la
  synthèse atteint `max_tokens`) ; rien sur Telegram (Nico : « autonomie,
  pas les rouages »).

- Découpage des tranches en fin de paragraphe (dernier `\n`, sinon fin de
  phrase, sinon espace), quitte à couper avant 100 000 car. (Nico).

## Carte des tronçons

| # | Kickoff | Statut |
|---|---------|--------|
| 01 | `01_lecture_url.md` — DIGEST sans Groq, `extract`, handler `URL_READ`, tranches, logs, heuristique URL | ✅ (pytest 278 verts, commit 44a8b1b) |
| 02 | `02_lire_la_suite.md` — « oui » / « lis la suite » via marqueur dans l'historique | ✅ (pytest 281 verts, commit 6975fe4) |
| 03 | `03_run_live.md` — run live (Nico) | ✅ A-G conformes (2026-10-16) ; D tronqué → tronçon 04 |
| 04 | `04_reponse_tronquee.md` — AnalystAgent `max_tokens` 800 → 1500 | ✅ (pytest 282 verts) ; re-live D à faire |

## Dettes

- Ferme : #69 (au run live OK).
- Ouvre : aucune pour l'instant (le message enrichi en historique reste
  rattaché à #73).

## §REPRISE

Lire `CLAUDE.md` + `docs/sprint23/audit_lecture_url.md` + ce fichier.
Tronçons 01 (44a8b1b), 02 (6975fe4) commités. Run live 03 : A-G conformes ;
D tronqué (« cloches de V ») car l'AnalystAgent plafonne la réponse REASONING
à `max_tokens=800` (hypothèse initiale `llm_router` défaut 1000 réfutée).
Tronçon 04 : 800 → 1500 global (arbitrage Nico), toutes réponses REASONING.
Relevé au live, à verser en dettes à la clôture : Groq 413 sur toute réponse
dès qu'une synthèse est dans l'historique (→ #73) ; réponse hors sujet
« Prochaine action… projet potager » ; intent parasite « vacances normandie
train » sur E.
Prochaine étape : re-live C + D par Nico, puis clôture.
