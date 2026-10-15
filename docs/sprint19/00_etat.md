# Sprint 19 — état (vision lisible, dettes #45-#51)

**Phase** : B figée le 2026-10-15 — prêt pour `/sprint-auto sprint 19`
**Branche** : `feat/sprint19-vision`
**Docs** : `context_kickoff_sprint_19.md` (cadrage), `audit_vision.md` (audit 2026-10-15)

## Carte des tronçons

| # | Kickoff | Qui | État |
|---|---|---|---|
| 01 | `01_vision.md` — DeepSeek d'abord (raisonnement coupé), prompt FR sobre + règle de langue, `max_tokens` 1024, MIME, vide = échec, logs (#45-#50) | /sprint-auto | ⏳ |
| 02 | `02_photo_sans_intent.md` — photo interrogative sans résolution d'intent (#51) | /sprint-auto | ⏳ |
| 03 | `03_run_live.md` — suppression intent artefact + 5 photos | Nico | ⏳ |

## Décisions arrêtées (2026-10-15, Nico)

- Q1 (a) : mode standard = nouveau prompt vision seulement (description
  brute, FR, courte, anti-invention). Pas de passage par la chaîne LLM.
  Raison : défaut de fond = prompt ; la chaîne LLM hériterait de #51.
- Q2 (b) : chaîne vision DeepSeek `deepseek-flash` (raisonnement coupé)
  d'abord, puis groq ×3 en secours. Raison : groq qwen3.8 décrit une photo
  comme plusieurs vues [4/6 sorties] ; DeepSeek plus juste [n=3 photos].
- Q3 : #51 dans le sprint.
- Q4 (a) : photo interrogative = aucune résolution/mutation d'intent
  (drapeau `metadata["skip_intent"]` → `LLMExecutionRouter` saute étapes
  2-3, `intent=None` ; garde `ctx.intent is None` dans `AnalystAgent` sans
  toucher `PROMPT`). Le lien projet reste possible via `[Projets actifs]`
  + souvenirs globaux du context_block. Consigne ajoutée au message
  enrichi : « ne rattache à un projet que si la description le justifie ».
  Raison : seule option qui supprime le mécanisme ; (b) attach-sur-match-fort
  reste branchable plus tard si le run live le demande.
- Q5 : supprimer l'intent « maison de montagne » de `~/.aria/intents.json`
  au run live (service arrêté, sinon réécrit depuis la RAM).
- Q6 : découpage 01 / 02 / 03 et propositions en bloc acceptés.
- Règle de langue (Nico) : français par défaut, sinon la langue de la question.

## Dettes

Visées par le sprint : #45, #46, #47, #48, #49, #50, #51 (fermées si le
run live passe).
À créer au kickoff sprint 20 :
- Mode standard : la photo n'est pas écrite dans `aria_conversation`
  (relance texte sans la photo dans l'historique).
- #51 option (b) : rattachement photo → intent sur correspondance forte,
  si le run live montre une perte de contexte projet.

## §REPRISE

Conception figée. Prochaine étape : `/sprint-auto sprint 19` (tronçons
01 puis 02), puis run live 03 par Nico.
