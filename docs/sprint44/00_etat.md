# Sprint 44 — carnet de bord

**Sujet** : recherche des documents lus — #146 (page introuvable par le sens) + #147
(relecture sans critère d'absence).
**Phase courante** : CLOS (2026-10-30) — run live 02 OK par Nico, tag `sprint-44`.
**Branche** : `feat/sprint44-recherche-documents`.
**Audit** : `docs/sprint44/audit_recherche_documents.md` (lire le TL;DR).

## Carte des tronçons

| # | Kickoff | Objet | État |
|---|---|---|---|
| 01 | `01_recherche_documents.md` | `bridge.find_documents` (room entière + filtre par mots porteurs) ; relecture → 1re fiche correspondante ou `NOT_FOUND` ; rappel global → fiche en tête de la section épisodique, log `document_recall` | ✅ |
| 02 | `02_run_live.md` | run live (Nico), messages `run_live/messages.txt` | ✅ |

## Décisions arrêtées

- Cible : #146 + #147 (choix de Nico, 2026-10-30) : même chemin de lecture.
- Mécanisme : recherche de documents dédiée dans le bridge (pool = toute la room
  `documents`, filtre lexical), utilisée par la relecture et ajoutée au rappel global.
  Raison : ne dépend ni du nombre d'images `general` ni des doublons.
- Critère d'absence : règle lexicale (mots ≥ 4 lettres, sans accents, hors courte liste de
  mots vides) ; aucun mot porteur (« relis le document ») → meilleure fiche comme aujourd'hui.
  Raison : sans appel LLM, sert aussi au rappel global.
- Fiche trouvée injectée **en tête** de la section épisodique via un paramètre de
  `build_context_block`, même si la session de l'intent est pleine (≥ 3 hits ignore le global).
- #143 (doublons) : reste en dette (« c'est juste un test »).
- Recherche autonome sur un sujet : **sprint 45 dédié** (choix de Nico).

## Dettes (inscrites au kickoff sprint 45)

- Ferme si run live OK : #146, #147.
- Nouvelles :
  - #149 Échecs : le compte rendu d'une partie envoyée sur Telegram doit montrer **en priorité**
    des miniatures sur les coups manqués de Nico (explosif, stratégique, piège, faute, gaffe) —
    « c'est en étudiant mes mauvais coups que je vais le plus apprendre » ; garder une miniature
    pour un coup spectaculaire de la partie s'il y en a un (demande de Nico, 2026-10-30).
  - #150 Rappel épisodique : les hits room `general` (images) sont retirés par le bridge après la
    coupe de mempalace → moins de souvenirs que `top_k` (n=4 → 3) [1 requête, audit sprint 44].
  - #151 L'opération classée par LLM et le nombre de souvenirs rappelés ne sont pas journalisés.
  - Sujet sprint 45 (hors dettes) : recherche autonome — ARIA mène une recherche sur un sujet,
    construit ses requêtes à partir de ses LLM, de sa mémoire et du contexte de conversation,
    va chercher sur internet. Existant : `WEB_SEARCH` = 1 requête → 5 extraits Tavily.

## §REPRISE

Sprint clos (2026-10-30). Tronçon 01 commité (`6a28a81`, 433 tests verts) ; run live 02 OK
par Nico (#146, #147 résolues). Points à surveiller du tronçon 01 inscrits en dette #152.
Suite : `docs/sprint45/context_kickoff_sprint_45.md`, puis `/conception sprint 45`.
