# aria/images/image_types.py
#
# Contrats de données pour le pipeline image d'ARIA.
#
# ImageInput  : ce qu'on envoie au modèle de vision (entrée)
# ImageArtifact : ce que le pipeline produit (sortie unifiée)
#
# Règle de conception :
#   Ces dataclasses ne contiennent aucune logique.
#   Elles sont des enveloppes de transport entre les couches.

from dataclasses import dataclass, field
from typing import Optional, Dict
from datetime import datetime, timezone


@dataclass
class ImageInput:
    """
    Représente une image à analyser par un modèle de vision.

    Champs :
        path    : chemin local vers le fichier image (jpg, png, etc.)
        base64  : alternative à path pour les images encodées en mémoire
        source  : origine de l'image ("input" = reçue de l'utilisateur)
        caption : texte accompagnant l'image, fourni par l'utilisateur.
                  Ce champ est crucial pour contextualiser le prompt vision :
                  "c'est la courge plantée en mars" oriente totalement
                  l'analyse du modèle vers ce que l'utilisateur veut savoir,
                  plutôt qu'une description générique de la scène.
    """
    path: Optional[str] = None
    base64: Optional[str] = None
    source: str = "input"
    caption: Optional[str] = None   # texte Telegram accompagnant la photo


@dataclass
class ImageArtifact:
    """
    Résultat unifié du pipeline image — analyse ou génération.

    Produit par ImageRouter.handle_input() et ImageRouter.generate().
    Consommé par ImageExecutionRouter, puis sérialisé en mémoire.

    Champs :
        source    : "input" (reçue) ou "generated" (produite par ARIA)
        path      : chemin local du fichier image
        caption   : description produite par le modèle de vision,
                    ou légende associée à une image générée
        prompt    : prompt utilisé pour la génération (source="generated")
        intent_id : intent cognitif auquel cette image est rattachée
        metadata  : champs libres pour enrichissement futur
        timestamp : horodatage UTC de production de l'artefact
    """
    source: str
    path: Optional[str] = None
    caption: Optional[str] = None
    prompt: Optional[str] = None
    intent_id: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )