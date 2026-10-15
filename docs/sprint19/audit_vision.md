# Sprint 19 — audit du chemin vision (2026-10-15)

Base : `main` @ `0841bd6` (merge sprint 18). Dettes ciblées : #45-#51.

## 1. Chemin de données (photo Telegram → réponse)

1. `interfaces/telegram_interface.py:76-102` `_handle_photo` : télécharge
   `photo[-1]` vers `received_images/<file_id>.jpg` (JPEG, 1280×960 sur
   les 3 photos du run live), crée un Event IMAGE
   `{"file_path", "caption"}`.
2. `core/kernel.py:48-49,79-80` : IMAGE_INPUT → `image_router`
   (`ImageExecutionRouter(internal_router=InternalImageRouter(), …)`).
3. `execution/routers/image_router.py:89-140` `_handle_input` :
   - appelle `internal_router.handle_input(ImageInput(path, caption))` ;
   - `write_image_artifact(artifact, intent_id=…)` (l. 119-124), log
     seulement en cas d'erreur ;
   - si `is_interrogative_caption(caption)` et `llm_execution_router`
     injecté → `_handle_input_enriched` (l. 142-183) ;
   - sinon **mode standard** : `return {"text": artifact.caption}` —
     la description vision est renvoyée brute à Nico.
4. `llm/image_router.py:96-150` `ImageRouter.handle_input` : construit
   le prompt vision (l. 123-137), `_run_vision` → `_dispatch` (l. 176-205)
   sur `VISION_ROUTING_TABLE` (groq1, groq2, groq3, deepseek).
5. `llm/vision/groq_vision.py:46-62` `GroqVisionClient.describe` :
   POST OpenAI-compatible, `max_tokens: 512` en dur, data URL
   `image/png` en dur (l. 44), retourne `content` tel quel.

Mode enrichi (`_handle_input_enriched`) : message
`[Analyse visuelle : <description>]\n\n<caption>` envoyé à
`LLMExecutionRouter.execute` en REASONING → pipeline texte complet
(`execution/routers/llm_router.py:99-260` : mémoire, résolution
d'intent, AnalystAgent, écriture épisodique + conversation).

## 2. Constats par dette

### #45 — langue
`llm/image_router.py:130-137` : sans légende, prompt en anglais
(« volontairement en anglais ») → réponse en anglais, renvoyée brute
en mode standard. Avec légende, prompt en français. Aucune consigne de
langue explicite dans aucun des deux prompts. En mode enrichi, la
réponse finale passe par `soul.md` (français) : pas de problème de
langue observé.

### #46 — troncature
Mesure 2026-10-15, photo gratin, prompt anglais actuel, groq qwen3.8 :
`finish: length`, 512 tokens de complétion, **aucun raisonnement**
(message sans champ `reasoning`). La troncature vient de la verbosité
du prompt « Describe this image in detail », pas d'un raisonnement
caché. Avec un prompt français « en quelques phrases » : 116-219
tokens, `finish: stop` [n=3 photos].

**DeepSeek vision raisonne** (non vu au sprint 18, mesuré alors sur un
PNG synthétique) : photo bain nordique, `max_tokens 1024`,
`reasoning_tokens: 892`, contenu coupé, `finish: length` [n=1]. Avec
`thinking: {type: disabled}` : 191-307 tokens, `finish: stop`, 3,4-4,1 s
[n=3 photos]. Le maillon de secours vision est donc aujourd'hui
tronqué sur photo réelle.

### #47 — logs
- `_dispatch` (`llm/image_router.py:199-200`) : échecs via `print()`.
- Aucun log de succès vision (ni fournisseur ni modèle).
- `write_image_artifact` : aucun log de succès côté router
  (`execution/routers/image_router.py:119-124`), seulement l'erreur.
- `[IMAGE ENRICHED]` logué en `log.error` (l. 177) alors que c'est une
  trace nominale.
- `logger` importé localement dans les fonctions (l. 122, 175, 227,
  283) au lieu du `log = get_logger(__name__)` module du style projet.

### #48 — inventions avec légende
Prompt légende actuel (l. 124-129) : « Réponds directement à ce que
l'utilisateur semble vouloir savoir ». Rejoué sur la photo bain
nordique + « Paysage savoyard » (groq) : « cheminée de *banja* »,
« chauffage d'air », « composition en quatre volets », `finish: length`
[n=1]. La consigne pousse à interpréter ; rien n'interdit de deviner.

**Défaut propre à groq qwen3.8** : il décrit une image unique comme un
assemblage de plusieurs vues — « cropped views » (gratin), « composition
en quatre volets » (bain nordique), « les vues de détail » (chalet),
« trois cercles rouges » pour un disque (sprint 18) [4 sorties sur 6
groq observées]. DeepSeek ne le fait sur aucune [n=4]. Hypothèse non
vérifiée : découpage en tuiles côté groq.

Comparaison qualité, prompt français sobre anti-invention [n=3 photos] :

| Photo | groq qwen3.8 (~1 s) | DeepSeek flash sans raisonnement (~4 s) |
|---|---|---|
| Bain nordique | « tonneau… barbecue ou poêle », fonction « pas claire » | « probablement un bain nordique » ✔ |
| Gratin | correct, court | correct, plus détaillé |
| Chalet | correct, mais « vues de détail » | correct, détaillé (drapeau, bain nordique) |

### #49 — MIME
`groq_vision.py:44` : `data:image/png` pour des fichiers `.jpg`. Les deux
fournisseurs acceptent quand même (mesuré : 200 en PNG déclaré comme en
JPEG). Défaut de correction, sans effet observable aujourd'hui.

### #50 — réponse vide
`groq_vision.py:62` retourne `content` sans contrôle : `''`/`None` =
succès, pas de fallback. Avec DeepSeek à raisonnement actif, un budget
serré produit exactement ce cas (audit sprint 18 §3).

### #51 — « c'est ta maison de montagne »
Mécanisme établi (pas un rattachement d'autorité à un intent existant) :
1. la photo « c'est quoi » passe en mode enrichi ; la vision décrit
   « une maison de campagne au style rustique… » ;
2. `LLMExecutionRouter` résout l'intent **sur le message enrichi
   entier** (description incluse) → action `create` → `extract_intent_name`
   → nouvel intent « maison de montagne » (`~/.aria/intents.json`,
   `actions_history: created_from_message:[Analyse visuelle : D'après
   les images, il s'agit d'une maison de campagne…`) ;
3. `AnalystAgent.PROMPT` (`agents/analyst_agent.py:13`) présente l'intent
   comme « PROJET RÉCENT EN MÉMOIRE : maison de montagne » → le LLM
   répond « c'est ta maison de montagne ».
Effets : réponse fausse par construction et pollution des intents
(un intent créé par photo interrogative non reconnue).

## 3. Hors périmètre constaté

- Mode standard : la photo n'est pas écrite dans `aria_conversation`
  (seul le mode enrichi passe par `write_conversation_turn`). Une
  relance texte (« en fait c'est un bain nordique ») n'a pas la photo
  dans l'historique.
- groq ITPM 7000 tokens/min par clé ; une photo ≈ 1 850 tokens
  d'entrée → ~3 photos/min/clé avant 429 (bascule groq2/groq3).
