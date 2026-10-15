# Sprint 19 — tronçon 04 : consignes du message enrichi (langue + projet)

Prérequis : tronçons 01 et 02 commités sur `feat/sprint19-vision`.
Origine : run live 03 (voir `00_etat.md` § Run live 03 et § Audit tronçon 04).

## Objectif

Une photo avec légende interrogative (chemin enrichi → LLM texte) :
1. reçoit une réponse **dans la langue de la question** (français par
   défaut) ;
2. **ne mentionne pas les projets** de Nico quand la description ne
   justifie pas de lien.

## Diagnostic (vérifié au code le 2026-10-15)

- `ImageRouter._handle_input_enriched` (`execution/routers/image_router.py`,
  ~l. 172-189) construit `enriched_message` :
  `[Analyse visuelle : …]` + `[Consigne : ne rattache cette photo à un
  projet de Nico que si la description le justifie clairement.]` + caption,
  puis `LLMExecutionRouter.execute` en REASONING → `AnalystAgent`.
- La règle de langue n'existe que dans le prompt vision avec légende
  (`llm/image_router.py` ~l. 131-143). Le LLM texte n'en a aucune et
  `user.md:4` dit « Langue : français » → E (« What's this? ») a répondu
  en français.
- La consigne projet ne dit pas quoi faire en l'absence de lien → le LLM
  écrit « Il n'y a pas de lien avec tes projets actifs ».

## À faire

Fichier unique de prod : `execution/routers/image_router.py`,
`_handle_input_enriched`, construction de `enriched_message`.

1. Consigne projet reformulée (décision Q8, texte arrêté) :
   « Ne rattache cette photo à un projet de Nico que si la description le
   justifie clairement ; sinon, ne mentionne pas ses projets. »
2. Consigne de langue (décision Q7 a), même schéma que le prompt vision du
   tronçon 01 — une ligne FR **et** une ligne EN (la version FR seule n'a
   pas suffi au tronçon 01 [n=2 essais]) :
   - FR : réponds en français, sauf si la question de l'utilisateur est
     dans une autre langue : réponds alors dans cette langue.
   - EN : `Language rule: if the user's message is not in French, write
     your whole answer in the language of that message.`
   Formulation exacte libre tant que l'intention est tenue.
3. Mettre à jour la docstring (format du message injecté) et le
   commentaire au-dessus de `enriched_message`.

## Test (cas nominal)

Étendre `test_message_enrichi_contient_analyse_visuelle`
(`tests/images/test_interrogative_vision_pipeline.py` ~l. 272) :
asserter que `call_payload["content"]` contient la consigne projet
reformulée (« ne mentionne pas ses projets ») et la ligne
`Language rule:`.

Vérification VM facultative (pas obligatoire) : si un appel réel est
simple à monter, « What is this? » → réponse EN. Sinon le run live 05
tranche.

## Ne PAS faire

- Toucher `soul.md`, `user.md`, le prompt AnalystAgent (`PROMPT`) ou
  `LLMRouter.build_base_system_prompt` (décision Q7 : règle limitée au
  chemin enrichi).
- Toucher le prompt vision (`llm/image_router.py`) ni le drapeau
  `skip_intent`.
- Traiter les dettes hors scope : intents parasites des relances texte,
  position inventée en mode texte, « maison de montagne » via
  l'historique, photo absente de `aria_conversation` en mode standard.

## Critère de fin

- `./venv/bin/pytest tests/ -q` vert (baseline 258).
- `tests/agents/test_analyst_prompt_guard.py` vert (non touché).
- `00_etat.md` : tronçon 04 ✅ + §REPRISE.
