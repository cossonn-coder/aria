# aria/memory/mempalace_writer.py
#
# Couche d'écriture MemPalace — point d'entrée unique pour toute persistence.
#
# Architecture mémoire 3 couches :
#
#   aria_episodic  → événements conversationnels dans le temps
#                    (échanges texte, images reçues, images générées)
#                    Indexé par intent_id (room) pour le recall ciblé.
#
#   aria_semantic  → faits stables sur l'utilisateur
#                    (allergie gluten, localisation, préférences, projets)
#                    Écrit explicitement, pas déduit automatiquement.
#                    Durée de vie longue — ne décroît pas.
#
#   aria_intentual → réservé aux intents sérialisés (sprint 1.2)
#                    Non utilisé ici.
#
# Règle fondamentale :
#   Une seule fonction par type d'écriture.
#   Aucun agent, aucun router n'écrit en ChromaDB directement.
#   Tout passe par ce module.
#
# Schéma ChromaDB obligatoire :
#   Métadonnées : str, int, float, bool, None uniquement.
#   Les datetime sont convertis en isoformat() avant stockage.

import hashlib
import time
from datetime import datetime, timezone
from uuid import uuid4

from config import config
from mempalace.palace import get_collection
from images.image_types import ImageArtifact


# ── Idempotence ───────────────────────────────────────────────────────────────

def _idempotent_doc_id(text: str, intent_id: str) -> str:
    """
    Doc_id stable sur une fenêtre de 60 secondes.
    Deux appels identiques (même text, même intent_id) dans la même minute
    produisent le même ID → upsert idempotent → pas de doublon.
    Hors fenêtre, ID différent → répétitions légitimes préservées.
    """
    bucket = int(time.time()) // 60
    h = hashlib.sha256(f"{intent_id}|{text}|{bucket}".encode()).hexdigest()[:16]
    return f"interaction_{intent_id}_{h}"


# ── Champs obligatoires du schéma ─────────────────────────────────────────────
#
# Toute entrée MemPalace doit porter ces champs pour être requêtable
# par wing, room, et type dans mempalace_bridge.

REQUIRED_FIELDS = {"wing", "room", "type"}


def _validate(meta: dict):
    """Vérifie que les champs obligatoires du schéma sont présents."""
    missing = REQUIRED_FIELDS - set(meta.keys())
    if missing:
        raise ValueError(f"MemPalace schema violation: missing fields {missing}")


def _now_iso() -> str:
    """Horodatage UTC en isoformat — format imposé par ChromaDB."""
    return datetime.now(timezone.utc).isoformat()


# ── Écriture épisodique (texte) ───────────────────────────────────────────────

def store_interaction(
    text: str,
    intent_id: str,
    metadata: dict | None = None,
):
    """
    Stocke un échange conversationnel dans la couche épisodique.

    La couche aria_episodic enregistre tout ce qui s'est passé dans
    le temps : les échanges USER/ARIA, liés à un intent actif.
    C'est la mémoire autobiographique d'ARIA.

    Args:
        text      : contenu de l'échange ("USER:\n...\nARIA:\n...")
        intent_id : identifiant de l'intent actif au moment de l'échange.
                    Sert de room — permet le recall ciblé par projet.
        metadata  : champs supplémentaires libres (intent_name, source, etc.)
    """
    col = get_collection(config.mempalace_path)
    doc_id = _idempotent_doc_id(text, intent_id)

    meta = {
        "wing": "aria_episodic",   # couche épisodique — événements temporels
        "room": intent_id,          # room = intent → recall ciblé par projet
        "intent": intent_id,
        "type": "interaction",
        "timestamp": _now_iso(),
        **(metadata or {}),
    }
    _validate(meta)

    col.upsert(
        documents=[text],
        ids=[doc_id],
        metadatas=[meta],
    )


# ── Écriture épisodique (image) ───────────────────────────────────────────────

def store_image_artifact(
    artifact: ImageArtifact,
    intent_id: str | None = None,
):
    """
    Stocke un artefact image dans la couche épisodique.

    Que ce soit une image reçue (IMAGE_INPUT) ou une image générée
    (IMAGE_GENERATION), les deux sont des événements cognitifs :
    ils ont eu lieu à un moment, dans un contexte, liés à un intent.

    Ce qui est indexé dans ChromaDB :
        - Pour IMAGE_INPUT  : la caption produite par le modèle de vision
          + la caption originale de l'utilisateur si présente.
          C'est la description de l'image qui sera requêtable sémantiquement.
        - Pour IMAGE_GENERATED : le prompt de génération.
          "dessine un plan de mon jardin" doit être retrouvable plus tard.

    Args:
        artifact  : ImageArtifact produit par ImageRouter
        intent_id : intent actif — None si aucun intent résolu
    """
    col = get_collection(config.mempalace_path)

    # Choix du texte indexé selon la source de l'image.
    # Pour la recherche vectorielle, on indexe ce qui a du sens sémantique :
    #   - une image reçue → sa description (caption du modèle vision)
    #   - une image générée → le prompt qui l'a produite
    if artifact.source == "generated":
        indexed_text = artifact.prompt or artifact.caption or ""
        doc_type = "image_generated"
    else:
        # Combine caption vision + caption utilisateur pour un index riche
        parts = [p for p in [artifact.caption, artifact.metadata.get("user_caption")] if p]
        indexed_text = " | ".join(parts) if parts else ""
        doc_type = "image_input"

    if not indexed_text:
        # Rien à indexer — on ne stocke pas une entrée vide
        print(f"[MEMORY] store_image_artifact skipped — no indexable text for {artifact.path}")
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

    col.upsert(
        documents=[indexed_text],
        ids=[doc_id],
        metadatas=[meta],
    )


# ── Écriture sémantique (faits stables) ──────────────────────────────────────

def store_semantic_fact(
    fact: str,
    subject: str,
    source: str = "conversation",
    metadata: dict | None = None,
):
    """
    Stocke un fait stable sur l'utilisateur dans la couche sémantique.

    La couche aria_semantic contient ce qu'ARIA sait de façon durable
    sur l'utilisateur : ses contraintes alimentaires, sa localisation,
    ses projets récurrents, ses préférences. Ces faits ne sont pas liés
    à un intent particulier — ils sont transversaux à toutes les sessions.

    Contrairement à aria_episodic (événements), aria_semantic stocke
    des vérités qui restent vraies dans le temps.

    Exemples :
        store_semantic_fact("Nico est allergique au gluten", subject="santé")
        store_semantic_fact("Nico habite à Seyssinet-Pariset", subject="localisation")
        store_semantic_fact("Nico pratique l'escalade", subject="activités")

    Args:
        fact    : énoncé du fait en langage naturel
        subject : catégorie du fait (santé, localisation, activités, etc.)
                  Sert de room pour le recall ciblé par domaine.
        source  : origine du fait ("conversation", "user_input", "inferred")
        metadata: champs libres supplémentaires
    """
    col = get_collection(config.mempalace_path)
    doc_id = f"semantic_{subject}_{uuid4().hex[:8]}"

    meta = {
        "wing": "aria_semantic",   # couche sémantique — faits stables
        "room": subject,            # room = sujet → recall par domaine
        "type": "semantic_fact",
        "timestamp": _now_iso(),
        "source": source,
        **(metadata or {}),
    }
    _validate(meta)

    col.upsert(
        documents=[fact],
        ids=[doc_id],
        metadatas=[meta],
    )