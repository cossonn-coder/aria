# Sprint 24 — Audit génération d'images (#44)

Date : 2026-10-16. Code lu sur `main` @ `8bf2b57`. Sondes réseau lancées
depuis la VM le même jour.

## 1. Chemin de données (vérifié au code)

```
Telegram texte ──► classify_operation()            cognition/cognitive_classifier.py:305-310
                   étape 4 : detect_image_generation_intent(message)  (mots-clés, l. 50-71)
Telegram photo ──► CognitiveEngine.classify()      cognition/cognitive_engine.py:87-96
                   detect_generation_intent_from_caption(caption) AVANT is_interrogative_caption
        │
        ▼  kernel : op IMAGE_GENERATION → "image_router"          core/kernel.py:49
ImageExecutionRouter._handle_generation(content, payload)        execution/routers/image_router.py:224-270
   raw_prompt = content si str, sinon str(content)
   context_block = _build_generation_context(raw_prompt)          l. 276-318
       intents actifs (top 3 salience) + bridge.retrieve_memories(query, n=3)
   enriched_prompt = "[Contexte :\n…]\n\n" + raw_prompt           l. 325-342
   internal_router.generate(message=enriched_prompt, intent_id)
        │
        ▼
llm/image_router.py ImageRouter.generate → _dispatch(GENERATION_ROUTING_TABLE, "generate")
   1. PollinationsClient   GET https://image.pollinations.ai/prompt/{quote(prompt)}
                           ?width=1024&height=1024&nologo=true, timeout 60 s, sans clé
   2. HuggingFaceImageClient POST https://api-inference.huggingface.co/models/{hf_image_model}
                           (FLUX.1-schnell), retry 503 ×5, print() en prod
   toutes en échec → RuntimeError → dispatcher status error
        │
        ▼
write_image_artifact(artifact)  memory/writer.py:97  (indexe artifact.prompt = PROMPT ENRICHI)
retour {"path", "caption": raw_prompt[:100]}
        │
        ▼
kernel._normalize : path .png/.jpg/.jpeg/.webp → {"type": "image", …}   core/kernel.py:199-207
TelegramInterface.send → send_photo(caption[:1024])                     interfaces/telegram_interface.py:183-197
```

Règles inviolables : respectées (écriture via `memory/writer.py`, lecture via
bridge, router retourne `{"path","caption"}`, kernel séquence).

## 2. État des fournisseurs (sondes 2026-10-16)

| Fournisseur | Résultat | Conséquence |
|---|---|---|
| Pollinations anonyme `image.pollinations.ai/prompt/…` | **200, JPEG 768×768, ~6 s** — mais **filigrane** « pollinations.ai » (`nologo` ignoré en anonyme) et **402 `FREE_LIMIT` : 1 image / 45 s par IP** | Revenu à la vie depuis l'audit sprint 18 (alors timeout). Utilisable, dégradé. |
| Pollinations, prompt enrichi réel d'ARIA (bloc `[Contexte : …]` multi-lignes, apostrophes) | **404 `Not Found`** [n=1, cause non isolée] | Retours à la ligne, apostrophes/accents et prompt de ~1000 car. passent séparément (200). Voir §3.2 |
| Pollinations avec clé (`gen.pollinations.ai`, `Authorization: Bearer sk_…`) | non testé (pas de clé) | Doc : GET `/image/{prompt}?model=…`, ou POST `/v1/images/generations` (OpenAI-compatible) ; supporte des images de référence (`image=`) et `/v1/images/edits`. Allocation gratuite d'un compte : non trouvée dans la doc. |
| HF `api-inference.huggingface.co` (URL du code) | domaine mort (audit sprint 18) | client HF inutilisable tel quel |
| HF router `hf-inference` FLUX.1-schnell / SDXL | **410** modèle retiré | — |
| HF router `hf-inference` SD3-medium (seul modèle t2i restant) | **402 « no remaining credits »** | compte HF gratuit (`canPay: false`) à sec |
| fal.ai (`FAL_KEY` présente dans `.env`, **jamais lue par le code**) | clé valide, **403 « User is locked. Exhausted balance »** | utilisable seulement après recharge |
| Gemini (`GEMINI_API_KEY`) | API Google injoignable depuis la VM (code 000, cf. #67 IPv6) | écarté |

## 3. Défauts dans le code (indépendants du fournisseur)

### 3.1 Aucun fournisseur à clé fonctionnel câblé
Pollinations est appelé sans clé (ancienne URL), HF pointe un domaine mort.
`FAL_KEY` n'est lue nulle part (`grep -rn -i fal_ --include=*.py` : vide).

### 3.2 Le prompt envoyé au générateur est pollué
`_inject_context` préfixe le prompt utilisateur par un bloc
`[Contexte : Projets actifs… Souvenirs pertinents…]` en français, issu de
3 intents + 3 souvenirs épisodiques **choisis par similarité, pas par
pertinence visuelle**. Un modèle de diffusion ne « comprend » pas ce bloc :
il le dessine (ou dilue le sujet). Effets : image hors sujet, URL très longue,
404 Pollinations observé sur ce format.

### 3.3 Pas de traduction FR→EN, malgré les commentaires
`llm/image_router.py:171` (« déjà traduit en EN par l'appelant ») et
`core/kernel.py:81` (« llm_router injecté pour la traduction FR→EN ») sont
faux : aucun appelant ne traduit. Le prompt contient aussi la formule de
demande (« génère une image de… »).

### 3.4 Mémoire épisodique auto-polluante
`write_image_artifact` indexe `artifact.prompt`, c'est-à-dire le prompt
**enrichi** : chaque génération stocke en `aria_episodic` un document
contenant les souvenirs de contexte eux-mêmes → ils ressortiront au prochain
recall, recopiés.

### 3.5 Génération depuis une photo : prompt = `str(dict)`
Photo + légende de génération (« transforme en aquarelle ») → `content` est
`{"file_path": …, "caption": …}` → `raw_prompt = str(content)` : le générateur
reçoit `"{'file_path': '/home/…/received_images/….jpg', 'caption': 'transforme
en aquarelle'}"`. Aucun img2img n'existe ; la photo est ignorée.

### 3.6 Heuristiques de déclenchement trop larges
Vérifié dans le venv :

| Message | Résultat |
|---|---|
| « tu peux afficher la liste des courses ? » | IMAGE_GENERATION (« affiche ») |
| « montre moi les intents actifs » | IMAGE_GENERATION (« montre moi ») |
| « quel logo pour ma marque ? » | IMAGE_GENERATION (« logo ») |
| photo + « c'est quoi ce style ? » | IMAGE_GENERATION (« style », testé avant l'interrogatif) |
| photo + « fais quoi avec ça ? » | IMAGE_GENERATION (« fais ») |

Tant que la génération était morte, ces faux positifs finissaient en
« Une erreur s'est produite » ; une fois réparée, ils produiront des images
non demandées.

### 3.7 Divers (dettes, hors cible probable)
- `hf_client.py:161` : `print()` en prod.
- Nom de fichier = md5(prompt) : même prompt → écrase le fichier précédent
  (sans effet utilisateur, l'image est envoyée aussitôt).
- `kernel._normalize` : `print()` (#71, déjà ouverte).

## 4. Ce qu'un run live devra montrer
« dessine un renard qui lit le journal dans la neige » → photo reçue sur
Telegram, sujet conforme, sans filigrane si fournisseur à clé ;
`journalctl` : fournisseur ayant répondu, pas de `[IMAGE ROUTER FALLBACK]` ;
« tu peux afficher la liste des courses ? » → réponse texte, pas d'image.

## 5. Sonde avec clé Nico (`POLLINATION_API_KEY`, `sk_`, 2026-10-16)

- `GET https://gen.pollinations.ai/image/{quote(prompt)}?model=tongyi-mai/z-image-turbo&width=1024&height=1024`,
  header `Authorization: Bearer <clé>` → **200, JPEG 1024×1024, 4-6 s, sans
  filigrane** ; deux requêtes consécutives sans 402 [n=3].
- Modèle `tongyi-mai/z-image-turbo` : non `paid_only`, 0,004 pollen/image
  (`/image/models`). Allocation gratuite quotidienne : non lisible (la clé
  n'a pas la permission `account:usage`).
- Prompt FR brut (« dessine un chat roux qui arrose des tomates dans un
  potager, style aquarelle ») → image conforme (action « arrose » ratée)
  [n=1] : pas besoin de traduction LLM.
