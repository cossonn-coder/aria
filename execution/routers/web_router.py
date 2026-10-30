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
# Pipeline FILE_READ (sprint 42) : document reçu sur Telegram, même
#   pipeline qu'URL_READ ; le texte vient de files.extract.extract_text
#   (chemin local) au lieu de Tavily. Le marqueur de lecture partielle
#   porte alors le chemin du fichier : « lis la suite » le relit du disque.
#
# Mémoire des documents lus (sprint 43) : à la première tranche (start == 0)
#   d'un FILE_READ ou d'un URL_READ réussi, la fiche (nom, source, synthèse)
#   et le texte intégral extrait sont écrits via writer.write_document.
#
# Pipeline DOC_REREAD (sprint 43) : fiche retrouvée par le sens (room
#   documents) → source → texte intégral lu dans aria_documents via le
#   bridge → même synthèse qu'URL_READ, sans fichier, Tavily ni OCR, et
#   sans réécrire la fiche.
#
# Pipeline WEB_RESEARCH (sprint 45), une seule vague :
#   4 derniers messages + 4 souvenirs (bridge) → plan de 3 à 5 requêtes
#   (LLM CHAT) → search() par requête → lecture intégrale de 3 pages sans
#   doublon (extract, à défaut l'extrait Tavily) → rapport (LLM DIGEST)
#   → rapport écrit comme un document lu (write_document, source
#   « recherche:<date>-<sha8> ») → LLMExecutionRouter en REASONING + skip_intent.
#
# Règle d'architecture :
#   Ce router n'écrit en mémoire que la fiche document, via memory/writer.py
#   (règle 1). L'écriture conversation est faite par LLMExecutionRouter.
#   La lecture de l'historique passe par le bridge (règle 2).

import hashlib
import re
from datetime import date
from pathlib import Path

from execution.routers.execution_base import BaseRouter
from cognition.cognitive_classifier import _DOC_REREAD_WORDS, detect_url
from cognition.cognitive_context import CognitiveOperation, REREAD_PROPOSAL, URL_PARTIAL_MARKER
from files.extract import extract_text
from llm.llm_role import LLMRole
from memory.writer import write_document
from web.tavily_search import extract, search
from logger import get_logger

log = get_logger(__name__)

# Longueur max d'un extrait injecté dans le message enrichi.
_SNIPPET_MAX_CHARS = 500

# Taille max d'une tranche de page envoyée à la synthèse [arbitraire, sprint 23].
_SLICE_MAX_CHARS = 100_000

# Marqueur de lecture partielle relu au tour suivant (« lis la suite »).
# Format exact émis par _read_slice : « <marqueur> <url> caractères <start>-<end> sur <total>] ».
_PARTIAL_RE = re.compile(re.escape(URL_PARTIAL_MARKER) + r" (\S+) caractères \d+-(\d+) sur \d+\]")

# Fiche document (sprint 43, format du tronçon 01) : ligne de source.
_SOURCE_RE = re.compile(r"^Source : (\S+)$", re.MULTILINE)

# Nom du document dans la proposition de relecture : « Veux-tu que je relise « X » ? ».
_PROPOSAL_RE = re.compile(re.escape(REREAD_PROPOSAL) + r"(.+?) »")

# Budget de la synthèse ; l'atteindre = synthèse probablement coupée.
_DIGEST_MAX_TOKENS = 1000

# Recherche autonome (sprint 45) : pages lues en entier, et taille max de
# chacune dans le prompt du rapport [arbitraire].
_RESEARCH_PAGES = 3
_RESEARCH_PAGE_MAX_CHARS = 30_000
_RESEARCH_MAX_QUERIES = 5


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

        if op_type == CognitiveOperation.FILE_READ.value:
            # Le content est le dict de l'Event FILE {file_path, file_name, caption}.
            content = payload.get("content") or {}
            return self._read_slice(
                content["file_path"], 0, content.get("caption") or "",
                payload.get("metadata", {}), name=content.get("file_name"),
            )

        if op_type == CognitiveOperation.DOC_REREAD.value:
            return self._handle_doc_reread(payload)

        if op_type == CognitiveOperation.WEB_RESEARCH.value:
            return self._handle_research(payload)

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
    # WEB RESEARCH (sprint 45)
    # =========================================================

    def _handle_research(self, payload: dict) -> dict:
        message  = str(payload.get("content") or "")
        metadata = payload.get("metadata", {})
        subject  = message[:80]

        queries = self._plan_research(message, metadata)

        # ── Recherche : séquentielle, une requête en échec n'arrête pas les autres ──
        results_by_query = []
        for q in queries:
            try:
                results_by_query.append(search(q))
            except Exception as e:
                log.warning("web_research search FAILED query=%r error=%s", q, e)
        n_results = sum(len(r) for r in results_by_query)
        if n_results == 0:
            log.warning("web_research FAILED: no result for %d queries", len(queries))
            return self._delegate_unavailable(message, metadata)

        # ── Lecture : 1er résultat de chaque requête, puis les suivants, sans doublon ──
        candidates, seen = [], set()
        for rank in range(max(len(r) for r in results_by_query)):
            for results in results_by_query:
                if rank < len(results) and results[rank]["url"] not in seen:
                    seen.add(results[rank]["url"])
                    candidates.append(results[rank])
        pages, failed = [], 0
        for r in candidates[:_RESEARCH_PAGES]:
            try:
                text = extract(r["url"])["content"]
            except Exception as e:
                # Échec de lecture : on garde l'extrait Tavily du résultat.
                log.warning("web_research extract FAILED url=%s error=%s", r["url"], e)
                failed += 1
                text = r["content"]
            pages.append({"title": r["title"], "url": r["url"], "content": text[:_RESEARCH_PAGE_MAX_CHARS]})
        log.info("web_research pages read=%d failed=%d", len(pages) - failed, failed)

        # ── Rapport : pages lues + extraits des autres résultats ──
        read_urls = {p["url"] for p in pages}
        blocks = [f"### {p['title']} — {p['url']}\n{p['content']}" for p in pages]
        snippets = [
            f"- {r['title']} — {r['url']}\n  {r['content'][:_SNIPPET_MAX_CHARS]}"
            for r in candidates if r["url"] not in read_urls
        ]
        prompt = (
            "Rédige un rapport de recherche fidèle en français sur la demande de Nico, "
            "sans rien inventer, uniquement à partir des pages et des extraits ci-dessous. "
            "Termine par la liste des URL utilisées.\n\n"
            f"Demande de Nico : {message}\n\n"
            "Pages lues :\n" + "\n\n".join(blocks) + "\n\n"
            "Autres extraits :\n" + ("\n".join(snippets) or "(aucun)") + "\n\nRapport :"
        )
        try:
            response = self.llm_router.complete(
                prompt=prompt, role=LLMRole.DIGEST, temperature=0.3, max_tokens=1500,
            )
            report = response.content.strip()
        except Exception as e:
            log.warning("web_research report FAILED error=%s", e)
            return self._delegate_unavailable(message, metadata)

        # ── Trace (non bloquante) : le rapport est conservé comme un document lu ──
        # Source sans espace : _SOURCE_RE doit la relire.
        source = f"recherche:{date.today().isoformat()}-{hashlib.sha256(message.encode()).hexdigest()[:8]}"
        doc_name = f"Recherche : {subject}"
        fiche = (
            f"Document « {doc_name} » lu le {date.today().isoformat()}\n"
            f"Source : {source}\n"
            f"Synthèse : {report}"
        )
        key = hashlib.sha256(source.encode()).hexdigest()[:16]
        try:
            write_document(fiche, report, source, doc_name)
            log.info("document_write OK key=%s source=%s chars=%d", key, source, len(report))
        except Exception:
            log.exception("document_write ERROR key=%s source=%s", key, source)

        log.info(
            "web_research OK queries=%d results=%d pages=%d",
            len(queries), n_results, len(pages),
        )
        enriched = (
            f"[Rapport de recherche « {subject} » :\n{report}]\n"
            "[Consigne : réponds à Nico à partir de ce rapport et termine par la "
            "liste des URL utilisées.]\n\n"
            f"{message}"
        )
        return self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            # skip_intent : une recherche ne résout ni ne mute d'intent
            "metadata": {**metadata, "skip_intent": True},
        })

    def _plan_research(self, message: str, metadata: dict) -> list[str]:
        """
        Plan de 3 à 5 requêtes web, construit à partir de la conversation
        récente et des souvenirs de Nico. Échec du LLM ou plan vide :
        la seule requête est le message brut.
        """
        conversation_key = str(metadata.get("chat_id", "default"))
        try:
            history = self.mempalace_bridge.load_conversation_history(conversation_key, n=4)
            hits = self.mempalace_bridge.retrieve_memories(message, n=4)["hits"]
            conversation = "\n".join(f"{t['role']}: {t['content']}" for t in history)
            memories = "\n".join(f"- {h.get('text', '')[:300]}" for h in hits)
            prompt = (
                "Formule 3 à 5 requêtes de recherche web courtes couvrant les différents "
                "angles du sujet demandé par Nico, en tenant compte de la conversation "
                "et de ses souvenirs. Une requête par ligne, rien d'autre.\n\n"
                f"Conversation récente :\n{conversation or '(aucune)'}\n\n"
                f"Souvenirs de Nico :\n{memories or '(aucun)'}\n\n"
                f"Demande : {message}\n\nRequêtes :"
            )
            response = self.llm_router.complete(
                prompt=prompt, role=LLMRole.CHAT, temperature=0.2, max_tokens=200,
            )
            # Nettoyage : puces, numéros (« 1. », « 2) ») et guillemets.
            queries = [
                re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip().strip('"«» ')
                for line in response.content.splitlines()
            ]
            queries = [q for q in queries if q][:_RESEARCH_MAX_QUERIES]
        except Exception as e:
            log.warning("web_research plan failed, raw message used: %s", e)
            queries = []
        queries = queries or [message]
        log.info("web_research plan queries=%d %r", len(queries), queries)
        return queries

    def _delegate_unavailable(self, message: str, metadata: dict) -> dict:
        """Même consigne que _handle_search quand la recherche web échoue."""
        enriched = (
            "[Recherche web indisponible : dis-le à Nico en une phrase, puis "
            "réponds si tu peux en précisant que ce n'est pas vérifié.]\n\n"
            f"{message}"
        )
        return self.llm_execution_router.execute({
            "op_type" : CognitiveOperation.REASONING.value,
            "content" : enriched,
            "metadata": {**metadata, "skip_intent": True},
        })

    # =========================================================
    # URL READ
    # =========================================================

    def _handle_url_read(self, payload: dict) -> dict:
        message  = str(payload.get("content") or "")
        metadata = payload.get("metadata", {})
        url = detect_url(message)
        if url:
            return self._read_slice(url, 0, message, metadata)

        # Pas d'URL : reprise (« oui », « lis la suite »). L'URL et la
        # position viennent du marqueur du dernier tour `user`.
        conversation_key = str(metadata.get("chat_id", "default"))
        history = self.mempalace_bridge.load_conversation_history(conversation_key, n=2)
        user_turns = [t["content"] for t in history if t.get("role") == "user"]
        match = _PARTIAL_RE.search(user_turns[-1]) if user_turns else None
        if match is None:
            log.warning("url_read resume FAILED: partial marker not found")
            enriched = f"[Page illisible : dis-le à Nico en une phrase.]\n\n{message}"
            return self.llm_execution_router.execute({
                "op_type" : CognitiveOperation.REASONING.value,
                "content" : enriched,
                "metadata": {**metadata, "skip_intent": True},
            })
        return self._read_slice(match.group(1), int(match.group(2)), message, metadata)

    # =========================================================
    # DOC REREAD (sprint 43)
    # =========================================================

    def _handle_doc_reread(self, payload: dict) -> dict:
        message  = str(payload.get("content") or "")
        metadata = payload.get("metadata", {})

        # Acceptation d'une proposition : le nom vient de la proposition,
        # la question du dernier tour `user` (restée sans réponse).
        # Sinon (« relis… ») : requête = question = le message.
        query = question = message
        if not any(w in message.lower() for w in _DOC_REREAD_WORDS):
            conversation_key = str(metadata.get("chat_id", "default"))
            history = self.mempalace_bridge.load_conversation_history(conversation_key, n=2)
            assistant_turns = [t["content"] for t in history if t.get("role") == "assistant"]
            match = _PROPOSAL_RE.search(assistant_turns[-1]) if assistant_turns else None
            if match:
                query = match.group(1)
                user_turns = [t["content"] for t in history if t.get("role") == "user"]
                if user_turns:
                    question = user_turns[-1]

        # Mots porteurs : 1re fiche qui en contient un, sinon NOT_FOUND (#147).
        # Sans mot porteur (« relis le document ») : meilleure fiche de la room.
        hits = self.mempalace_bridge.find_documents(query)
        if hits is None:
            hits = self.mempalace_bridge.retrieve_memories(query, room="documents", n=1)["hits"]
        source_match = _SOURCE_RE.search(hits[0].get("text", "")) if hits else None
        doc = self.mempalace_bridge.load_document_text(source_match.group(1)) if source_match else None
        if doc is None:
            log.info("doc_reread NOT_FOUND query=%r", query)
            enriched = (
                "[Aucun document correspondant en mémoire : dis-le à Nico en une phrase.]\n\n"
                f"{message}"
            )
            return self.llm_execution_router.execute({
                "op_type" : CognitiveOperation.REASONING.value,
                "content" : enriched,
                "metadata": {**metadata, "skip_intent": True},
            })

        source = source_match.group(1)
        log.info("doc_reread OK source=%s chars=%d", source, len(doc["text"]))
        return self._read_slice(
            source, 0, question, metadata,
            page={"title": doc["title"], "content": doc["text"]},
        )

    def _read_slice(
        self, url: str, start: int, message: str, metadata: dict, name: str | None = None,
        page: dict | None = None,
    ) -> dict:
        """
        Lit une tranche de la page à partir de `start`, la synthétise et
        délègue la réponse à LLMExecutionRouter.

        Appelée avec start > 0 pour « lis la suite » (tronçon 02).
        `url` est une URL http(s) ou, pour FILE_READ, le chemin local du
        fichier reçu (sprint 42) : seuls la source du texte et les
        libellés changent. `name` : nom d'origine du fichier, porté par
        la fiche document (à défaut, le titre de la page). `page` :
        titre et texte déjà connus (relecture depuis le palace, sprint 43) ;
        ni extraction ni réécriture de la fiche dans ce cas.
        """
        reread = page is not None
        is_file = not url.startswith(("http://", "https://"))
        source = "du fichier" if is_file else "de la page"
        kind = "d'un fichier" if is_file else "d'une page web"
        # En reprise (start > 0), « oui » n'oriente pas la synthèse.
        request = message if start == 0 else "(suite de la lecture : résumé général)"
        try:
            if reread:
                pass  # titre et texte fournis par le palace
            elif is_file:
                # Titre = nom téléchargé, qui contient le nom d'origine.
                page = {"title": Path(url).name, "content": extract_text(url)}
            else:
                page = extract(url)
            text = page["content"]
            total = len(text)
            chunk = _cut_slice(text, start)
            end = start + len(chunk)

            prompt = (
                f"Voici le texte {kind}. Fais-en une synthèse fidèle en "
                "français, sans rien inventer. Si le message de Nico contient une "
                "consigne ou une question, oriente la synthèse en conséquence ; "
                "sinon, fais un résumé général.\n\n"
                f"Titre : {page['title']}\n{'Fichier' if is_file else 'URL'} : {url}\n"
                f"Message de Nico : {request}\n\n"
                f"Texte (caractères {start}-{end} sur {total}) :\n{chunk}\n\nSynthèse :"
            )
            response = self.llm_router.complete(
                prompt=prompt, role=LLMRole.DIGEST,
                temperature=0.3, max_tokens=_DIGEST_MAX_TOKENS,
            )
            digest = response.content.strip()
        except Exception as e:
            log.warning("url_read FAILED url=%s error=%s", url, e)
            unreadable = "Fichier illisible" if is_file else "Page illisible"
            enriched = f"[{unreadable} : dis-le à Nico en une phrase.]\n\n{message}"
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

            # ── Fiche document (non bloquante), à la première tranche seulement ──
            # Nom et source en tête : l'embedder ne lit que ≈ 128 tokens.
            # Format parsé par le tronçon 02 du sprint 43 : ne pas changer.
            if start == 0 and not reread:
                doc_name = name or page["title"]
                fiche = (
                    f"Document « {doc_name} » lu le {date.today().isoformat()}\n"
                    f"Source : {url}\n"
                    f"Synthèse : {digest}"
                )
                key = hashlib.sha256(url.encode()).hexdigest()[:16]
                try:
                    write_document(fiche, text, url, doc_name)
                    log.info("document_write OK key=%s source=%s chars=%d", key, url, total)
                except Exception:
                    log.exception("document_write ERROR key=%s source=%s", key, url)

            parts = [
                f"[Synthèse {source} « {page['title']} » — {url} "
                f"(caractères {start}-{end} sur {total}) :\n{digest}]"
            ]
            if end < total:
                parts.append(f"{URL_PARTIAL_MARKER} {url} caractères {start}-{end} sur {total}]")
                parts.append(
                    f"[Consigne : dis à Nico que tu as lu les caractères {start} à {end} "
                    f"sur {total}, donne la synthèse ou la réponse à partir de cette "
                    "synthèse, puis propose-lui de lire la suite.]"
                )
            elif is_file:
                parts.append("[Consigne : réponds à partir de cette synthèse.]")
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
