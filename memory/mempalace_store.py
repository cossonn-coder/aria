# memory/mempalace_store.py

from mempalace.searcher import search_memories
from config import config


def search(
    query: str,
    wing: str,
    room: str | None = None,
    n: int = 5,
):
    kwargs = dict(
        query=query,
        palace_path=config.mempalace_path,
        wing=wing,
        room=room,
        n_results=n,
    )

    return search_memories(**kwargs)