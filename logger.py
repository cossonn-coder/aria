# aria/logger.py
import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """
    Retourne un logger configuré pour le module donné.

    Usage :
        from logger import get_logger
        log = get_logger(__name__)
        log.info("message")
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
            datefmt="%H:%M:%S",
        ))
        logger.addHandler(handler)

    return logger


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