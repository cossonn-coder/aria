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
#   from memory.mempalace_store import search
#   bridge = MempalaceBridge(store=search)
#
# Instanciation (tests) :
#   bridge = MempalaceBridge(store=fake_search)


class MempalaceBridge:
    """
    Adapter mémoire — couche de lecture MemPalace injectable et testable.

    Args:
        store : callable avec signature search(query, wing, room, n) → dict.
                En production : mempalace_store.search.
                En test       : tout callable compatible.
    """

    def __init__(self, store):
        self._store = store

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
    ) -> dict:
        """
        Recall sémantique dans la mémoire épisodique.

        Recherche par similarité vectorielle dans wing (défaut: aria_episodic).
        Filtre les résultats trop distants (distance > 0.8) et les rooms
        génériques ("general") qui polluent le contexte.

        Args:
            query       : texte de la requête (message utilisateur)
            wing        : wing MemPalace cible. Défaut "aria_episodic".
                          Passer "aria" pour lire les anciennes entrées.
            room        : filtre optionnel sur un room spécifique (intent_id)
            n           : nombre maximum de résultats souhaités
            type_filter : liste de types à garder ("interaction", "image_input", etc.)
                          None = pas de filtre

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
            # Seuil de distance : au-delà de 0.8 le souvenir n'est plus pertinent
            and h.get("distance", 1.0) < 0.8
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