# aria/llm/image_gen/pollinations_client.py
#
# Client de génération d'image via Pollinations.ai.
#
# Aucune clé API requise — génération gratuite par HTTP GET.
# Le prompt est encodé dans le path de l'URL via urllib.parse.quote.
#
# Problème corrigé :
#   L'ancien code utilisait httpx.URL(prompt) pour encoder le prompt.
#   httpx.URL() est conçu pour parser des URLs complètes, pas pour
#   encoder un segment de path — il laissait passer les caractères
#   non-ASCII et les sauts de ligne (\n), ce qui provoquait :
#   "Invalid non-printable ASCII character in URL, '\n' at position 11"
#   dès que le prompt était enrichi par _inject_context().
#
#   Fix : urllib.parse.quote(prompt, safe="") encode tous les caractères
#   spéciaux incluant \n, \t, espaces, accents — conforme RFC 3986.

import hashlib
import httpx
from pathlib import Path
from urllib.parse import quote


class PollinationsClient:
    """
    Génère une image depuis un prompt texte via Pollinations.ai.

    Télécharge l'image générée et retourne son chemin local.
    Aucune clé API requise.

    Args:
        base_url   : URL de base de l'API Pollinations (ex: "https://image.pollinations.ai")
        output_dir : répertoire local où sauvegarder les images générées
    """

    def __init__(self, base_url: str, output_dir: str, **_):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        prompt: str,
        width: int = 1024,
        height: int = 1024,
    ) -> "GenerationResult":
        """
        Génère une image à partir d'un prompt texte.

        Le prompt est encodé via urllib.parse.quote avant d'être inséré
        dans le path de l'URL — cela garantit que les caractères spéciaux
        (\n, espaces, accents, guillemets) ne corrompent pas la requête HTTP.

        Args:
            prompt : texte décrivant l'image à générer (peut être multi-lignes)
            width  : largeur en pixels (défaut 1024)
            height : hauteur en pixels (défaut 1024)

        Returns:
            GenerationResult avec path local et caption
        """
        # Encodage strict du prompt : safe="" encode TOUT sauf les lettres et chiffres.
        # Indispensable quand le prompt contient des \n issus de _inject_context().
        encoded_prompt = quote(prompt, safe="")
        url = f"{self.base_url}/prompt/{encoded_prompt}"

        params = {"width": width, "height": height, "nologo": "true"}

        r = httpx.get(url, params=params, timeout=60, follow_redirects=True)
        r.raise_for_status()

        # Nom de fichier dérivé du prompt — stable pour un même prompt
        slug     = hashlib.md5(prompt.encode()).hexdigest()[:12]
        filename = self.output_dir / f"aria_{slug}.png"
        filename.write_bytes(r.content)

        return GenerationResult(
            path=str(filename),
            caption=f"[generated: {prompt[:60]}]",
        )


class GenerationResult:
    """Résultat d'une génération image — path local + caption courte."""

    def __init__(self, path: str, caption: str):
        self.path    = path
        self.caption = caption