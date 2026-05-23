# memory/mempalace_store.py

from mempalace.palace import get_collection
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


def get_by_metadata(
    palace_path: str,
    where: dict,
    include: list[str] | None = None,
) -> dict:
    """Lecture ChromaDB par filtre metadata uniquement (pas d'embedding query).

    Wrapper mince autour de col.get(where=...). Retourne le dict natif
    ChromaDB {ids, documents, metadatas}. Caller responsable du tri et
    de la mise en forme.

    Utilisé par MempalaceBridge.load_conversation_history pour récupérer
    les tours d'une conversation par filtre wing/room.
    """
    # Note : include est une liste car c'est l'API native ChromaDB.
    if include is None:
        include = ["documents", "metadatas"]
    col = get_collection(palace_path, create=False)
    return col.get(where=where, include=include)