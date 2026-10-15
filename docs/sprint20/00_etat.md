# Sprint 20 — état de conception

**Phase** : B bis — figée (Q7-Q9), en attente du run live bis 04 (Nico).
**Branche** : `feat/sprint20-relances`.

## Décisions arrêtées

- Q1 : cible = relances après photo (#57, #59, #60, #61). Raison : un seul
  scénario observé au run live 03.

## Audit

`docs/sprint20/audit_relances_photo.md`. En bref :
- #57 confirmé : mode standard (`image_router.py` l. 142) n'écrit pas dans
  `aria_conversation` ; `chat_id` disponible dans `payload["metadata"]`.
- #59 confirmé et général : 4 intents sur 5 en prod sont parasites ; le
  recall n'a pas d'issue « pas d'intent » (IGNORE déclaré, jamais utilisé).
- #60 mal étiquetée : l'invention vient du modèle vision (photo + « évalue
  la position », mode standard), pas du LLM texte.
- #61 : cause = historique (« C'est ta maison de montagne », sprint 18) ;
  symptôme éteint depuis sprint 19 tronçon 04.

## Décisions arrêtées (suite)

- Q2 (#59) : les deux mécanismes — (a) le namer peut répondre « aucun »
  → `intent=None` (create et split) ; (b) recall contextuel (message +
  tour précédent). Raison : (a) seul ne rattache pas les relances de
  projet, (b) seul n'empêche pas les créations hors projet.
- Q3 (#57) : format du mode enrichi — user = `[Analyse visuelle : …]` +
  légende, assistant = description. Choix Nico.
- Q4 : #60 reformulée « vision : lecture fine inventée (position
  d'échecs), limite modèle », ouverte acceptée, hors sprint. #61 fermée
  sans code.

## Questions tranchées (suite)

- Q5 (Nico) : contexte via le namer, pas de concaténation. Q6 (Nico) :
  les 4 intents parasites restent dans `intents.json`.

- Q5 — mesure qui a motivé le choix. Mesure 2026-10-15 (embedder prod
  `paraphrase-multilingual-mpnet-base-v2`, cosine max vs intents
  « plantation tomates balcon est » / « potager herbes aromatiques
  fenêtre », seuil attach 0.45) [n=8 messages, 3 relances + 5 hors projet] :

  | Message (tour précédent : tomates ou échiquier) | seul | concat prev+msg |
  |---|---|---|
  | combien de pieds… (relance tomates) | 0.27 | **0.76** |
  | et quel engrais pour elles ? | 0.54 | 0.41 |
  | tu me disais quoi sur l'orientation ? | 0.20 | 0.28 |
  | évalue la position | 0.33 | 0.29 |
  | pourtant les noirs abandonnent ici | 0.32 | 0.27 |
  | je veux apprendre docker (après tomates) | 0.15 | **0.56 → faux attach** |
  | vacances en Normandie (après tomates) | 0.30 | **0.58 → faux attach** |
  | il fait beau aujourd'hui | 0.37 | 0.37 |

  La concaténation rattache à tort les changements de sujet [2 sur 2
  contre-exemples] et casse « quel engrais ». Alternative proposée : le
  contexte passe par le namer (LLM) — il reçoit tour précédent + message
  + noms des intents actifs et répond un nom existant (→ attach via
  `_find_by_name`, déjà dans `apply`), un nouveau nom, ou « aucun ».

## Carte des tronçons

| # | Kickoff | Dette | État |
|---|---|---|---|
| 01 | `01_photo_historique.md` — photo standard écrite dans `aria_conversation` | #57 | ✅ (259 verts) |
| 02 | `02_namer_contextuel.md` — namer contextuel, « aucun » → pas d'intent | #59 | ✅ (261 verts) |
| 03 | `03_run_live.md` — run live (Nico) | — | ⚠️ partiel (3 critères sur 6, voir §Run live 03) |
| 04 | `04_run_live_bis.md` — purge parasites (faite) + relances | #59 | ⏳ |

Esprit (Nico) : ARIA doit juger, comme un humain, si un intérêt vaut
d'être retenu comme intent.

## Dettes

- Visées : #59 (fermée si run live bis OK). #57 fermée (Q8).
- Fermée sans code : #61 (cause = historique, symptôme éteint).
- Reformulée, ouverte acceptée : #60 → « vision : lecture fine inventée
  (position d'échecs), limite modèle ».
- Notées, hors sprint : `IntentActionType.IGNORE` déclaré jamais utilisé ;
  les 4 intents parasites passés en `abandoned` (Q7, remplace Q6).

## Run live 03 (2026-10-15, 22:51-22:55)

| # | Message | Observé | |
|---|---|---|---|
| 1 | photo sans légende | `conversation_write OK key=6895898630` | ✅ |
| 2 | « évalue la position » | « je ne vois pas l'image » ; attach parasite `evaluation position` | ❌ |
| 3 | « j'ai envoyé la photo juste avant » (remplace le message prévu) | même refus ; même parasite | ❌ |
| 4 | « il fait beau aujourd'hui » | `intent SKIPPED reason=namer_aucun` · `memory_write SKIPPED` | ✅ |
| 5 | « combien de litres de terreau par pied » | attach parasite `surface pieds conseils` (pas tomates) | ❌ |
| 6 | « je veux apprendre docker cet hiver » | `apprentissage docker` créé, 6 intents | ✅ |

Diagnostic :
- #57 : mécanisme OK. Dump `aria_conversation` (lecture seule) : tours
  photo écrits à 20:52:24/27 UTC, historique chargé à 20:52:36 (20
  derniers messages) → la description était dans le contexte du LLM.
  Le refus vient de la description elle-même (aucune case, aucune pièce
  nommée = #60) ; « je ne vois pas l'image » est une formulation fausse
  du modèle (rien ne lui dit que `[Analyse visuelle : …]` est une photo).
- #59 : « aucun » et création OK. Échecs 2, 3, 5 = recall `attach`
  (cosine message ↔ nom d'intent ≥ 0.45) sur les parasites,
  créés aux runs précédents par ces mêmes messages ; le namer
  n'est jamais consulté en attach. Cause = Q6 (parasites conservés).
- Levier sans code : `IntentStatus.ABANDONED` (`intent/intent.py:30`)
  est relu depuis le JSON (`intent_store.py:36`) et le recall ne garde
  que `status == "active"` (`intent_recall_engine.py:73`). Passer les
  parasites en `"abandoned"` les retire du recall, réversible. Aucun
  caller prod de `abandon()`. Édition JSON service arrêté (sinon le
  service réécrit le fichier).

## Décisions arrêtées (run live 03)

- Q7 (#59, revient sur Q6) : les 4 parasites passent en `status:
  "abandoned"` dans `~/.aria/intents.json` (opération données, service
  arrêté, réversible). Pas de namer en attach. Raison : sans code ; le
  namer « aucun » limite les nouveaux parasites.
- Q8 (#57) : fermée telle quelle. Mécanisme validé ; le refus résiduel
  relève de #60 (description sans position).
- Q9 : tronçon 04 = run live bis ciblé (purge + relances 2, 3, 5).

## §REPRISE

Lire `CLAUDE.md`, ce fichier. Tronçons 01 (`2359a4f`) et 02 (`07a890c`)
commités. Run live 03 partiel, diagnostic ci-dessus.
Q7-Q9 tranchées, purge faite (`intents.json.bak-sprint20`).
Prochaine étape : run live bis par Nico (`04_run_live_bis.md`), puis clôture.
