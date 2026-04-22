#aria/memory/mempalace_bridge.py

from memory.mempalace_store import search


def retrieve_memories(query: str, wing: str = "aria", room: str | None = None, n: int = 5):

    result = search(
        query=query,
        wing=wing,
        room=room,
        n=n * 2,  # over-fetch pour filtrer ensuite
    )

    hits = [
        h for h in result.get("results", [])
        if h.get("room", "") != "general"       # exclure contenu étranger
        and h.get("distance", 1.0) < 0.8        # exclure hits trop distants
    ][:n]

    return {
        "query": query,
        "hits": hits,
        "count": len(hits),
    }


def retrieve_by_intent(query: str, intent_id: str, n: int = 10):

    result = search(
        query=query,
        wing="aria",
        room=intent_id,
        n=n,
    )

    return {
        "query": query,
        "hits": result.get("results", []),
        "count": len(result.get("results", [])),
    }