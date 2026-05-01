# aria/logger.py
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger qui hérite du handler configuré sur le root."""
    return logging.getLogger(name)

def configure_root(level: str = "INFO"):
    """
    À appeler une seule fois dans bot.py au démarrage.
    Niveau configurable : DEBUG pour dev, INFO pour prod.
    """
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
        level=getattr(logging, level.upper(), logging.INFO),
        force=True,
    )
    # Réduire le bruit des libs externes
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("sentence_transformers").setLevel(logging.WARNING)