from mempalace.searcher import search_memories
from config import config


def search(query: str, wing: str = "aria", room: str | None = None, n: int = 5):
    return search_memories(
        query=query,
        palace_path=config.mempalace_path,
        wing=wing,
        room=room,
        n_results=n,
    )