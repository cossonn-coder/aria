# Sprint 20 — état de conception

**Phase** : B — conception figée (OK Nico 2026-10-15), prête pour `/sprint-auto sprint 20`.
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
| 03 | `03_run_live.md` — run live (Nico) | — | ⏳ |

Esprit (Nico) : ARIA doit juger, comme un humain, si un intérêt vaut
d'être retenu comme intent.

## Dettes

- Visées : #57, #59 (fermées si run live OK).
- Fermée sans code : #61 (cause = historique, symptôme éteint).
- Reformulée, ouverte acceptée : #60 → « vision : lecture fine inventée
  (position d'échecs), limite modèle ».
- Notées, hors sprint : `IntentActionType.IGNORE` déclaré jamais utilisé ;
  les 4 intents parasites restent dans `intents.json` (Q6).

## §REPRISE

Lire `CLAUDE.md`, ce fichier, puis le kickoff du premier tronçon ⏳.
Tronçon 01 ✅ commité (`2359a4f`). Tronçon 02 ✅ (non commité à la
sortie du sous-agent) : namer contextuel (intents actifs + tour user
précédent, « aucun » → `None`), historique chargé avant l'intent,
namer appelé en create/split, `SPLIT` dédoublonne par nom ; 2 tests.
Prochaine étape : run live 03 par Nico (`03_run_live.md`).
