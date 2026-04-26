# aria/cognition/cognitive_engine.py
#
# Cerveau décisionnel du pipeline ARIA.
#
# Responsabilité unique : transformer un Event en CognitiveResult.
# Ce module décide QUOI faire — jamais COMMENT le faire.
#
# Règle stricte : CognitiveEngine ne touche pas MemPalace, les agents,
# ni aucun router d'exécution. Il classifie, c'est tout.
#
# Entrée  : Event (type + content + metadata)
# Sortie  : CognitiveResult (type string + operation enum + short_circuit flag)

from dataclasses import dataclass
from typing import Any, Optional

from core.event import Event, EventType
from cognition.cognitive_classifier import classify_operation, detect_generation_intent_from_caption
from cognition.cognitive_context import CognitiveOperation


@dataclass
class CognitiveResult:
    """
    Résultat de la classification cognitive.

    type          : valeur string de l'opération (ex: "image_generation")
                    → utilisée comme clé de routing dans ExecutionDispatcher
    operation     : enum CognitiveOperation pour les lookups (TOP_K, LLM_ROLE, etc.)
    short_circuit : si True, le kernel retourne `result` directement sans dispatch
    result        : réponse pré-calculée en cas de short_circuit
    """
    type: str
    operation: CognitiveOperation
    short_circuit: bool = False
    result: Optional[Any] = None


class CognitiveEngine:
    """
    Classificateur central d'opérations cognitives.

    Deux chemins de classification :

    1. Heuristique rapide sur EventType (IMAGE → IMAGE_INPUT sans LLM)
       → évite un appel LLM inutile quand l'information est dans le type d'Event

    2. classify_operation() pour les Events TEXT
       → heuristiques + cache MemPalace + fallback LLM

    Le llm_router est optionnel : sans lui, le classifier tombe sur UNKNOWN
    pour les cas ambigus. Utile pour les tests sans API.
    """

    def __init__(self, llm_router=None):
        # llm_router injecté par AriaKernel — None autorisé (tests, mode offline)
        self.llm_router = llm_router

    def classify(self, event: Event) -> CognitiveResult:

        # ── Événements image ─────────────────────────────────────────────────
        if event.type == EventType.IMAGE:
            content = event.content if isinstance(event.content, dict) else {}
            caption = content.get("caption")

            # Caption = demande de génération → IMAGE_GENERATION
            if detect_generation_intent_from_caption(caption):
                return CognitiveResult(
                    type=CognitiveOperation.IMAGE_GENERATION.value,
                    operation=CognitiveOperation.IMAGE_GENERATION,
                )

            # Pas de caption ou caption descriptive → analyse de l'image reçue
            return CognitiveResult(
                type=CognitiveOperation.IMAGE_INPUT.value,
                operation=CognitiveOperation.IMAGE_INPUT,
            )

        # ── Événements texte ─────────────────────────────────────────────────
        if event.type == EventType.TEXT:
            message = event.content if isinstance(event.content, str) else ""
            operation = classify_operation(
                message=message,
                llm_router=self.llm_router,
                metadata=event.metadata or {},
            )
            return CognitiveResult(
                type=operation.value,
                operation=operation,
            )

        # ── Types non supportés ──────────────────────────────────────────────
        return CognitiveResult(
            type=CognitiveOperation.UNKNOWN.value,
            operation=CognitiveOperation.UNKNOWN,
        )