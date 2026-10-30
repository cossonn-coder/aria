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
    FILE_READ = "file_read"    # document reçu sur Telegram, lu comme une URL (sprint 42)
    DOC_REREAD = "doc_reread"  # relecture d'un document en mémoire (sprint 43)
    WEB_RESEARCH = "web_research"  # recherche autonome (sprint 45)


# Préfixe du marqueur de lecture partielle posé par web_router dans le
# message enrichi (donc dans l'historique) ; relu au tronçon 02 du sprint 23.
URL_PARTIAL_MARKER = "[Lecture partielle :"

# Début de la phrase par laquelle ARIA propose de relire un document dont la
# fiche est remontée en mémoire (consigne posée par context_builder) ; le
# classifier du tronçon 02 du sprint 43 la reconnaît dans le dernier tour.
REREAD_PROPOSAL = "Veux-tu que je relise « "


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