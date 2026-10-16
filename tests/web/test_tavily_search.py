# tests/web/test_tavily_search.py
#
# Parsing de la réponse Tavily (sprint 22, tronçon 01) — httpx.post monkeypatché.

from unittest.mock import MagicMock

import web.tavily_search as tavily
from config import config


def test_search_parses_results(monkeypatch):
    monkeypatch.setattr(config, "tavily_api_key", "test-key")
    response = MagicMock()
    response.json.return_value = {"results": [
        {"title": "T1", "url": "https://u1", "content": "C1", "score": 0.9, "id": "x", "raw_content": None},
    ]}
    monkeypatch.setattr(tavily.httpx, "post", lambda *a, **kw: response)

    assert tavily.search("q") == [{"title": "T1", "url": "https://u1", "content": "C1"}]
