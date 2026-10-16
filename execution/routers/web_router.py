# aria/execution/routers/web_router.py
#
# Router d'exécution pour les opérations « monde extérieur » (sprint 22).
#
# Aiguillage sur payload["op_type"], comme ImageExecutionRouter :
#   WEB_SEARCH → recherche web, puis réponse déléguée à LLMExecutionRouter
#
# Point d'extension : une capacité future (lecture d'URL, météo…) =
# une branche dans execute() + un handler + un module fournisseur.
#
# Pipeline WEB_SEARCH :
#   message + dernier échange → requête courte (LLM CHAT)
#   → search(requête) → message enrichi des résultats
#   → LLMExecutionRouter en REASONING + skip_intent
#
# Règle d'architecture :
#   Ce router n'écrit RIEN en mémoire. L'écriture conversation est faite
#   par LLMExecutionRouter (règle 1). La lecture de l'historique passe
#   par le bridge (règle 2).

from execution.routers.execution_base import BaseRouter
from cognition.cognitive_context import CognitiveOperation
from llm.llm_role import LLMRole
from web.tavily_search import search
from logger import get_logger

log = get_logger(__name__)

# Longueur max d'un extrait injecté dans le message enrichi.
_SNIPPET_MAX_CHARS = 500


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
