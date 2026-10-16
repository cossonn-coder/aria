# aria/execution/routers/web_router.py
#
# Router d'exécution pour les opérations « monde extérieur » (sprint 22).
#
# Aiguillage sur payload["op_type"], comme ImageExecutionRouter :
#   WEB_SEARCH → recherche web, puis réponse déléguée à LLMExecutionRouter
#   URL_READ   → lecture d'une page (sprint 23), synthèse, puis délégation
#
# Point d'extension : une capacité future (météo…) =
# une branche dans execute() + un handler + un module fournisseur.
#
# Pipeline WEB_SEARCH :
#   message + dernier échange → requête courte (LLM CHAT)
#   → search(requête) → message enrichi des résultats
#   → LLMExecutionRouter en REASONING + skip_intent
#
# Pipeline URL_READ (sprint 23) :
#   première URL du message → extract(url) → tranche de 100 000 car.
#   coupée en fin de paragraphe → synthèse (LLM DIGEST, sans Groq)
#   → message enrichi de la synthèse (+ marqueur de lecture partielle)
#   → LLMExecutionRouter en REASONING + skip_intent. C'est donc la
#   synthèse, pas la page, qui part dans l'historique.
#
# Règle d'architecture :
#   Ce router n'écrit RIEN en mémoire. L'écriture conversation est faite
#   par LLMExecutionRouter (règle 1). La lecture de l'historique passe
#   par le bridge (règle 2).

from execution.routers.execution_base import BaseRouter
from cognition.cognitive_classifier import detect_url
from cognition.cognitive_context import CognitiveOperation, URL_PARTIAL_MARKER
from llm.llm_role import LLMRole
from web.tavily_search import extract, search
from logger import get_logger

log = get_logger(__name__)

# Longueur max d'un extrait injecté dans le message enrichi.
_SNIPPET_MAX_CHARS = 500

# Taille max d'une tranche de page envoyée à la synthèse [arbitraire, sprint 23].
_SLICE_MAX_CHARS = 100_000

# Budget de la synthèse ; l'atteindre = synthèse probablement coupée.
_DIGEST_MAX_TOKENS = 1000


class WebExecutionRouter(BaseRouter):
    """
    Effecteur web du pipeline d'exécution.

    Args:
        llm_router           : LLMRouter — reformulation de la requête
        mempalace_bridge     : MempalaceBridge — lecture du dernier échange
        llm_execution_router : LLMExecutionRouter — production de la réponse
    """

    def __init__(self, llm_router, mempalace_bridge, llm_execution_router):
        self.llm_router           = llm_router
        self.mempalace_bridge     = mempalace_bridge
        self.llm_execution_router = llm_execution_router

    def execute(self, payload: dict) -> dict:
        op_type = payload.get("op_type", "")

        if op_type == CognitiveOperation.WEB_SEARCH.value:
            return self._handle_search(payload)

        if op_type == CognitiveOperation.URL_READ.value:
            return self._handle_url_read(payload)

        raise ValueError(f"WebExecutionRouter: op_type inconnu '{op_type}'")

    # =========================================================
    # WEB SEARCH
    # =========================================================

    def _handle_search(self, payload: dict) -> dict:
        message  = str(payload.get("content") or "")
        metadata = payload.get("metadata", {})

        query = self._build_query(message, metadata)

        # Échec de recherche (exception ou 0 résultat) : consigne au LLM
        # plutôt qu'une erreur remontée à l'utilisateur.
        try:
            results = search(query)
            if not results:
                raise RuntimeError("aucun résultat")
        except Exception as e:
            log.warning("web_search FAILED query=%r error=%s", query, e)
            enriched = (
                "[Recherche web indisponible : dis-le à Nico en une phrase, puis "
                "réponds si tu peux en précisant que ce n'est pas vérifié.]\n\n"
                f"{message}"
            )
        else:
            log.info("web_search OK provider=tavily results=%d query=%r", len(results), query)
            lines = [f"[Résultats web pour « {query} » :"]
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r['title']} — {r['url']}")
                lines.append(f"   {r['content'][:_SNIPPET_MAX_CHARS]}")
            enriched = (
                "\n".join(lines) + "]\n"
                "[Consigne : réponds à partir de ces résultats et termine par la "
                "liste des URL utilisées ; si les résultats ne répondent pas à la "
                "question, dis-le.]\n\n"
                f"{message}"
            )

        return self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            # skip_intent : une recherche web ne résout ni ne mute d'intent
            "metadata": {**metadata, "skip_intent": True},
        })

    def _build_query(self, message: str, metadata: dict) -> str:
        """
        Reformule le message en requête de recherche courte.

        Le dernier échange est fourni au LLM : indispensable pour « source ? »,
        dont la requête est le sujet du tour précédent. Si l'appel LLM lève,
        la requête est le message brut.
        """
        conversation_key = str(metadata.get("chat_id", "default"))
        try:
            history = self.mempalace_bridge.load_conversation_history(conversation_key, n=2)
            last_exchange = "\n".join(f"{t['role']}: {t['content']}" for t in history)
            prompt = (
                "Formule une requête de recherche web courte (quelques mots, sans "
                "guillemets ni explication) pour répondre au message de "
                "l'utilisateur. Si le message renvoie au tour précédent (ex. « source ? »), "
                "la requête porte sur le sujet de ce tour.\n\n"
                f"Dernier échange :\n{last_exchange or '(aucun)'}\n\n"
                f"Message : {message}\n\nRequête :"
            )
            response = self.llm_router.complete(
                prompt=prompt, role=LLMRole.CHAT, temperature=0.1, max_tokens=40,
            )
            query = response.content.strip().strip('"«» ')
            return query or message
        except Exception as e:
            log.warning("web_search query reformulation failed, raw message used: %s", e)
            return message


    # =========================================================
    # URL READ
    # =========================================================

    def _handle_url_read(self, payload: dict) -> dict:
        message  = str(payload.get("content") or "")
        metadata = payload.get("metadata", {})
        return self._read_slice(detect_url(message), 0, message, metadata)

    def _read_slice(self, url: str, start: int, message: str, metadata: dict) -> dict:
        """
        Lit une tranche de la page à partir de `start`, la synthétise et
        délègue la réponse à LLMExecutionRouter.

        Réutilisée au tronçon 02 (« lis la suite ») avec start > 0.
        """
        try:
            page = extract(url)
            text = page["content"]
            total = len(text)
            chunk = _cut_slice(text, start)
            end = start + len(chunk)

            prompt = (
                "Voici le texte d'une page web. Fais-en une synthèse fidèle en "
                "français, sans rien inventer. Si le message de Nico contient une "
                "consigne ou une question, oriente la synthèse en conséquence ; "
                "sinon, fais un résumé général.\n\n"
                f"Titre : {page['title']}\nURL : {url}\n"
                f"Message de Nico : {message}\n\n"
                f"Texte (caractères {start}-{end} sur {total}) :\n{chunk}\n\nSynthèse :"
            )
            response = self.llm_router.complete(
                prompt=prompt, role=LLMRole.DIGEST,
                temperature=0.3, max_tokens=_DIGEST_MAX_TOKENS,
            )
            digest = response.content.strip()
        except Exception as e:
            log.warning("url_read FAILED url=%s error=%s", url, e)
            enriched = f"[Page illisible : dis-le à Nico en une phrase.]\n\n{message}"
        else:
            # Tokens de sortie : DeepSeek (format OpenAI) ou Anthropic.
            usage = response.usage or {}
            digest_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
            log.info(
                "url_read OK url=%s page_chars=%d start=%d end=%d digest_tokens=%s",
                url, total, start, end, digest_tokens,
            )
            if digest_tokens is not None and digest_tokens >= _DIGEST_MAX_TOKENS:
                log.warning("url_read digest hit max_tokens=%d url=%s", _DIGEST_MAX_TOKENS, url)

            parts = [
                f"[Synthèse de la page « {page['title']} » — {url} "
                f"(caractères {start}-{end} sur {total}) :\n{digest}]"
            ]
            if end < total:
                parts.append(f"{URL_PARTIAL_MARKER} {url} caractères {start}-{end} sur {total}]")
                parts.append(
                    f"[Consigne : dis à Nico que tu as lu les caractères {start} à {end} "
                    f"sur {total}, donne la synthèse ou la réponse à partir de cette "
                    "synthèse, puis propose-lui de lire la suite.]"
                )
            else:
                parts.append("[Consigne : réponds à partir de cette synthèse et cite l'URL.]")
            enriched = "\n".join(parts) + f"\n\n{message}"

        return self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            # skip_intent : la lecture d'une page ne résout ni ne mute d'intent
            "metadata": {**metadata, "skip_intent": True},
        })


def _cut_slice(text: str, start: int) -> str:
    """
    Tranche de `_SLICE_MAX_CHARS` caractères max à partir de `start`.

    Si la page continue au-delà, la tranche est raccourcie pour finir en
    fin de paragraphe (dernier "\n"), à défaut en fin de phrase (". "),
    à défaut sur un espace — jamais au milieu d'un mot.
    """
    chunk = text[start : start + _SLICE_MAX_CHARS]
    if start + len(chunk) >= len(text):
        return chunk
    for sep in ("\n", ". ", " "):
        idx = chunk.rfind(sep)
        if idx > 0:
            # Le "\n" et le "." restent dans la tranche ; l'espace non.
            return chunk[: idx + 1] if sep != " " else chunk[:idx]
    return chunk
