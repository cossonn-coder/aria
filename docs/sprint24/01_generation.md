# Sprint 24 — Tronçon 01 : génération d'images réparée (#44)

Lire d'abord : `CLAUDE.md`, `docs/sprint24/00_etat.md`. Diagnostic complet :
`docs/sprint24/audit_generation_images.md` (§3 défauts, §5 sonde avec clé).

## Objectif

« dessine un renard dans la neige » sur Telegram renvoie une image générée
par Pollinations **avec la clé de Nico** (sans filigrane), à partir du
message brut, sans bloc de contexte. Les faux déclenchements connus
disparaissent.

## Fichiers à toucher (vérifiés au code, `main` @ `8bf2b57`)

### 1. `config.py`
Ajouter `pollination_api_key: str = ""` (champ de classe, à côté de
`tavily_api_key`) et `self.pollination_api_key = os.getenv("POLLINATION_API_KEY", "")`
dans `__init__`. **Nom de variable sans S** : c'est celui du `.env` de Nico.

### 2. `llm/image_gen/pollinations_client.py`
Intention : un même client sert les deux entrées de la table.
- Avec `api_key` : `GET https://gen.pollinations.ai/image/{quote(prompt, safe="")}`
  params `model=tongyi-mai/z-image-turbo`, `width`, `height` (1024),
  header `Authorization: Bearer <api_key>`.
- Sans `api_key` : comportement actuel inchangé (`{base_url}/prompt/…`,
  `nologo=true`).
- Le constructeur accepte déjà `**_` : ajouter `api_key=None` et `model=None`
  en paramètres nommés. Le modèle vient de la table (`model`), pas en dur
  dans le client.
- Vérifier `content-type` image avant d'écrire le fichier (Pollinations
  renvoie du JSON en 402/erreur ; `raise_for_status` couvre les codes ≠ 2xx,
  ce garde-fou couvre un 200 non-image) → `RuntimeError`, ce qui fait jouer
  le fallback. Même logique que `hf_client.py:113-118`.

Vérité terrain (sonde 2026-10-16, réponse 200 `image/jpeg` 1024×1024, ~5 s) :
```
GET https://gen.pollinations.ai/image/<prompt-encodé>?model=tongyi-mai/z-image-turbo&width=1024&height=1024
Authorization: Bearer sk_…
```

### 3. `llm/image_router.py` — `GENERATION_ROUTING_TABLE` (l. 70-83)
```
1. provider "pollinations_key" : PollinationsClient,
   base_url "https://gen.pollinations.ai", model "tongyi-mai/z-image-turbo",
   api_key lambda: config.pollination_api_key
2. provider "pollinations_anon" : PollinationsClient,
   base_url "https://image.pollinations.ai"   (secours : filigrane, 1 image / 45 s)
```
Retirer l'entrée HuggingFace et l'import `HuggingFaceImageClient` (l. 21).
Si la clé est vide, l'entrée 1 doit échouer (exception) pour tomber sur le
secours — ne pas appeler l'endpoint à clé sans clé.

Dans `_dispatch` (l. 213-215) : le log de succès ne vise que `describe`.
L'étendre à la génération, `log.info("[IMAGE GEN] %s a répondu.", provider)`,
pour que le run live voie quel fournisseur a servi.

Corriger le docstring de `generate` (l. 171 « déjà traduit en EN par
l'appelant » est faux : le prompt est le message brut de l'utilisateur).

### 4. `execution/routers/image_router.py`
- `_handle_generation` (l. 224-270) : appeler
  `internal_router.generate(message=raw_prompt, …)`. Plus d'enrichissement.
- Supprimer `_build_generation_context` (l. 276-318) et `_inject_context`
  (l. 325-342), devenus sans caller. Mettre à jour le docstring du flux
  et l'en-tête du module (l. 32-35 « Enrichir le prompt de génération… »).
- La mémoire épisodique reçoit donc la demande brute (`artifact.prompt`
  = `raw_prompt`), ce qui supprime l'auto-pollution (audit §3.4). Ne pas
  toucher `memory/writer.py`.
- Le constructeur garde ses paramètres `intent_engine` / `mempalace_bridge`
  (le kernel les passe, `core/kernel.py:82-87`) même s'ils ne servent plus à
  la génération ; ne pas modifier le kernel sauf le commentaire faux
  l. 81 (« llm_router injecté pour la traduction FR→EN ») → le corriger.

### 5. `cognition/cognitive_engine.py` — `classify` (l. 87-96)
Un event IMAGE ne produit plus jamais `IMAGE_GENERATION` : supprimer la
branche `detect_generation_intent_from_caption`. Photo + « transforme en
aquarelle » → `IMAGE_INPUT` (description vision). Mettre à jour le docstring
de classe (l. 60-73) et retirer l'import devenu inutile.
`detect_generation_intent_from_caption` et `_CAPTION_GENERATION_KEYWORDS`
dans `cognitive_classifier.py` deviennent sans caller prod : les supprimer
(orphelins créés par ce tronçon), ainsi que leur mention dans l'en-tête du
module (l. 23).

### 6. `cognition/cognitive_classifier.py` — `_TEXT_GENERATION_KEYWORDS` (l. 50-71)
Retirer : `"affiche"`, `"montre moi"`, `"visualise"`, `"logo"`,
`"illustration"`, `"infographie"`, `"render"`.
Faux positifs vérifiés : « tu peux afficher la liste des courses ? »,
« montre moi les intents actifs », « quel logo pour ma marque ? ».
Garder les verbes de création (`génère`, `dessine`, `illustre`, « crée une
image »…), `meme`, `bannière`, `draw`, etc.

## Tests

À adapter (comportement volontairement changé) :
- `tests/images/test_image_context_enrichment.py` : tests du bloc contexte
  (`_inject_context`, injection intents / souvenirs, erreur mémoire non
  bloquante) → supprimer ; garder / adapter
  `test_generation_without_context_passes_raw_prompt` et
  `test_generation_result_contains_path_and_caption`. Ajouter : avec intents
  actifs et souvenirs, le prompt passé à `generate` reste exactement le
  message brut.
- `tests/images/test_caption_pipeline.py` l. 27-36 et
  `tests/images/test_interrogative_vision_pipeline.py` l. 161-166 : une
  légende de génération donne désormais `IMAGE_INPUT`.
- `tests/images/test_architecture_rules.py` l. 7, 14 : retirer
  `HuggingFaceImageClient` de la liste si le test porte sur la table ;
  le fichier `hf_client.py` n'est pas supprimé (voir hors-scope).
- `tests/images/test_image_router_dispatch.py`, `test_fallback_order.py` :
  lancer, adapter seulement si cassés.

À ajouter (cas nominal) :
- `PollinationsClient` avec `api_key` : URL `gen.pollinations.ai/image/…`,
  `model` en param, header `Authorization: Bearer …`, fichier écrit
  (monkeypatch de `httpx.get`, comme `test_generation_clients.py`).
- `PollinationsClient` : réponse 200 non-image → `RuntimeError`.
- `classify_operation("tu peux afficher la liste des courses ?")` ≠
  `IMAGE_GENERATION` ; `classify_operation("dessine un chat")` ==
  `IMAGE_GENERATION`.

`tests/conftest.py` patche `httpx.get` / `httpx.post` : aucun appel réseau
réel en test.

## Hors scope (ne PAS faire)

- Supprimer `llm/image_gen/hf_client.py` ou `config.hf_image_model`
  (deviennent morts → dette à lister en fin de livrable). Ne pas toucher
  `config.hf_token` (env HF positionné pour les libs Hub).
- Image-to-image / photo + légende de génération (dette #77).
- Réécriture du prompt par LLM, traduction FR→EN.
- `kernel._normalize` `print()` (#71), `hf_client.py` `print()`.
- `.env` : ne pas le lire dans les tests, ne pas le modifier.

## Critère de fin

- `pytest tests/ -q` vert.
- `grep -rn "_inject_context\|_build_generation_context\|detect_generation_intent_from_caption\|HuggingFaceImageClient" --include=*.py . | grep -v venv`
  ne remonte plus que `llm/image_gen/hf_client.py` (définition de la classe).
- Commit local `feat(sprint24) tronçon 01: …`.
- Validation finale = run live 02 (Nico), pas les tests.
