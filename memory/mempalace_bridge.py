# aria/memory/mempalace_bridge.py
#
# Adapter mémoire d'ARIA — interface unique vers MemPalace (ChromaDB).
#
# Architecture :
#
#   MempalaceBridge est l'unique point d'accès en lecture à la mémoire vectorielle.
#   Il reçoit un store en injection de dépendance et expose trois méthodes
#   correspondant aux trois couches mémoire d'ARIA :
#
#       retrieve_memories()   → couche épisodique (aria_episodic)
#                               échanges passés, images reçues/générées
#
#       retrieve_by_intent()  → recall ciblé dans aria_episodic par intent_id
#                               mémoire de session d'un projet
#
#       retrieve_semantic()   → couche sémantique (aria_semantic)
#                               faits stables : allergie, localisation, préférences
#
# Responsabilités :
#   - Filtrage qualité (distance, room générique)
#   - Filtre optionnel par type de document
#   - Isolation du reste du code de tout import ChromaDB direct
#
# Règles :
#   - Ce module ne décide pas — il récupère et filtre.
#   - La décision sur quoi récupérer (top_k, wing) appartient au router appelant.
#   - Aucun agent, aucun router n'importe mempalace_store directement.
#
# Instanciation (production) :
#   from memory.mempalace_store import search, get_by_metadata
#   bridge = MempalaceBridge(store=search, get_by_metadata=get_by_metadata)
#
# Instanciation (tests) :
#   bridge = MempalaceBridge(store=fake_search)
#   bridge = MempalaceBridge(store=fake_search, get_by_metadata=fake_get)


class MempalaceBridge:
    """
    Adapter mémoire — couche de lecture MemPalace injectable et testable.

    Args:
        store           : callable avec signature search(query, wing, room, n) → dict.
                          En production : mempalace_store.search.
                          En test       : tout callable compatible.
        get_by_metadata : callable optionnel avec signature
                          get_by_metadata(palace_path, where, include=None) → dict
                          natif ChromaDB {ids, documents, metadatas}.
                          Requis uniquement pour load_conversation_history.
                          Si None, l'appel à load_conversation_history lève
                          RuntimeError.
    """

    def __init__(self, store, get_by_metadata=None):
        self._store = store
        self._get_by_metadata = get_by_metadata

    # =========================================================
    # RECALL ÉPISODIQUE
    # =========================================================

    def retrieve_memories(
        self,
        query: str,
        wing: str = "aria_episodic",
        room: str | None = None,
        n: int = 5,
        type_filter: list[str] | None = None,
        max_distance: float | None = 0.8,
    ) -> dict:
        """
        Recall sémantique dans la mémoire épisodique.

        Recherche par similarité vectorielle dans wing (défaut: aria_episodic).
        Filtre les résultats trop distants et les rooms génériques ("general")
        qui polluent le contexte.

        Args:
            query        : texte de la requête (message utilisateur)
            wing         : wing MemPalace cible. Défaut "aria_episodic".
                           Passer "aria" pour lire les anciennes entrées.
            room         : filtre optionnel sur un room spécifique (intent_id)
            n            : nombre maximum de résultats souhaités
            type_filter  : liste de types à garder ("interaction", "image_input", etc.)
                           None = pas de filtre
            max_distance : seuil de distance maximal (défaut 0.8).
                           None = désactive le filtre distance — le caller
                           applique son propre seuil métier (ex : cache
                           classifier avec similarity ≥ 0.92).

        Returns:
            dict {"query", "hits", "count"}
            hits : liste de documents avec text, distance, métadonnées
        """
        if n <= 0:
            return {"query": query, "hits": [], "count": 0}

        # On demande le double pour absorber les filtrages à venir
        result = self._store(
            query=query,
            wing=wing,
            room=room,
            n=n * 2,
        )

        hits = [
            h for h in result.get("results", [])
            # Exclut la room "general" — trop générique, nuit à la pertinence
            if h.get("room", "") != "general"
            # Seuil de distance paramétrable — None = pas de filtre distance
            and (max_distance is None
                 or h.get("distance", 1.0) < max_distance)
        ][:n]

        # Filtre optionnel par type de document
        if type_filter:
            hits = [h for h in hits if h.get("type") in type_filter]

        return {
            "query": query,
            "hits": hits,
            "count": len(hits),
        }

    # =========================================================
    # RECALL PAR INTENT
    # =========================================================

    def retrieve_by_intent(
        self,
        query: str,
        intent_id: str,
        n: int = 10,
    ) -> dict:
        """
        Recall ciblé sur un intent spécifique dans la couche épisodique.

        Tous les souvenirs liés à un intent sont stockés dans
        room=intent_id, wing=aria_episodic. Cette méthode permet
        de récupérer le contexte complet d'un projet ou d'une session.

        Inclut les interactions texte ET les artefacts images liés à l'intent.

        Args:
            query     : texte de la requête pour le ranking sémantique
            intent_id : identifiant de l'intent (filtre sur room)
            n         : nombre maximum de résultats

        Returns:
            dict {"query", "hits", "count"}
        """
        result = self._store(
            query=query,
            wing="aria_episodic",
            room=intent_id,
            n=n,
        )

        return {
            "query": query,
            "hits": result.get("results", []),
            "count": len(result.get("results", [])),
        }

    # =========================================================
    # RECALL SÉMANTIQUE
    # =========================================================

    def retrieve_semantic(
        self,
        query: str,
        subject: str | None = None,
        n: int = 5,
    ) -> dict:
        """
        Recall dans la couche sémantique — faits stables sur l'utilisateur.

        Utilisé pour injecter des faits durables dans le contexte agent :
        allergies, localisation, préférences, habitudes.
        Ces faits sont transversaux aux intents et aux sessions.

        Exemple d'usage dans le pipeline :
            faits = bridge.retrieve_semantic("gluten régime alimentaire")
            → {"hits": [{"text": "Nico est allergique au gluten", ...}], ...}

        Args:
            query   : texte de la requête pour le ranking sémantique
            subject : filtre optionnel sur un sujet (room)
                      None = recherche dans toute la couche sémantique
            n       : nombre maximum de résultats

        Returns:
            dict {"query", "hits", "count"}
        """
        result = self._store(
            query=query,
            wing="aria_semantic",
            room=subject,   # None = pas de filtre sur le room
            n=n,
        )

        return {
            "query": query,
            "hits": result.get("results", []),
            "count": len(result.get("results", [])),
        }

    # =========================================================
    # LECTURE CONVERSATIONNELLE (chronologique, pas de query vectorielle)
    # =========================================================

    def load_conversation_history(
        self,
        conversation_key: str,
        n: int = 10,
    ) -> list[dict]:
        """
        Restitution chronologique (oldest → newest) des n derniers tours
        d'une conversation. Format prêt à être passé en `messages` au
        provider LLM au sprint 16.

        Lecture non-vectorielle : filtre metadata pur sur wing/room,
        puis tri Python sur metadata.timestamp. ChromaDB ne trie pas
        nativement sur .get() — c'est délibéré côté caller (cf. audit
        sprint 15 §5.3).

        Args:
            conversation_key : clé d'indexation de la conversation
                               (chat_id Telegram stringifié côté caller).
            n                : nombre maximum de tours retournés
                               (les plus récents). n<=0 → liste vide.

        Returns:
            liste de {"role": str, "content": str, "timestamp": str}
            triée par timestamp croissant. Liste vide si conversation
            inconnue ou n<=0.

        Raises:
            RuntimeError : si le bridge a été construit sans get_by_metadata
                           (injection optionnelle au constructeur).
        """
        if self._get_by_metadata is None:
            raise RuntimeError(
                "get_by_metadata callable required for conversation history; "
                "inject at construction"
            )

        if n <= 0:
            return []

        from config import config as _config

        where = {"$and": [
            {"wing": "aria_conversation"},
            {"room": conversation_key},
        ]}

        result = self._get_by_metadata(_config.mempalace_path, where) or {}
        docs = result.get("documents") or []
        metas = result.get("metadatas") or []

        turns = [
            {
                "role": (meta or {}).get("role", ""),
                "content": doc or "",
                "timestamp": (meta or {}).get("timestamp", ""),
            }
            for doc, meta in zip(docs, metas)
        ]
        turns.sort(key=lambda t: t["timestamp"])
        return turns[-n:]