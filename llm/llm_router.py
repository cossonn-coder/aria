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

ROUTING_TABLE = {
    LLMRole.CHAT: [
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
            "provider": "mistral",
            "model": config.mistral_model,
            "base_url": "https://api.mistral.ai/v1",
            "api_key": lambda: config.mistral_api_key,
        },
        {
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": lambda: config.openrouter_api_key,
        },
        {
            "provider": "cerebras",
            "model": "llama3.1-8b",
            "base_url": "https://api.cerebras.ai/v1",
            "api_key": lambda: config.cerebras_api_key,
        },
        {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": lambda: config.anthropic_api_key,
        },
    ],
    # ... reste inchangé
    LLMRole.PLANNING: [
        {
            "provider": "mistral",
            "model": config.mistral_model,
            "base_url": "https://api.mistral.ai/v1",
            "api_key": lambda: config.mistral_api_key,
        },
        {   "provider": "cerebras",
            "model": "llama-3.3-70b", 
            "base_url": "https://api.cerebras.ai/v1",
            "api_key": lambda: config.cerebras_api_key,
        },
        {
            "provider": "openrouter",
            "model": "meta-llama/llama-3.3-70b-instruct:free",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": lambda: config.openrouter_api_key,
        },
        {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": lambda: config.anthropic_api_key,
        },
    ],
    LLMRole.REASONING: [
        {
            "provider": "cerebras",
            "model": config.cerebras_model,
            "base_url": "https://api.cerebras.ai/v1",
            "api_key": lambda: config.cerebras_api_key,
        },
        {
            "provider": "openrouter",
            "model": "google/gemma-3-27b-it:free",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": lambda: config.openrouter_api_key,
        },
        {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": lambda: config.anthropic_api_key,
        },
    ],
    LLMRole.REFLECTION: [
        {
            "provider": "mistral",
            "model": config.mistral_model,
            "base_url": "https://api.mistral.ai/v1",
            "api_key": lambda: config.mistral_api_key,
        },
        {
            "provider": "openrouter",
            "model": "nvidia/nemotron-3-super-120b-a12b:free",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": lambda: config.openrouter_api_key,
        },
        {
            "provider": "anthropic",
            "model": "claude-haiku-4-5",
            "base_url": "https://api.anthropic.com/v1",
            "api_key": lambda: config.anthropic_api_key,
        },
    ],
}

# fallback global si role inconnu
DEFAULT_CHAIN = ROUTING_TABLE[LLMRole.CHAT]


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