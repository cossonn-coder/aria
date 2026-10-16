# aria/llm/image_gen/pollinations_client.py
#
# Client de génération d'image via Pollinations.ai.
#
# Deux modes, un même client (sprint 24) :
#   - avec modèle (entrée « pollinations_key » de la table) :
#     GET gen.pollinations.ai/image/<prompt> + Authorization: Bearer <clé>,
#     sans filigrane. Sans clé, ce mode échoue pour laisser jouer le secours.
#   - sans modèle (entrée « pollinations_anon ») : endpoint anonyme
#     {base_url}/prompt/<prompt>, filigrane, 1 image / 45 s.
#
# Le prompt est encodé dans le path de l'URL via urllib.parse.quote(safe="")
# (RFC 3986) : httpx.URL() laissait passer \n et caractères non-ASCII.

import hashlib
import httpx
from pathlib import Path
from urllib.parse import quote


class PollinationsClient:
    """
    Génère une image depuis un prompt texte via Pollinations.ai.

    Télécharge l'image générée et retourne son chemin local.

    Args:
        base_url   : URL de base de l'API Pollinations (ex: "https://image.pollinations.ai")
        output_dir : répertoire local où sauvegarder les images générées
        api_key    : clé Pollinations (mode à clé uniquement)
        model      : modèle Pollinations ; sa présence active le mode à clé
    """

    def __init__(self, base_url: str, output_dir: str, api_key=None, model=None, **_):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
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
        encoded_prompt = quote(prompt, safe="")

        if self.model:
            # Mode à clé : sans clé, on échoue sans appeler l'endpoint,
            # le dispatcher passe alors au secours anonyme.
            if not self.api_key:
                raise RuntimeError("POLLINATION_API_KEY absente")
            url = f"{self.base_url}/image/{encoded_prompt}"
            params = {"model": self.model, "width": width, "height": height}
            headers = {"Authorization": f"Bearer {self.api_key}"}
        else:
            url = f"{self.base_url}/prompt/{encoded_prompt}"
            params = {"width": width, "height": height, "nologo": "true"}
            headers = {}

        r = httpx.get(url, params=params, headers=headers, timeout=60, follow_redirects=True)
        r.raise_for_status()

        # Pollinations peut renvoyer du JSON (erreur, quota) : un 200 non-image
        # écrit dans un .png donnerait un fichier corrompu. On lève pour que
        # le dispatcher passe au fournisseur suivant.
        content_type = r.headers.get("content-type", "")
        if "image" not in content_type:
            raise RuntimeError(
                f"Pollinations a retourné un contenu non-image "
                f"(content-type: {content_type!r}) : {r.text[:200]}"
            )

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