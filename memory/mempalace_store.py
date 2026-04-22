# memory/mempalace_store.py

from mempalace.searcher import search_memories
from config import config


def search(
    query: str,
    wing: str = "aria",
    room: str | None = None,
    n: int = 5,
    user_id: str | None = None,
):
    kwargs = dict(
        query=query,
        palace_path=config.mempalace_path,
        wing=wing,
        room=room,
        n_results=n,
    )

    # ONLY if backend supports it
    if "user_id" in search_memories.__code__.co_varnames:
        kwargs["user_id"] = user_id

    return search_memories(**kwargs)