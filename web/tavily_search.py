# aria/web/tavily_search.py
#
# Recherche web via l'API Tavily (sprint 22).
#
# Ce module est le SEUL à connaître le fournisseur de recherche :
# changer de moteur = changer ce fichier, sans toucher au web_router.
#
# Contrat : search(query) → [{"title", "url", "content"}] ;
# extract(url) → {"title", "url", "content"} (sprint 23). Toute erreur
# (clé absente, HTTP, réseau, page injoignable) remonte en exception ; le
# router la traite comme un échec.

import httpx

from config import config

_TAVILY_URL = "https://api.tavily.com/search"
_TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"


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


def extract(url: str) -> dict:
    """Récupère le texte complet d'une page via Tavily /extract."""
    if not config.tavily_api_key:
        raise RuntimeError("TAVILY_API_KEY absente")

    response = httpx.post(
        _TAVILY_EXTRACT_URL,
        headers={"Authorization": f"Bearer {config.tavily_api_key}"},
        json={"urls": [url], "format": "text"},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()

    # Page injoignable : HTTP 200 mais `results` vide, l'URL est dans `failed_results`.
    results = data.get("results", [])
    if not results:
        raise RuntimeError(f"extraction impossible : {data.get('failed_results')}")

    r = results[0]
    return {"title": r.get("title") or "", "url": r.get("url", url), "content": r.get("raw_content") or ""}
