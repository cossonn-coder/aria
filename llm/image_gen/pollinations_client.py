# aria/llm/image_gen/pollinations_client.py

import httpx
import hashlib
from pathlib import Path


class PollinationsClient:
    """
    Génération d'image via Pollinations.ai.
    télécharge une image générée et retourne son chemin local.

    Aucune clé API requise.
    Retourne le path local du fichier PNG téléchargé.
    """

    def __init__(self, base_url, output_dir, **_):
        self.base_url = base_url
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str, width: int = 1024, height: int = 1024) -> "GenerationResult":
        url = f"{self.base_url}/prompt/{httpx.URL(prompt)}"
        params = {"width": width, "height": height, "nologo": "true"}

        r = httpx.get(url, params=params, timeout=60, follow_redirects=True)
        r.raise_for_status()

        slug = hashlib.md5(prompt.encode()).hexdigest()[:12]
        filename = self.output_dir / f"aria_{slug}.png"
        filename.write_bytes(r.content)

        return GenerationResult(
            path=str(filename),
            caption=f"[generated: {prompt[:60]}]",
        )


class GenerationResult:
    def __init__(self, path: str, caption: str):
        self.path = path
        self.caption = caption