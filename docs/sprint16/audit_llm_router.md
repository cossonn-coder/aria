# Audit cartographique — `LLMRouter` pour signature multi-messages

**Sprint** : 16, tour 1 (audit)
**Date** : 2026-05-23
**Branche** : `feat/sprint16-router-multi-messages` (créée depuis `sprint-15`)
**Périmètre** : `llm/llm_router.py`, ses callers, la chaîne de fallback,
les tests existants.

> **Statut** : audit pur. Aucune ligne de code modifiée dans le working tree
> à part la création de ce document.

---

## §1 — Inventaire du module `llm/`

```
llm/
├── __init__.py                    # vide
├── llm_role.py                    # enum LLMRole (CHAT, REASONING, PLANNING, REFLECTION)
├── llm_router.py                  # *** cible du sprint *** — router texte avec fallback et cache négatif
├── intent_namer.py                # caller LLM (1 call → llm_router.complete) pour nommer un intent en 2-5 mots
├── image_router.py                # ImageRouter texte→image et vision — N'UTILISE PAS LLMRouter texte
├── image_gen/
│   ├── __init__.py                # vide
│   ├── pollinations_client.py     # client génération image (HTTP GET, hors scope sprint 16)
│   └── hf_client.py               # client génération image HuggingFace (hors scope)
└── vision/
    ├── __init__.py                # vide
    ├── groq_vision.py             # client vision Groq (format `messages=[{role:user, content:[image_url,text]}]`)
    └── openrouter_vision.py       # client vision OpenRouter (même format multimodal)
```

**Classification rôle/contrat** :

- **Routeur texte** : `llm/llm_router.py` (seul concerné par ce sprint).
- **Rôle / contrat** : `llm/llm_role.py` (enum stable, pas de modif prévue).
- **Caller LLM léger** : `llm/intent_namer.py` (appelle `complete`).
- **Routeur image** (texte→image + vision) : `llm/image_router.py` — il a sa
  propre routing table et ses propres wrappers. **Pas de wrapper provider
  partagé avec `LLMRouter`**, l'audit ne s'y attarde donc pas.
- **Wrappers image** : `image_gen/` et `vision/` — chacun encapsule un
  provider image. Hors scope.

**Constat structurel important** : il n'existe **PAS** de wrappers par
provider pour le pipeline texte. Le brief tour 1 mentionne
« `wrappers/<provider>.py` » : ce dossier n'existe pas. Toute la logique
de dispatch HTTP est inlinée dans `LLMRouter._call` (cf. §2).

---

## §2 — Signature actuelle de `LLMRouter._call`

### 2.a — Code intégral de `_call` (`llm/llm_router.py:241-324`)

```python
def _call(
    self,
    prompt: str,
    provider_cfg: dict,
    temperature: float,
    max_tokens: int,
) -> LLMResponse:

    api_key = provider_cfg["api_key"]()

    # system prompt = soul + user (commun aux deux formats)
    system_parts = [_SOUL]
    if _USER:
        system_parts.append(f"\n\nPROFIL UTILISATEUR :\n{_USER}")
    system_prompt = "\n".join(system_parts)

    if provider_cfg["provider"] == "anthropic":
        from logger import get_logger
        log = get_logger(__name__)

        url = f"{provider_cfg['base_url']}/messages"
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        payload = {
            "model": provider_cfg["model"],
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()
        data = response.json()
        content = data["content"][0]["text"]
        log.info("[LLM] Anthropic (%s) a répondu.", provider_cfg["model"])
        return LLMResponse(
            content=content,
            metadata={
                "provider": provider_cfg["provider"],
                "model": provider_cfg["model"],
            },
            usage=data.get("usage"),
        )

    # ── Format OpenAI-compatible ──────────────────────────────────────────
    url = f"{provider_cfg['base_url']}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # OpenRouter requiert ces headers pour le rate limiting
    if provider_cfg["provider"] == "openrouter":
        headers["HTTP-Referer"] = "https://aria.local"
        headers["X-Title"] = "Aria"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    payload = {
        "model": provider_cfg["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    return LLMResponse(
        content=content,
        metadata={
            "provider": provider_cfg["provider"],
            "model": provider_cfg["model"],
        },
        usage=data.get("usage"),
    )
```

### 2.b — Code intégral du point d'entrée public `complete` (`llm/llm_router.py:199-239`)

```python
def complete(
    self,
    prompt: str,
    role: LLMRole = LLMRole.CHAT,
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> LLMResponse:

    from logger import get_logger
    log = get_logger(__name__)

    chain = ROUTING_TABLE.get(role, DEFAULT_CHAIN)
    last_error = None

    for i, provider_cfg in enumerate(chain):
        provider = provider_cfg["provider"]

        # Skip direct si récemment 429 — pas de tentative HTTP.
        if self._is_rate_limited(provider):
            log.info("[LLM] provider %s skipped (cached 429)", provider)
            continue

        try:
            return self._call(
                prompt=prompt,
                provider_cfg=provider_cfg,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            log.error("[LLM FALLBACK] %s failed: %s", provider, e)
            # Cache uniquement les 429 explicites — un crash réseau
            # ou un 5xx ne bloque pas le provider 5 min.
            if (isinstance(e, httpx.HTTPStatusError)
                    and e.response.status_code == 429):
                self._mark_rate_limited(provider)
            last_error = e
            if i < len(chain) - 1:  # pas de sleep après le dernier
                time.sleep(1)

    raise RuntimeError(f"All providers failed. Last error: {last_error}")
```

### 2.c — Rôle de chaque paramètre

| Paramètre | Type | Rôle |
|-----------|------|------|
| `prompt` (de `complete` et `_call`) | `str` | Contenu utilisateur. Devient `messages[1].content` côté OpenAI-compat, `messages[0].content` côté Anthropic. **Aucun appelant ne fournit le system prompt.** |
| `role` (de `complete` uniquement) | `LLMRole` | Sélectionne la chaîne de providers dans `ROUTING_TABLE` (CHAT / PLANNING / REASONING / REFLECTION). |
| `temperature` | `float` | Transmis tel quel au provider, défaut `0.7`. |
| `max_tokens` | `int` | Transmis tel quel, défaut `1000`. |
| `provider_cfg` (de `_call` uniquement) | `dict` | Entrée de la `ROUTING_TABLE` (provider, model, base_url, api_key). |

### 2.d — Constat majeur sur la position architecte

Le brief tour 1 décrit la forme legacy comme
`_call(system_prompt: str, user_prompt: str, ...)`. **Cette signature
n'existe pas.** La forme legacy réelle est :

- `complete(prompt: str, role=..., temperature=..., max_tokens=...)` côté API publique
- `_call(prompt: str, provider_cfg: dict, temperature, max_tokens)` côté implémentation

Le **system prompt est construit en dur** dans `_call` à partir de deux
fichiers (`config.soul_path`, `config.user_path`), chargés une seule fois
au module-load via les globals `_SOUL` et `_USER` (lignes 13-26 du fichier).
**Aucun caller existant ne peut le surcharger.**

Conséquence pour le sprint 16 : la signature évoluée ne peut pas être
`_call(system_prompt, user_prompt, ..., messages, ...)` (xor) telle que
le brief la décrit, parce que `system_prompt` n'est pas un paramètre.
La signature correcte à concevoir est :

- **Forme legacy à préserver** : `complete(prompt, role, temperature, max_tokens)`
- **Forme nouvelle** : `complete(messages=[...], role, temperature, max_tokens)` (xor avec `prompt`)

Le système conserve son injection `_SOUL` + `_USER` quand la forme legacy
est utilisée, et **n'injecte rien** quand la forme `messages` est utilisée
(le caller assume la responsabilité du system prompt, c'est tout l'intérêt).
Arbitrage détaillé en §7.

---

## §3 — Callers de `_call` (et de `complete`)

**Aucun caller du repo n'appelle `_call` directement.** Tous passent par
`complete`. Quatre sites de prod, plus deux sites en test.

### 3.a — Callers de production

| Fichier:ligne | Rôle LLM | Format prompt construit |
|---------------|----------|-------------------------|
| `agents/analyst_agent.py:49` | `LLM_ROLE_MAP[operation]` (CHAT par défaut, voir `cognition/cognitive_context.py`) | **Gros prompt unique** avec 5 slots concaténés : `PROJET RÉCENT`, `MESSAGE UTILISATEUR`, `HISTORIQUE DE CETTE SESSION`, `CONTEXTE COGNITIF`, `RÈGLES`. |
| `agents/planner_agent.py:44` | `LLMRole.PLANNING` | Prompt unique avec slots `MESSAGE`, `INTENT`, `CONTEXTE`, `RÈGLES`. |
| `cognition/cognitive_classifier.py:222` | `LLMRole.CHAT` | Prompt court — formattage de `CLASSIFIER_PROMPT.format(message=message)`. |
| `llm/intent_namer.py:20` | `LLMRole.CHAT` | Prompt court — formattage de `NAMER_PROMPT.format(message=message)`. |

Extraits avec contexte :

```python
# agents/analyst_agent.py:42-54
prompt = PROMPT.format(
    intent_name=ctx.intent.name,
    message=ctx.message,
    session_memory=self._format_memories(ctx.session_memory),
    context_block=ctx.extra.get("context_block", "Aucun contexte disponible."),
)

response = llm_router.complete(
    prompt,
    role=role,
    temperature=0.3,
    max_tokens=800,
)
```

```python
# agents/planner_agent.py:38-49
prompt = PROMPT.format(
    message=ctx.message,
    intent=ctx.intent.name,
    analysis=ctx.result or "Aucune analyse disponible.",
)

response = llm_router.complete(
    prompt,
    role=LLMRole.PLANNING,
    temperature=0.4,
    max_tokens=600,
)
```

```python
# cognition/cognitive_classifier.py:222-226
response = llm_router.complete(
    prompt=CLASSIFIER_PROMPT.format(message=message),
    role=LLMRole.CHAT,
    temperature=0.1,
    max_tokens=60,
)
```

```python
# llm/intent_namer.py:20-25
response = llm_router.complete(
    prompt=NAMER_PROMPT.format(message=message),
    role=LLMRole.CHAT,
    temperature=0.1,
    max_tokens=20,
)
```

### 3.b — Callers de tests (cartographie, code non recopié)

- `tests/llm/test_negative_cache.py` : 5 tests sur `complete()`, monkeypatch
  de `_call` avec `LLMRouter._call`.
- `tests/execution/test_pipeline_memory_isolation.py:69-71` : crée un
  `MagicMock(name="LLMRouter")` injecté dans `AnalystAgent`.
- `tests/conftest.py:67-84` : fixture `autouse` qui patch `httpx.post`
  globalement pour retourner un faux JSON compatible avec le format
  OpenAI (`choices[0].message.content`). **C'est ce mock qui maintient
  toute la suite verte sans réseau.**

### 3.c — Caller indirect via `route()`

`LLMRouter` a aussi une méthode `route(message, intent, phase,
memory_results)` (lignes 330-349) qui formatte un prompt minimal et délègue
à `complete(role=LLMRole.CHAT)`. **Cette méthode n'est appelée nulle part
en prod** (grep négatif sur le repo) — vestige inerte non documenté.
Hors scope, à signaler en dettes adjacentes (cf. §9).

### 3.d — Bilan migration future

Sur les 4 callers prod :

- **Candidat naturel à migrer (sprint 17)** : `analyst_agent.py` —
  le slot `HISTORIQUE DE CETTE SESSION` est précisément ce que la
  forme `messages=[...]` rendra structurel (cf. fil rouge #34).
- **Resteront en forme legacy** : `planner_agent.py`, `cognitive_classifier.py`,
  `intent_namer.py` — tous traitent un message ponctuel sans historique
  conversationnel. Migration sans valeur ajoutée.

---

## §4 — Matrice de compatibilité provider × format messages

**Aucun wrapper séparé par provider** dans le pipeline texte. Le dispatch
se fait via un `if provider_cfg["provider"] == "anthropic": ...` dans `_call`
(ligne 257) et tout le reste tombe dans la branche OpenAI-compatible.

### 4.a — Matrice

| Provider | Wrapper | Format natif accepté | Conversion interne | Multi-msg supporté ? |
|----------|---------|----------------------|--------------------|----------------------|
| **Mistral** | `_call` branche OpenAI-compat (l. 288-324) | OpenAI Chat Completions (`messages=[{role, content}]`) | Aucune — payload OpenAI brut | OUI |
| **Groq** (et `groq_2`, `groq_3`) | `_call` branche OpenAI-compat | OpenAI Chat Completions | Aucune | OUI |
| **Cerebras** | `_call` branche OpenAI-compat | OpenAI Chat Completions | Aucune | OUI |
| **OpenRouter** | `_call` branche OpenAI-compat + 2 headers ad-hoc (`HTTP-Referer`, `X-Title`) | OpenAI Chat Completions | Aucune | OUI |
| **Anthropic** | `_call` branche `if provider == "anthropic"` (l. 257-286) | API Anthropic Messages : `system: str` top-level + `messages=[{role, content}]` (rôles `user`/`assistant` seulement) | **Oui** — split entre `system` top-level et `messages` | OUI sur `messages` ; le rôle `system` doit être extrait vers le param top-level |
| **Gemini** | **N'EST PAS dans `ROUTING_TABLE`** malgré `config.gemini_api_key` et `config.gemini_model` | n/a | n/a | **HORS SCOPE — pas appelé en prod** |
| **SambaNova** | **N'EST PAS dans `ROUTING_TABLE`** malgré `config.sambanova_api_key` et `config.sambanova_model` | n/a | n/a | **HORS SCOPE — pas appelé en prod** |

### 4.b — Constat important sur Gemini et SambaNova

Le brief tour 1 demande de remplir la matrice pour Gemini et SambaNova.
**Ces deux providers sont configurés mais jamais utilisés** : `grep`
exhaustif sur `gemini` et `sambanova` en dehors de `config.py` ne renvoie
aucun caller. Ils n'apparaissent dans aucune chaîne de la `ROUTING_TABLE`
de `llm/llm_router.py` (l. 40-151).

→ Conséquence sprint 16 : **on ne traite ni Gemini ni SambaNova**, le code
de `_call` ne contient aucune branche pour ces providers. Si un jour on
les active, ce sera dans un sprint dédié avec son propre audit
(format Gemini différent — `contents=[{role: user|model, parts:[{text}]}]`).

### 4.c — Extraits de wrapper

**Branche OpenAI-compat** (`llm/llm_router.py:288-310`) — couvre Mistral,
Groq, Cerebras, OpenRouter :

```python
# ── Format OpenAI-compatible ──────────────────────────────────────────
url = f"{provider_cfg['base_url']}/chat/completions"
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

# OpenRouter requiert ces headers pour le rate limiting
if provider_cfg["provider"] == "openrouter":
    headers["HTTP-Referer"] = "https://aria.local"
    headers["X-Title"] = "Aria"

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": prompt},
]

payload = {
    "model": provider_cfg["model"],
    "messages": messages,
    "temperature": temperature,
    "max_tokens": max_tokens,
}
```

→ Le champ `messages` est **déjà** une liste OpenAI standard ; il suffit
d'éviter de la reconstruire en dur quand le caller fournit déjà
`messages=[...]`.

**Branche Anthropic** (`llm/llm_router.py:257-286`) :

```python
if provider_cfg["provider"] == "anthropic":
    url = f"{provider_cfg['base_url']}/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": provider_cfg["model"],
        "max_tokens": max_tokens,
        "system": system_prompt,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
```

→ Le system prompt est **un paramètre top-level**, pas un message
`{role: system}`. Quand le caller fournit `messages=[...]` contenant un
ou plusieurs `{role: system, content: ...}`, le router devra les
**extraire et concaténer** vers le param `system`, et ne laisser dans
`messages` que les `{role: user|assistant}`. C'est le seul vrai travail
de conversion du sprint 16 côté Anthropic.

### 4.d — Liens doc providers (pinned)

- **Mistral** : https://docs.mistral.ai/api/#tag/chat (endpoint
  `POST /v1/chat/completions`, payload `messages` strictement compatible
  OpenAI).
- **Groq** : https://console.groq.com/docs/api-reference#chat-create
  (clone exact OpenAI Chat Completions).
- **Cerebras** : https://inference-docs.cerebras.ai/api-reference/chat-completions
  (clone OpenAI).
- **OpenRouter** : https://openrouter.ai/docs/api-reference/chat-completion
  (clone OpenAI + champs additionnels facultatifs `transforms`, `route`).
- **Anthropic** : https://docs.anthropic.com/en/api/messages
  (param `system: str` top-level distinct, `messages` n'accepte que
  `user` et `assistant`).

---

## §5 — Logique de fallback inter-providers

Le fallback vit dans `complete()`, pas dans `_call` (cf. §2.b pour le code
intégral). Il est constitué de trois éléments :

1. **Itération séquentielle** sur la chaîne `ROUTING_TABLE[role]`
   (boucle `for i, provider_cfg in enumerate(chain)`).
2. **Skip immédiat** des providers en cache négatif 429
   (`self._is_rate_limited(provider)`), pas de tentative HTTP.
3. **Sur exception** : log de l'échec, mise en cache négatif **uniquement
   si l'exception est un `httpx.HTTPStatusError` avec status 429**, puis
   `time.sleep(1)` si ce n'est pas le dernier provider de la chaîne.

Code de gestion du cache négatif (`llm/llm_router.py:172-197`) :

```python
def __init__(self):
    # {provider_name: expires_at_monotonic}
    # time.monotonic() pour être immune aux changements d'horloge.
    self._negative_cache: dict[str, float] = {}

def _is_rate_limited(self, provider: str) -> bool:
    """True si le provider a un 429 récent encore valide.
    Purge lazy : une entrée expirée est supprimée au lookup."""
    expires_at = self._negative_cache.get(provider)
    if expires_at is None:
        return False
    if time.monotonic() >= expires_at:
        del self._negative_cache[provider]
        return False
    return True

def _mark_rate_limited(self, provider: str) -> None:
    """Pose le provider en cache négatif pour TTL secondes."""
    from logger import get_logger
    log = get_logger(__name__)
    ttl = config.negative_cache_ttl_seconds
    self._negative_cache[provider] = time.monotonic() + ttl
    log.warning(
        "[LLM] provider %s rate-limited (429), caching for %ds",
        provider, ttl,
    )
```

### 5.a — Impact sprint 16

Le fallback transmet à `_call` les paramètres reçus par `complete`
(prompt, provider_cfg, temperature, max_tokens). **Si on ajoute `messages`
à `complete`, il faut le forwarder à `_call` exactement comme `prompt`**,
et `_call` doit choisir entre l'un et l'autre.

Pas de retraitement du payload entre providers ; chaque provider de la
chaîne recevra **la même forme** (legacy ou messages). Aucun risque de
drift inter-providers.

→ **Conclusion** : la chaîne de fallback est neutre vis-à-vis du format
multi-messages, du moment que `_call` accepte les deux formats et que
`complete` forwarde uniformément.

---

## §6 — Tests existants sur `LLMRouter`

| Fichier | Nb tests | Couvre |
|---------|----------|--------|
| `tests/llm/test_negative_cache.py` | **5** | Cache négatif 429 : insertion, skip, expiration, ignorer 5xx, ignorer exception générique. Patche `LLMRouter._call` avec `monkeypatch.setattr`. |
| `tests/conftest.py` | (fixture autouse) | `mock_network` patche `httpx.post` globalement. Réponse factice avec format OpenAI strict (`choices[0].message.content`). **Toute la suite repose dessus.** |
| `tests/execution/test_pipeline_memory_isolation.py` | (utilise `MagicMock(name="LLMRouter")`) | 6 tests d'isolation mémoire — ne touche pas au format du payload, vérifie juste que `llm_router.complete` est appelé. |

**Total à préserver tel quel au tour 2 : 5 tests sur le cache + ne rien
casser dans la fixture autouse.**

La fixture `_fake_llm_response` (`conftest.py:33-44`) retourne un JSON
au format OpenAI. La forme Anthropic n'est pas couverte — le sprint 16
n'a pas besoin de changer ça : les nouveaux tests construiront leur
propre mock.

---

## §7 — Arbitrage des trois décisions

### 7.1 — Signature

**Position architecte initiale** : `_call(*, system_prompt=None,
user_prompt=None, messages=None, ...)` avec xor entre les deux groupes.

**Réfutation à la lumière du code** : `system_prompt` n'est pas et n'a
jamais été un paramètre. La signature legacy à préserver est
`complete(prompt, role, temperature, max_tokens)`. L'arbitrage doit porter
sur `complete`, pas sur `_call`, parce que **tous les callers prod passent
par `complete`** (cf. §3).

**Options réelles** :

- **A — `complete(*, prompt=None, messages=None, role, temperature,
  max_tokens)`** : xor entre `prompt` et `messages`. Tout-keyword pour
  empêcher les appels positionnels ambigus. Les 4 callers prod actuels
  appellent `complete(prompt, ...)` ou `complete(prompt=..., ...)`. La
  forme `complete(prompt, role=..., ...)` (positionnelle sur le 1er arg)
  reste légale parce que `prompt` reste en première position keyword.

  → **Risque** : `complete(prompt, role=...)` aux lignes
  `analyst_agent.py:49` et `planner_agent.py:44` est positionnel pur sur
  `prompt`. Si on force `*` strict (tout keyword), ces deux callers
  cassent. → Solution : garder `prompt` en positionnel autorisé,
  `messages` strictement keyword.

  Signature finale recommandée :
  `complete(prompt=None, *, messages=None, role=LLMRole.CHAT,
  temperature=0.7, max_tokens=1000)`.

- **B — Deux fonctions** `complete()` legacy + `complete_messages()` :
  duplique le code de fallback. Surface d'API plus large à maintenir,
  callers prod devraient choisir explicitement. → Plus de surface, pas
  de gain de clarté.

- **C — Dispatch `complete(payload)` où `payload` est `str | list`** :
  perte de la lisibilité keyword, mélange les types côté caller, casse
  les 4 callers existants. → Rejeté.

**Recommandation** : **A**, avec `prompt` keyword optionnel positionnel
(défaut `None`) et `messages` keyword-only. `ValueError("complete():
fournir prompt OU messages, pas les deux ni aucun")` si les deux ou
aucun ne sont fournis. Tous les callers existants passent sans
modification.

Côté `_call`, propagation identique : ajouter `messages: list[dict] |
None = None` keyword. La construction du payload dans `_call` se ramifie
sur `if messages is None: ...legacy... else: ...messages...`.

### 7.2 — Validation côté router

**Position architecte initiale** : validation minimale (rôles ∈ {user,
assistant, system}, content non-None et non vide, messages non vide,
ordre non vérifié).

**Réfutation/confirmation à la lumière du code** : cette position tient.
Précisions :

- `messages` doit être une `list` non vide. Sinon `ValueError`.
- Chaque item doit être un `dict` avec exactement les clés `role` et
  `content` (au minimum). On tolère des clés en plus pour rester
  forward-compatible (Anthropic accepte `cache_control`, OpenAI accepte
  `name`).
- `role` doit appartenir à `{"user", "assistant", "system"}`. Sinon
  `ValueError` (les rôles `tool`, `function`, `developer` ne sont pas
  attendus dans ce sprint — si un caller en a besoin un jour, dette
  séparée).
- `content` doit être un `str` non vide (les `content` structurés à la
  vision multimodale ne sont pas couverts par ce sprint — pour rappel,
  `groq_vision.py` les utilise déjà mais via un autre chemin que
  `LLMRouter`).
- **Ordre non vérifié.** Le provider acceptera ou refusera. Anthropic
  exige l'alternance user/assistant ; OpenAI tolère plus de désordre.
  Laisser au provider évite de coder une logique qui finirait obsolète.

**Risques** :

- Si le router est trop laxiste, un message mal formé file vers le
  provider et l'erreur HTTP est moins lisible. → Acceptable : un dev
  qui passe un mauvais `messages` recevra une 400 explicite du provider.
- Si le router est trop strict, on bloque un usage légitime futur. → Le
  garde-fou minimal (rôle/content/non-vide) est dimensionné pour ne
  laisser passer que les évidents bugs.

**Recommandation** : validation minimale comme décrit ci-dessus, **côté
`complete` avant dispatch**, dans un helper privé `_validate_messages`.

### 7.3 — Compatibilité provider

**Position architecte initiale** : tous les providers OpenAI-compatibles
passent ; Gemini reporté en dette si conversion propriétaire.

**Confirmation à la lumière du code** :

- Mistral, Groq (×3), Cerebras, OpenRouter : passent **sans aucune
  modification du dispatch** — payload OpenAI brut.
- Anthropic : **demande un travail de conversion** dans la branche
  Anthropic de `_call`, pour extraire les `{role: system}` de la liste
  vers le param `system` top-level. Une stratégie simple :
  1. parcourir `messages`, isoler tous les `system` en les concaténant
     dans une chaîne `system_concat` (séparateur `\n\n`).
  2. construire le payload `{system: system_concat, messages: [m for m
     in messages if m["role"] != "system"]}`.
  3. si zéro `system` : utiliser une chaîne vide.
- Gemini et SambaNova : **non concernés**, absents de la `ROUTING_TABLE`.

**Risques** :

- Anthropic refuse les `messages` qui ne commencent pas par `user` ou qui
  ne respectent pas l'alternance. Si un caller passe `[{system}, {assistant},
  {user}]`, après extraction du system, l'API renverra 400. → Laissé au
  provider (cf. §7.2).
- OpenRouter ajoute deux headers conditionnels. Pas affecté par la
  signature.

**Recommandation** : sprint 16 inclut **Mistral / Groq / Cerebras /
OpenRouter / Anthropic** (i.e. tous les providers de `ROUTING_TABLE`).
Pas de dette à ouvrir.

---

## §8 — Découpage proposé pour le tour 2

### 8.a — Fichiers touchés

| Fichier | Nature de la modif | Lignes estimées |
|---------|---------------------|-----------------|
| `llm/llm_router.py` | Ajout param `messages` à `complete` et `_call` + helper `_validate_messages` + branche `messages` dans `_call` (split OpenAI / Anthropic) | ~80-100 lignes ajoutées, ~10 modifiées |
| `tests/llm/test_llm_router_messages.py` | **Nouveau fichier**, ~6 tests (voir liste ci-dessous) | ~120 lignes |

**Aucun autre fichier touché** : pas de modification des 4 callers prod
(forme legacy strictement préservée), pas de modif de `conftest.py`
(le mock OpenAI continue de fonctionner), pas de modif des fichiers
`vision/` ni `image_gen/`.

### 8.b — Tests à ajouter (énumération)

1. `test_complete_legacy_unchanged` — passer `prompt="hello"`, vérifier
   que le payload envoyé contient `messages=[{system+user}]` (cas OpenAI).
2. `test_complete_messages_transmits_as_is` — passer
   `messages=[{user}, {assistant}, {user}]`, vérifier transmission
   identique au provider OpenAI sans réinjection de `_SOUL`.
3. `test_complete_messages_anthropic_extracts_system` — passer
   `messages=[{system: A}, {system: B}, {user}]` sur la chaîne Anthropic,
   vérifier payload `{system: "A\n\nB", messages: [{user}]}`.
4. `test_complete_raises_if_both_prompt_and_messages` —
   `complete(prompt="x", messages=[...])` → `ValueError`.
5. `test_complete_raises_if_neither` — `complete()` → `ValueError`.
6. `test_complete_rejects_invalid_role` —
   `complete(messages=[{role: "tool", content: "x"}])` → `ValueError`.

Optionnel selon temps :

7. `test_complete_rejects_empty_messages` — `complete(messages=[])` →
   `ValueError`.
8. `test_complete_rejects_empty_content` — `complete(messages=[{user,
   content: ""}])` → `ValueError`.

### 8.c — Volume diff estimé

**Total ~200-220 lignes** (modifs + nouveau fichier de tests). Sous le
seuil ~300 du brief. **Tour 2 atomique faisable d'un bloc.**

---

## §9 — Risques et points d'attention

### 9.a — Caller qui construit déjà un quasi-historique

**Oui** : `agents/analyst_agent.py` (cf. §3.a). Le slot
`HISTORIQUE DE CETTE SESSION` est aujourd'hui un texte plat formaté
par `_format_memories`, concaténé dans le prompt utilisateur unique.
**C'est exactement le candidat naturel pour migrer au sprint 17** :
l'historique passera en `messages=[{role:user/assistant, content:...}, ...]`
au lieu d'être noyé dans le user prompt.

**Hors-scope sprint 16 strict.** Mentionné ici pour traçabilité fil
rouge #34.

### 9.b — Risque de drift silencieux sur Anthropic

Si on passe une liste `messages` ne contenant que des `{role: system}`
(zéro user/assistant) au provider Anthropic après extraction, l'API
renverra 400 (`messages` ne peut pas être vide). **Comportement
acceptable** — c'est un bug évident côté caller. La 400 du provider
est plus parlante qu'un check muet côté router.

Si on passe `messages` avec un `system` non-string (ex. `{role: system,
content: ["..."]}` style multimodal), `system_concat` plantera sur
`"\n\n".join`. Le check §7.2 (`content` doit être `str`) attrape ce cas
en amont.

### 9.c — Fallback inter-providers

Le `time.sleep(1)` entre deux providers de la chaîne est neutre vis-à-vis
du format. La chaîne fonctionne identiquement en forme legacy et en
forme messages, donc **pas de garde-fou supplémentaire à ajouter** pour
le fallback.

À noter : si le premier provider rate sur **format** (400 sur messages
invalide), le fallback réessayera sur le suivant avec le **même
payload**, qui sera tout aussi invalide. → Acceptable et conforme à la
sémantique actuelle (un 5xx est traité pareil). Le rate-limit cache
(429 seulement) n'est pas affecté.

### 9.d — Dette #35 (auto-sys.path tests)

`tests/llm/` n'a **pas de `__init__.py`** — convention conforme à
`tests/llm/test_negative_cache.py` qui existe déjà. Le nouveau fichier
`tests/llm/test_llm_router_messages.py` doit suivre la même convention :
**pas d'`__init__.py` à ajouter**. Imports par chemin absolu depuis la
racine repo (`from llm.llm_router import LLMRouter, LLMResponse`),
exactement comme `test_negative_cache.py:18-19`.

→ La dette #35 ne sera pas aggravée.

### 9.e — Méthode `route()` inerte

`LLMRouter.route(message, intent, phase, memory_results)` (l. 330-349)
n'est appelée nulle part en prod. Elle utilise `intent.build_llm_context`
qui doit exister sur les intents. **À documenter comme dette adjacente
hors-scope** (à proposer en clôture sprint 16 ou à conserver pour un
sprint cleanup). Ne pas la modifier ce sprint — pas dans le brief.

---

## §10 — Hors-scope confirmés

Les six hors-scope du kickoff sont **tous respectés** par le plan tour 2
proposé en §8 :

1. ❌ Aucun appel à `bridge.load_conversation_history` ajouté côté caller
   — pas touché.
2. ❌ Aucun retrait du slot `HISTORIQUE DE CETTE SESSION` dans
   `AnalystAgent` — `analyst_agent.py` n'est pas modifié.
3. ❌ Aucune modification de `MEMORY_TOP_K[CONFIRMATION]` ni de
   `MIN_MESSAGE_LENGTH` — fichiers non touchés.
4. ❌ Aucune modification de `core/event.py` — fichier non touché.
5. ❌ Aucun nettoyage de `config.max_history_turns` ni de
   `Event.conversation_id` — `config.py` non touché.
6. ❌ Pas de gestion fallback inter-providers liée au multi-messages —
   le fallback existant fonctionne tel quel (cf. §5.a).

---

## Synthèse exécutive (pour relecture rapide)

1. **Le brief tour 1 parle d'une signature `_call(system_prompt,
   user_prompt, ...)` qui n'existe pas.** La signature réelle est
   `complete(prompt, role, temperature, max_tokens)` → `_call(prompt,
   provider_cfg, temperature, max_tokens)`, avec le system prompt
   construit en dur depuis `soul.md` + `user.md` dans `_call`.
2. **Pas de wrappers par provider** : tout le dispatch HTTP est inliné
   dans `_call`, avec une seule branche conditionnelle `if provider ==
   "anthropic": ...`.
3. **Gemini et SambaNova** sont configurés mais jamais utilisés (absents
   de `ROUTING_TABLE`). Hors-scope, pas de matrice à remplir pour eux.
4. **Tous les autres providers** (Mistral, Groq×3, Cerebras, OpenRouter,
   Anthropic) sont concernés. OpenAI-compatibles passent sans modif du
   dispatch ; Anthropic demande une extraction `{role:system}` →
   param `system` top-level.
5. **Signature recommandée** : `complete(prompt=None, *, messages=None,
   role, temperature, max_tokens)` avec xor `prompt`/`messages`,
   `ValueError` si les deux ou aucun. Aucun caller prod ne casse.
6. **Validation minimale** côté router : `messages` non vide, chaque
   item dict avec rôle ∈ {user, assistant, system} et content `str`
   non vide. Ordre laissé au provider.
7. **Plan tour 2** : 1 fichier modifié + 1 fichier de test créé,
   ~200-220 lignes de diff, atomique. 5 tests préservés + 6 nouveaux
   (énumérés §8.b). Pas d'impact dette #35.
8. **Candidat sprint 17** : `analyst_agent.py` (slot historique de
   session à migrer en `messages`).
