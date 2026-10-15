# Sprint 20 — audit « relances après photo » (#57, #59, #60, #61)

Date : 2026-10-15. Code au commit `b9336ac` (main, tag `sprint-19`).
Sources : code lu intégralement (chemins ci-dessous), `journalctl -u aria`
du 2026-10-15, palace prod lu en **sqlite lecture seule**
(`file:…/chroma.sqlite3?mode=ro`), `~/.aria/intents.json`.

## 1. Reconstitution du run live 03 (séquence échiquier)

Horodatages journalctl en heure locale (UTC+2), palace en UTC.

| Heure locale | Envoi Nico | Chemin | Écrit dans `aria_conversation` ? | Intent |
|---|---|---|---|---|
| 18:11:03 | Photo échiquier + « c'est quoi? » | enrichi (`[IMAGE ENRICHED]`) | oui : message enrichi complet (`[Analyse visuelle : …échiquier… WOGAMAT]` + consigne + question) et réponse | SKIPPED |
| 18:11:44 | « évalue la position » | texte | oui | **créé `evaluation position`** |
| 18:12:17 | Photo échiquier + « évalue la position » | **standard** (légende non interrogative) | **non** | — |
| 18:13:05 | « pourtant les noirs abandonnent ici » | texte | oui | **créé `abandon des noirs`** |

Réponses réelles (palace, `aria_conversation`) :

- 18:11:48 « évalue la position » → « Je ne peux pas évaluer la position
  […] je ne vois pas l'image ». **Pas d'invention** : la description
  vision de 18:11 ne contient aucune case. Réponse correcte.
- 18:12:17 photo + « évalue la position » → réponse **du modèle vision
  seul** (artefact `aria_episodic`) : « Les Noirs ont déjà développé leur
  dame en d8 et leur cavalier en f6, tandis que les Blancs […] un fou en
  c4. Aucun camp ne présente de déséquilibre matériel évident ». C'est la
  « position inventée au 2e essai » : contradiction avec « les noirs
  abandonnent ici ».
- 18:13:09 « pourtant les noirs abandonnent ici » → « Sans voir
  l'échiquier, je ne peux pas confirmer *pourquoi* ». Le LLM texte ignore
  la description de 18:12 : elle n'est pas dans l'historique (#57).

## 2. #57 — photo standard absente de l'historique : CONFIRMÉ

`execution/routers/image_router.py` `_handle_input` (l. 92-142) :

- l. 117-126 : vision puis `write_image_artifact` (wing `aria_episodic`).
- l. 132-139 : mode enrichi seulement si `is_interrogative_caption` →
  délègue à `LLMExecutionRouter`, qui écrit la conversation
  (`llm_router.py` l. 255-260, `write_conversation_turn` ×2).
- l. 142 : mode standard → `return {"text": artifact.caption or ""}`,
  **aucun** `write_conversation_turn`.

Lecture de l'historique : `mempalace_bridge.load_conversation_history`
(l. ~243-271) filtre `wing=aria_conversation` + `room=chat_id`. Les
artefacts image (`aria_episodic`) n'y figurent jamais.

`chat_id` est bien disponible côté image : `telegram_interface.py` l. 105
`metadata={"chat_id": chat_id}` → kernel (`core/kernel.py` l. 157) →
`payload["metadata"]` (le chemin enrichi l'utilise déjà : clé
`6895898630` dans les logs).

Écrivain disponible : `memory/writer.py` `write_conversation_turn`
(l. 173-209), wing/room structurels posés après `extra`. Règle 1
respectée si l'appel est fait dans `ImageExecutionRouter` (handler de
l'opération ; il écrit déjà l'artefact).

## 3. #59 — intents parasites : CONFIRMÉ, et plus large que « après photo »

`~/.aria/intents.json` au 2026-10-15 : **5 intents, 1 seul légitime**.

| Intent | Message source (palace) | Verdict |
|---|---|---|
| `plantation tomates balcon est` | « je prévois de planter des tomates cerises… » | légitime |
| `surface pieds conseils` | « combien de pieds tu me conseilles pour la surface ? » | relance du projet tomates, aurait dû s'y rattacher |
| `orientation scolaire professionnelle` | « tu me disais quoi déjà sur l'orientation? » (orientation du balcon) | contresens complet |
| `evaluation position` | « évalue la position » | relance de photo |
| `abandon des noirs` | « pourtant les noirs abandonnent ici » | relance de photo |

Mécanique (`intent/intent_recall_engine.py` l. 49-125) : le message
**seul** est embarqué et comparé (cosine) aux embeddings des **noms**
d'intents actifs. ≥ 0.45 → `attach` ; ≥ 2 candidats > 0.40 → `split` ;
sinon → `create`. Il n'existe **aucune issue « pas d'intent »** :
`IntentActionType.IGNORE` est déclaré (`intent/intent_decision.py` l. 14)
mais jamais produit ni traité (`grep` : 0 usage). Tout message texte hors
`skip_intent` finit donc rattaché ou crée un intent.

Côté mutation (`intent/intent_engine.py` `apply`, l. 125-195) :
- `create` : nom via `extract_intent_name` (`llm/intent_namer.py`,
  prompt « extrait le sujet en 2 à 5 mots », jamais de refus possible),
  puis dédoublonnage exact et sémantique (seuil 0.55) sur le nom.
- `split` : **pas** d'appel au namer (`llm_router.py` l. 141 ne le fait
  que pour `create`) → nom = `message[:60]`.

Les relances courtes (« évalue la position », « et quel engrais ? »)
sont pauvres sémantiquement : sans le contexte du tour précédent, la
similarité au nom d'intent reste sous le seuil → `create`.

Chemin `intent=None` déjà éprouvé (sprint 19, `skip_intent`) :
`retrieve_by_intent` sauté, `AnalystAgent` reçoit « aucun », planner et
executor gardent `if ctx.intent is None`, critic ne tourne qu'en phase
`execution` (impossible sans intent). Conséquence : `write_interaction`
sauté (`memory_write SKIPPED reason=no_intent_resolved`), l'échange
reste dans `aria_conversation` seulement.

## 4. #60 — « invention en mode texte » : MAL ÉTIQUETÉE

Le LLM texte n'a rien inventé (§1 : il refuse d'évaluer faute de
données). L'invention vient du **modèle vision** (deepseek-flash), en
mode standard, sur la légende « évalue la position » : il lit des cases
précises (d8, f6, c4) qu'il ne peut pas fiabiliser, malgré la consigne
anti-invention du prompt avec légende (`llm/image_router.py` l. ~131-143).
Limite modèle sur la lecture fine (position d'échecs) ; aucun défaut de
code identifié.

Note : « évalue la position » n'est pas reconnue comme interrogative
(`is_interrogative_caption`, `cognition/cognitive_classifier.py`
l. 126-144, marqueurs de question uniquement) → mode standard. Le mode
enrichi n'aurait pas évité l'invention (la description vision serait la
même), il ne fait que l'habiller.

## 5. #61 — intent supprimé encore cité : CAUSE CONFIRMÉE, symptôme éteint

Historique `aria_conversation` à 15:15 UTC : la réponse ARIA « C'est ta
**maison de montagne** » (sprint 18, avant suppression de l'intent).
À 18:11 local, l'historique chargé comptait 16 messages et contenait ce
tour → le LLM a cité « maison de montagne » dans sa liste de projets.
Depuis le tronçon 04 du sprint 19 (consigne « sinon, ne mentionne pas
ses projets »), la mention a disparu (run live 05). L'historique est
désormais à 20 messages et ce tour en est sorti par glissement.
Rien à corriger : l'historique rapporte ce qui a été dit.

## 6. Synthèse

| # | Statut audit | Piste |
|---|---|---|
| 57 | confirmé | écrire user/assistant dans `aria_conversation` en mode standard |
| 59 | confirmé, général | permettre « pas d'intent » au moment de créer |
| 60 | mal étiquetée | limite vision ; reformuler la dette |
| 61 | cause confirmée, symptôme éteint | fermer |
