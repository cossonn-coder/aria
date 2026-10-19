# aria/cognition/cognitive_context.py

from enum import Enum


class CognitiveOperation(Enum):
    FACT_RECALL   = "fact_recall"    # "quelles graines n'ont pas germé"
    MEMORY_QUERY  = "memory_query"   # "rappelle moi ma liste"
    PLANNING      = "planning"       # "fais moi un plan pour..."
    REASONING     = "reasoning"      # "analyse / compare / explique"
    META_MEMORY   = "meta_memory"    # "quels sujets on a abordé"
    PROFILE_QUERY = "profile_query"  # "est ce que je peux manger..."
    # Reserved for explicit ingestion commands. NOT auto-classified — see Sprint 3.0.
    INGESTION     = "ingestion"
    CONFIRMATION  = "confirmation"
    UNKNOWN       = "unknown"
    IMAGE_INPUT = "image_input"
    IMAGE_GENERATION = "image_generation"
    WEB_SEARCH = "web_search"  # délégué en REASONING par web_router (sprint 22)
    URL_READ = "url_read"      # lecture d'URL collée, déléguée en REASONING (sprint 23)
    CHESS_ANALYSIS = "chess_analysis"  # PGN collé, analyse Stockfish (sprint 26)


# Préfixe du marqueur de lecture partielle posé par web_router dans le
# message enrichi (donc dans l'historique) ; relu au tronçon 02 du sprint 23.
URL_PARTIAL_MARKER = "[Lecture partielle :"


# TOP_K mémoire par opération
MEMORY_TOP_K = {
    CognitiveOperation.FACT_RECALL:   3,
    CognitiveOperation.MEMORY_QUERY:  6,
    CognitiveOperation.PLANNING:      4,
    CognitiveOperation.REASONING:     8,
    CognitiveOperation.META_MEMORY:   0,  # ← intents actifs suffisent
    CognitiveOperation.CONFIRMATION:  0,
    CognitiveOperation.PROFILE_QUERY: 3,
    CognitiveOperation.INGESTION:     4,  # defense in depth — non auto-classifié
    CognitiveOperation.UNKNOWN:       4,
}

# LLMRole par opération
from llm.llm_role import LLMRole

LLM_ROLE_MAP = {
    CognitiveOperation.FACT_RECALL:   LLMRole.CHAT,
    CognitiveOperation.MEMORY_QUERY:  LLMRole.CHAT,
    CognitiveOperation.PLANNING:      LLMRole.PLANNING,
    CognitiveOperation.REASONING:     LLMRole.REASONING,
    CognitiveOperation.META_MEMORY:   LLMRole.CHAT,
    CognitiveOperation.PROFILE_QUERY: LLMRole.CHAT,
    CognitiveOperation.CONFIRMATION:  LLMRole.CHAT,
    CognitiveOperation.INGESTION:     LLMRole.CHAT,  # defense in depth — non auto-classifié
    CognitiveOperation.UNKNOWN:       LLMRole.CHAT,
}