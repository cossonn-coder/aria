# Sprint 19 — état (vision lisible, dettes #45-#51)

**Phase** : B figée le 2026-10-15 (tronçon 04 ajouté après run live 03) — prêt pour `/sprint-auto sprint 19`
**Branche** : `feat/sprint19-vision`
**Docs** : `context_kickoff_sprint_19.md` (cadrage), `audit_vision.md` (audit 2026-10-15)

## Carte des tronçons

| # | Kickoff | Qui | État |
|---|---|---|---|
| 01 | `01_vision.md` — DeepSeek d'abord (raisonnement coupé), prompt FR sobre + règle de langue, `max_tokens` 1024, MIME, vide = échec, logs (#45-#50) | /sprint-auto | ✅ |
| 02 | `02_photo_sans_intent.md` — photo interrogative sans résolution d'intent (#51) | /sprint-auto | ✅ |
| 03 | `03_run_live.md` — suppression intent artefact + 5 photos | Nico | ✅ partiel (E ❌) |
| 04 | `04_consignes_enrichi.md` — message enrichi : règle de langue FR+EN, consigne projet « sinon n'en parle pas » | /sprint-auto | ⏳ |
| 05 | `05_run_live.md` — 3 photos (E' EN, C' sans projets, D' châssis) | Nico | ⏳ |

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
- Q7 (a) : règle de langue dans le message enrichi seulement (ligne FR +
  ligne EN). Raison : défaut limité au chemin enrichi ; `soul.md`/`user.md`
  toucheraient tout ARIA.
- Q8 : consigne projet « … que si la description le justifie clairement ;
  sinon, ne mentionne pas ses projets ». Nico rattachera lui-même si besoin.
- Q9 : tronçon 04 (code + test du contenu enrichi) puis 05 run live
  (3 photos E'/C'/D').

## Dettes

Visées par le sprint : #45, #46, #47, #48, #49, #50, #51 (fermées si le
run live passe).
À créer au kickoff sprint 20 :
- Mode standard : la photo n'est pas écrite dans `aria_conversation`
  (relance texte sans la photo dans l'historique).
- #51 option (b) : rattachement photo → intent sur correspondance forte,
  si le run live montre une perte de contexte projet.
- Relances texte après photo : intents parasites créés
  (`evaluation position`, `abandon des noirs`, run live 03).
- Mode texte : invention de détails absents de la description
  (position d'échecs inventée, run live 03).
- Intent supprimé (« maison de montagne ») encore cité via l'historique
  conversationnel (hypothèse non vérifiée).

## Run live 03 (2026-10-15, Nico)

- ✅ A, B, C, D en FR, non coupées ; `[VISION] deepseek` à chaque photo
  [n=5], aucun fallback ; `intent SKIPPED reason=skip_intent` en C/D/E ;
  aucun intent créé par une photo.
- ❌ E « What's this? » → réponse en FR.
- ⚠️ C et E : mention non sollicitée « pas de lien avec tes projets actifs ».
- C cite encore « maison de montagne » alors que l'intent est supprimé
  (hypothèse non vérifiée : historique de 16 messages).
- Relances texte « évalue la position » : 2 intents parasites
  (`evaluation position`, `abandon des noirs`) + position inventée au
  2e essai. Hors sprint → dettes sprint 20.

## Audit tronçon 04 (2026-10-15)

- Chemin enrichi : `ImageRouter._handle_input_enriched`
  (`execution/routers/image_router.py` ~l. 172-189) construit
  `[Analyse visuelle : …]` + `[Consigne : ne rattache …]` + caption, puis
  `LLMExecutionRouter` REASONING → `AnalystAgent` (groq qwen).
- La règle de langue n'existe que dans le prompt vision avec légende
  (`llm/image_router.py` ~l. 131-143, ligne FR + ligne EN). Rien côté LLM
  texte : `soul.md` muet sur la langue, `user.md:4` « Langue : français,
  tutoiement », historique FR → la réponse finale part en FR.
- La consigne projet dit quand rattacher, pas quoi faire sinon → le LLM
  commente l'absence de lien.
- Aucun test n'asserte le contenu du message enrichi.

## §REPRISE

Tronçon 01 ✅ (2026-10-15, non commité) : DeepSeek d'abord (`thinking`
désactivé via `extra`), prompts FR sobres, `max_tokens` 1024, MIME par
extension, réponse vide = échec, logs `[VISION] <provider> (<model>) a
répondu.` (vision seulement), `image_write OK`, `[IMAGE ENRICHED]` en info.
Pytest 257 verts. Vérif VM sans mock : FR sans légende [n=1 photo],
EN sur « What is this? » et FR sur « c'est quoi ? » [n=2 photos], deepseek seul, aucun fallback.
Écart kickoff : la règle de langue en français seule ne suffisait pas
(réponse FR à « What is this? » [n=2 essais]) → ajout d'une ligne en
anglais « Language rule: ... » dans le prompt avec légende.
Tronçon 01 commité (195aced).

Tronçon 02 ✅ (2026-10-15, non commité) : `ImageRouter._handle_input_enriched`
pose `metadata["skip_intent"]=True` + consigne « ne rattache cette photo à
un projet de Nico que si la description le justifie clairement » ;
`LLMExecutionRouter._run_pipeline` saute étapes 2-3 (log
`intent SKIPPED reason=skip_intent`, `intent=None`, `recall=None`) ;
`AnalystAgent` : `intent_name` = « aucun » si `ctx.intent is None`
(`PROMPT` inchangé, garde-fou vert). Chemin REASONING = `analyst` seul
(`controller_agent.py`) → aucun autre agent exposé à `None`.
Pytest 258 verts. Aucun écart au kickoff.
Prochaine étape : run live 03 par Nico.

Run live 03 consigné ci-dessus. Tronçon 04 figé (Q7-Q9, 2026-10-15).
Prochaine étape : `/sprint-auto sprint 19` (tronçon 04), puis run live 05 par Nico.
