# aria/execution/routers/ingestion_router.py
#
# Router d'exécution pour l'opération INGESTION.
#
# L'ingestion est une opération terminale simple :
# l'utilisateur fournit de l'information brute (liste, catalogue,
# contexte long) sans poser de question.
#
# Ce router stocke directement dans MemPalace sans pipeline cognitif,
# sans intent engine, sans agents. La donnée est enregistrée telle quelle.
#
# Cas typiques :
#   - catalogue d'huiles essentielles
#   - liste de courses
#   - copie d'un document texte
#   - contexte de projet à mémoriser

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