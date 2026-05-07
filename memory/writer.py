# aria/memory/writer.py
#
# Couche d'écriture MemPalace — API explicite, wing/room non overridables.
#
# Remplaçant architectural de mempalace_writer.py (cohabitation en strangler
# pattern jusqu'à migration complète des callers, sprint 4).
#
# Garantie centrale :
#   Les champs structurels wing, room, type sont posés APRÈS le spread
#   de `extra`. Toute tentative de les overrider via extra est silencieusement
#   écrasée — le document atterrit toujours dans la bonne couche.
#   C'est le mécanisme anti-régression du bug W4 (sprint 3.1 / dette #11).
#
# Schéma ChromaDB obligatoire :
#   Métadonnées : str, int, float, bool, None uniquement.
#   Les datetime sont convertis en isoformat() avant stockage.

import hashlib
import json
import time
from datetime import datetime, timezone
from uuid import uuid4

from config import config
from images.image_types import ImageArtifact
from logger import get_logger
from mempalace.palace import get_collection

log = get_logger(__name__)


# ── Schéma ────────────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {"wing", "room", "type"}


def _validate(meta: dict):
    missing = REQUIRED_FIELDS - set(meta.keys())
    if missing:
        raise ValueError(f"MemPalace schema violation: missing fields {missing}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _idempotent_doc_id(text: str, intent_id: str) -> str:
    """
    Doc_id stable sur une fenêtre de 60 secondes.
    Deux appels identiques (même text, même intent_id) dans la même minute
    produisent le même ID → upsert idempotent → pas de doublon.
    """
    bucket = int(time.time()) // 60
    h = hashlib.sha256(f"{intent_id}|{text}|{bucket}".encode()).hexdigest()[:16]
    return f"interaction_{intent_id}_{h}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Écriture épisodique (texte) ───────────────────────────────────────────────

def write_interaction(
    text: str,
    intent_id: str,
    *,
    intent_name: str | None = None,
    source: str = "conversation",
    extra: dict | None = None,
) -> None:
    """
    Stocke un échange conversationnel dans aria_episodic.

    wing="aria_episodic" et room=intent_id sont structurels et non overridables.
    `extra` peut enrichir les métadonnées mais ne peut pas modifier wing/room/type.
    """
    col = get_collection(config.mempalace_path)
    doc_id = _idempotent_doc_id(text, intent_id)

    meta = {
        **(extra or {}),
        "wing": "aria_episodic",
        "room": intent_id,
        "type": "interaction",
        "timestamp": _now_iso(),
        "intent": intent_id,
        "source": source,
    }
    if intent_name is not None:
        meta["intent_name"] = intent_name

    _validate(meta)
    col.upsert(documents=[text], ids=[doc_id], metadatas=[meta])


# ── Écriture épisodique (image) ───────────────────────────────────────────────

def write_image_artifact(
    artifact: ImageArtifact,
    *,
    intent_id: str | None = None,
) -> None:
    """
    Stocke un artefact image dans aria_episodic.

    IMAGE_INPUT  : indexe la caption vision + caption utilisateur.
    IMAGE_GENERATED : indexe le prompt de génération.
    """
    col = get_collection(config.mempalace_path)

    if artifact.source == "generated":
        indexed_text = artifact.prompt or artifact.caption or ""
        doc_type = "image_generated"
    else:
        parts = [p for p in [artifact.caption, artifact.metadata.get("user_caption")] if p]
        indexed_text = " | ".join(parts) if parts else ""
        doc_type = "image_input"

    if not indexed_text:
        log.warning("write_image_artifact skipped — no indexable text for %s", artifact.path)
        return

    room = intent_id or "general"
    doc_id = f"{doc_type}_{uuid4().hex[:8]}"

    meta = {
        "wing": "aria_episodic",
        "room": room,
        "type": doc_type,
        "timestamp": artifact.timestamp.isoformat(),
        "path": artifact.path or "",
        "prompt": artifact.prompt or "",
        "intent": intent_id or "",
        "source": artifact.source,
    }
    _validate(meta)
    col.upsert(documents=[indexed_text], ids=[doc_id], metadatas=[meta])


# ── Écriture sémantique (faits stables) ──────────────────────────────────────

def write_semantic_fact(
    fact: str,
    subject: str,
    *,
    source: str = "conversation",
    extra: dict | None = None,
) -> None:
    """
    Stocke un fait stable sur l'utilisateur dans aria_semantic.

    wing="aria_semantic" et room=subject sont structurels et non overridables.
    """
    col = get_collection(config.mempalace_path)
    doc_id = f"semantic_{subject}_{uuid4().hex[:8]}"

    meta = {
        **(extra or {}),
        "wing": "aria_semantic",
        "room": subject,
        "type": "semantic_fact",
        "timestamp": _now_iso(),
        "source": source,
    }
    _validate(meta)
    col.upsert(documents=[fact], ids=[doc_id], metadatas=[meta])


# ── Écriture cache classifier ─────────────────────────────────────────────────

def write_classifier_cache(
    message: str,
    operation: str,
    *,
    confirmed: bool = False,
) -> None:
    """
    Stocke un mapping message→operation dans le cache classifier.

    Schéma post-T2 sprint 5 (fix dette #20) :
      - document indexé : message brut. L'embedding est aligné avec celui
        que produit _search_cache() (qui query=message brut). Avant ce fix,
        le document était json.dumps({"message", "operation"}) → cosine
        similarity 0.47-0.60 sur des messages identiques, jamais de hit.
      - room : operation. Récupérable depuis hits[].room sans dépendre du
        wrapper search() pour propager metadata.operation (cf.
        docs/sprint5/audit_cache_classifier.md §4 et spot-check T2).

    operation doit être str (.value côté caller). wing/room/type sont
    structurels et non overridables.
    """
    if not isinstance(operation, str):
        raise TypeError(
            f"operation must be str (got {type(operation).__name__}). "
            f"Pass operation.value if you have a CognitiveOperation enum."
        )
    col = get_collection(config.mempalace_path)
    doc_id = _idempotent_doc_id(message, "classifier_cache")

    meta = {
        "wing": "aria_classifier",
        "room": operation,
        "type": "classifier_cache",
        "timestamp": _now_iso(),
        "confirmed": confirmed,
    }
    _validate(meta)
    col.upsert(documents=[message], ids=[doc_id], metadatas=[meta])
