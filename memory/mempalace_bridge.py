# aria/memory/mempalace_bridge.py
#
# Couche de lecture MemPalace — API publique de recall mémoire.
#
# Ce module expose les fonctions de récupération utilisées par
# LLMExecutionRouter et les agents (via AgentContext).
#
# Architecture 3 couches — lecture :
#
#   retrieve_memories()   → recall sémantique dans aria_episodic
#                           (échanges passés, images reçues/générées)
#
#   retrieve_by_intent()  → recall ciblé dans aria_episodic par intent_id
#                           (room = intent_id → mémoire de session)
#
#   retrieve_semantic()   → recall dans aria_semantic
#                           (faits stables : allergie, localisation, prefs)
#
# Règle :
#   Ces fonctions ne décident pas — elles récupèrent et filtrent.
#   La décision sur quoi récupérer (top_k, wing) appartient au router.
#
# Migration :
#   Les entrées existantes sous wing="aria" restent lisibles.
#   On les retrouve via retrieve_memories(wing="aria") si besoin.
#   Les nouvelles entrées sont écrites sous wing="aria_episodic".

from memory.mempalace_store import search


def retrieve_memories(
    query: str,
    wing: str = "aria_episodic",   # défaut mis à jour : couche épisodique
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
    result = search(
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


def retrieve_by_intent(
    query: str,
    intent_id: str,
    n: int = 10,
) -> dict:
    """
    Recall ciblé sur un intent spécifique dans la couche épisodique.

    Tous les souvenirs liés à un intent sont stockés dans
    room=intent_id, wing=aria_episodic. Cette fonction permet
    de récupérer le contexte complet d'un projet ou d'une session.

    Inclut les interactions texte ET les artefacts images liés à l'intent.

    Args:
        query     : texte de la requête pour le ranking sémantique
        intent_id : identifiant de l'intent (filtre sur room)
        n         : nombre maximum de résultats

    Returns:
        dict {"query", "hits", "count"}
    """
    result = search(
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


def retrieve_semantic(
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
        faits = retrieve_semantic("gluten régime alimentaire")
        → [{"text": "Nico est allergique au gluten", ...}]

    Args:
        query   : texte de la requête pour le ranking sémantique
        subject : filtre optionnel sur un sujet (room)
                  None = recherche dans toute la couche sémantique
        n       : nombre maximum de résultats

    Returns:
        dict {"query", "hits", "count"}
    """
    result = search(
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