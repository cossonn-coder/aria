# aria/execution/routers/ingestion_router.py
#
# Router d'exécution pour l'opération INGESTION.
#
# ⚠️  DÉSACTIVÉ DU WIRING KERNEL depuis le sprint 3.0 (fix #2).
#
# Pourquoi désactivé :
#   La branche len(message) > 150 → INGESTION dans cognitive_classifier.py
#   court-circuitait silencieusement toute question longue (> 150 chars)
#   sans appel LLM ni réponse cognitive. Le classifier LLM (étape 5) est
#   plus adapté pour distinguer un vrai dump d'information d'une question
#   élaborée. La mémorisation est déjà un effet de bord systématique de
#   LLMExecutionRouter (étape 10).
#
# Ce fichier est conservé pour une future commande /ingest explicite
# (ingestion volontaire de documents longs, déclenchée par l'utilisateur).
# CognitiveOperation.INGESTION reste dans l'enum à cet effet.
#
# Pour réactiver : ajouter l'entrée dans _ROUTING_TABLE de core/kernel.py
# et réimporter IngestionExecutionRouter.

from execution.routers.execution_base import BaseRouter
from memory.mempalace_writer import store_interaction


class IngestionExecutionRouter(BaseRouter):
    """
    Effecteur d'ingestion directe en mémoire.

    Pas de classification, pas d'intent, pas d'agents.
    Stockage brut dans MemPalace sous l'intent "knowledge_ingest".
    """

    def execute(self, payload: dict) -> dict:
        """
        Stocke le contenu brut dans MemPalace.

        payload attendu :
            content  : str (texte à ingérer)
            metadata : dict (optionnel, enrichit les métadonnées mémoire)
        """
        content = payload.get("content", "")
        metadata = payload.get("metadata", {})

        # Normalisation : le contenu peut être str ou dict selon la source
        text = content if isinstance(content, str) else str(content)

        try:
            store_interaction(
                text=text,
                intent_id="knowledge_ingest",
                metadata={
                    "source": metadata.get("source", "ingestion"),
                    "type": "ingestion",
                },
            )
            return {"text": "[INGESTION] Contexte enregistré."}

        except Exception as e:
            print(f"[INGESTION ERROR] {e}")
            from logger import get_logger
            log = get_logger(__name__)
            log.error("[INGESTION ERROR] : %s", e)
            return {"text": "[INGESTION] Échec de l'enregistrement."}