#aria/llm/llm_router.py

from dataclasses import dataclass
from typing import Optional

import httpx
import time
from config import config
from llm.llm_role import LLMRole

from pathlib import Path

def _load_soul() -> str:
    path = Path(config.soul_path)
    if path.exists():
        return path.read_text().strip()
    return "Tu es Aria, un assistant cognitif personnel."

def _load_user() -> str:
    path = Path(config.user_path)
    if path.exists():
        return path.read_text().strip()
    return ""

_SOUL = _load_soul()
_USER = _load_user()


@dataclass
class LLMResponse:
    content: str
    metadata: dict
    usage: Optional[dict] = None


# ==========================
# ROUTING TABLE
# ==========================

def _text_chain(deepseek_model: str) -> list[dict]:
    """Chaîne de fallback texte commune aux 4 rôles (sprint 18) :
    groq ×3 (même modèle, 3 clés) → DeepSeek → Anthropic.
    Seul le modèle DeepSeek varie selon le rôle. L'entrée `extra` est
    fusionnée dans le payload par `_call` : on y coupe le raisonnement
    DeepSeek, qui sinon consomme le budget de tokens et renvoie ''."""
    return [
        {
            "provider": "groq",
            "model": config.groq_model,
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": lambda: config.groq_api_key,
        },
        {
            "provider": "groq_2",
            "model": config.groq_model,
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": lambda: config.groq_api_key_2,
        },
        {
            "provider": "groq_3",
            "model": config.groq_model,
            "base_url": "https://api.groq.com/openai/v1",
            "api_key": lambda: config.groq_api_key_3,
        },
        {
            "provider": "deepseek",
            "model": deepseek_model,
            "base_url": "https://api.deepseek.com",
            "api_key": lambda: config.deepseek_api_key,
            "extra": {"thinking": {"type": "disabled"}},
        },
        {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": lambda: config.anthropic_api_key,
        },
    ]


ROUTING_TABLE = {
    LLMRole.CHAT: _text_chain(config.deepseek_model),
    LLMRole.PLANNING: _text_chain(config.deepseek_model),
    # Groq exclu (sprint 28) : l'analyse d'échecs dépasse seule son quota gratuit (413).
    LLMRole.REASONING: [
        e for e in _text_chain(config.deepseek_reasoning_model)
        if not e["provider"].startswith("groq")
    ],
    LLMRole.REFLECTION: _text_chain(config.deepseek_model),
    # Synthèse de page (sprint 23) : Groq exclu (contexte trop court pour
    # une page entière) → DeepSeek puis Anthropic.
    LLMRole.DIGEST: [
        e for e in _text_chain(config.deepseek_model)
        if not e["provider"].startswith("groq")
    ],
}

# fallback global si role inconnu
DEFAULT_CHAIN = ROUTING_TABLE[LLMRole.CHAT]

# Sprint 31 / dette #73 : au-delà de cette taille (en caractères), le
# payload dépasserait le palier ITPM Groq (7000 tokens) → 413 certain.
# On saute alors Groq d'emblée, sans aller-retour HTTP ni sommeil.
GROQ_MAX_PAYLOAD_CHARS = 12_000


# ==========================
# ROUTER
# ==========================

class LLMRouter:
    """
    Router LLM avec fallback chain et cache négatif des 429.

    Cache négatif (dette #8) : un provider qui renvoie 429 est skippé
    sur les requêtes suivantes pendant `config.negative_cache_ttl_seconds`
    (défaut 5 min) — évite de retenter et de tomber en fallback à chaque
    message le temps que le quota free tier se libère. Détails et
    justification : docs/sprint5/audit_negative_cache.md.
    """

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

    @staticmethod
    def _validate_messages(messages) -> None:
        """Valide la forme `messages=[...]` du sprint 16.

        Garde-fou minimal (cf. audit §7.2) : forme, rôle, content non vide.
        L'ordre user/assistant et l'alternance ne sont pas vérifiés — laissé
        au provider qui renverra une 400 explicite si la séquence est
        invalide.
        """
        if not isinstance(messages, list):
            raise ValueError(
                f"messages doit être une list, reçu {type(messages).__name__}"
            )
        if not messages:
            raise ValueError("messages est vide")

        valid_roles = {"user", "assistant", "system"}
        for i, m in enumerate(messages):
            if not isinstance(m, dict):
                raise ValueError(f"messages[{i}] n'est pas un dict")
            if "role" not in m:
                raise ValueError(f"messages[{i}]: clé 'role' manquante")
            if "content" not in m:
                raise ValueError(f"messages[{i}]: clé 'content' manquante")
            role = m["role"]
            if role not in valid_roles:
                raise ValueError(
                    f"messages[{i}]: role {role!r} invalide "
                    f"(attendu user/assistant/system)"
                )
            content = m["content"]
            if not isinstance(content, str):
                raise ValueError(
                    f"messages[{i}]: content doit être une str, reçu "
                    f"{type(content).__name__}"
                )
            if not content.strip():
                raise ValueError(
                    f"messages[{i}]: content vide ou whitespace seulement"
                )

    def complete(
        self,
        prompt: str | None = None,
        *,
        messages: list[dict] | None = None,
        role: LLMRole = LLMRole.CHAT,
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        # Xor strict — un seul des deux modes à la fois (cf. audit §7.1).
        if prompt is None and messages is None:
            raise ValueError(
                "complete(): fournir prompt OU messages, pas aucun"
            )
        if prompt is not None and messages is not None:
            raise ValueError(
                "complete(): fournir prompt OU messages, pas les deux"
            )

        if messages is not None:
            self._validate_messages(messages)

        from logger import get_logger
        log = get_logger(__name__)

        chain = ROUTING_TABLE.get(role, DEFAULT_CHAIN)
        last_error = None
        # Un 413 Groq (requête trop grosse pour le palier ITPM) est
        # déterministe : les autres entrées groq* (même modèle, même
        # limite) échoueraient pareil. Local à cette requête : pas de cache.
        groq_too_large = False
        # Taille du payload : le prompt, ou la somme des contenus des messages.
        if messages is not None:
            size = sum(len(m["content"]) for m in messages)
        else:
            size = len(prompt)

        for i, provider_cfg in enumerate(chain):
            provider = provider_cfg["provider"]

            # Skip direct si récemment 429 — pas de tentative HTTP.
            if self._is_rate_limited(provider):
                log.info("[LLM] provider %s skipped (cached 429)", provider)
                continue

            if groq_too_large and provider.startswith("groq"):
                log.info("[LLM] provider %s skipped (413 sur groq)", provider)
                continue

            # Saut préventif : placé avant le try, il ne déclenche pas le
            # time.sleep(1) de fin d'except.
            if size > GROQ_MAX_PAYLOAD_CHARS and provider.startswith("groq"):
                log.info("[LLM] provider %s skipped (payload %d chars > %d)",
                         provider, size, GROQ_MAX_PAYLOAD_CHARS)
                continue

            # On ne forwarde `messages` à `_call` que dans la branche
            # nouvelle : la branche legacy garde sa signature d'origine,
            # ce qui préserve le patch monkeypatch de test_negative_cache.
            call_kwargs = dict(
                prompt=prompt,
                provider_cfg=provider_cfg,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if messages is not None:
                call_kwargs["messages"] = messages

            try:
                return self._call(**call_kwargs)
            except Exception as e:
                if isinstance(e, httpx.HTTPStatusError):
                    # Le corps porte la limite et la taille demandée.
                    log.error("[LLM FALLBACK] %s failed: %s | %s",
                              provider, e, e.response.text[:200])
                    if (e.response.status_code == 413
                            and provider.startswith("groq")):
                        groq_too_large = True
                else:
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

    @classmethod
    def build_base_system_prompt(cls) -> str:
        """
        System prompt de base d'ARIA : _SOUL, puis le profil utilisateur
        s'il existe. Source de vérité unique, partagée entre la forme
        legacy de _call et les callers en forme messages (AnalystAgent).
        """
        system_parts = [_SOUL]
        if _USER:
            system_parts.append(f"\n\nPROFIL UTILISATEUR :\n{_USER}")
        return "\n".join(system_parts)

    def _call(
        self,
        prompt: str | None,
        provider_cfg: dict,
        temperature: float,
        max_tokens: int,
        *,
        messages: list[dict] | None = None,
    ) -> LLMResponse:

        from logger import get_logger
        log = get_logger(__name__)

        api_key = provider_cfg["api_key"]()
        provider = provider_cfg["provider"]

        # ── Construction des messages selon le mode ──────────────────────────
        if messages is None:
            # Forme legacy : on construit le system prompt depuis _SOUL/_USER
            # et on l'injecte avec le user prompt unique.
            system_prompt = self.build_base_system_prompt()

            if provider == "anthropic":
                anthropic_system: str | None = system_prompt
                anthropic_messages = [{"role": "user", "content": prompt}]
            else:
                openai_messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ]
        else:
            # Forme nouvelle (sprint 16) : caller fournit messages complet,
            # le router n'injecte ni _SOUL ni _USER. Anthropic exige
            # néanmoins d'extraire les {role:system} vers le param top-level.
            if provider == "anthropic":
                system_parts_list = [
                    m["content"] for m in messages if m["role"] == "system"
                ]
                anthropic_system = (
                    "\n\n".join(system_parts_list)
                    if system_parts_list
                    else None
                )
                anthropic_messages = [
                    m for m in messages if m["role"] != "system"
                ]
            else:
                openai_messages = messages  # transmis tel quel

        # ── Dispatch HTTP ────────────────────────────────────────────────────
        if provider == "anthropic":
            url = f"{provider_cfg['base_url']}/messages"
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }
            payload = {
                "model": provider_cfg["model"],
                "max_tokens": max_tokens,
                "messages": anthropic_messages,
                "temperature": temperature,
            }
            if anthropic_system:
                payload["system"] = anthropic_system

            response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
            response.raise_for_status()
            data = response.json()
            content = data["content"][0]["text"]
            # Réponse vide = échec : on lève pour que complete() passe au
            # provider suivant au lieu de renvoyer '' au caller.
            if content is None or not content.strip():
                raise ValueError(
                    f"{provider}: réponse vide "
                    f"(stop_reason={data.get('stop_reason')})"
                )
            log.info("[LLM] Anthropic (%s) a répondu.", provider_cfg["model"])
            return LLMResponse(
                content=content,
                metadata={
                    "provider": provider,
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
        if provider == "openrouter":
            headers["HTTP-Referer"] = "https://aria.local"
            headers["X-Title"] = "Aria"

        payload = {
            "model": provider_cfg["model"],
            "messages": openai_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        # Paramètres propres au provider (ex. DeepSeek : thinking désactivé).
        payload.update(provider_cfg.get("extra", {}))
        response = httpx.post(url, json=payload, headers=headers, timeout=30.0)
        response.raise_for_status()

        data = response.json()
        choice = data["choices"][0]
        content = choice["message"]["content"]
        # Réponse vide = échec (un modèle à raisonnement peut renvoyer ''
        # quand le budget de tokens est épuisé) → fallback dans complete().
        if content is None or not content.strip():
            raise ValueError(
                f"{provider}: réponse vide "
                f"(finish_reason={choice.get('finish_reason')})"
            )
        log.info("[LLM] %s (%s) a répondu.", provider, provider_cfg["model"])

        return LLMResponse(
            content=content,
            metadata={
                "provider": provider,
                "model": provider_cfg["model"],
            },
            usage=data.get("usage"),
        )

    # ==========================
    # ASYNC ROUTE (kernel usage)
    # ==========================

    async def route(
        self,
        message: str,
        intent,
        phase: str,
        memory_results: list[dict],
    ) -> LLMResponse:

        context = intent.build_llm_context(
            memory_results=memory_results,
            phase=phase,
        )

        prompt = (
            f"Intent: {context['intent_name']}\n"
            f"Phase: {context['phase']}\n"
            f"Message: {message}"
        )

        return self.complete(prompt, role=LLMRole.CHAT)