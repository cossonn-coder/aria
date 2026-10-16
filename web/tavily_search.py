# aria/web/tavily_search.py
#
# Recherche web via l'API Tavily (sprint 22).
#
# Ce module est le SEUL à connaître le fournisseur de recherche :
# changer de moteur = changer ce fichier, sans toucher au web_router.
#
# Contrat : search(query) → [{"title", "url", "content"}]. Toute erreur
# (clé absente, HTTP, réseau) remonte en exception ; le router la traite
# comme un échec de recherche.

import httpx

from config import config

_TAVILY_URL = "https://api.tavily.com/search"


def search(query: str, max_results: int = 5) -> list[dict]:
    """Interroge Tavily et retourne les résultats sous forme normalisée."""
    if not config.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY absente")

    response = httpx.post(
        _TAVILY_URL,
        headers={"Authorization": f"Bearer {config.tavily_api_key}"},
        json={"query": query, "max_results": max_results, "search_depth": "basic"},
        timeout=15.0,
    )
    response.raise_for_status()
    data = response.json()

    return [
        {"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
        for r in data.get("results", [])
    ]
