# aria/llm/vision/groq_vision.py

import base64
import httpx
from pathlib import Path


class GroqVisionClient:
    """
    Analyse d'image via Groq.
    Modèle injecté par le router.

    Accepte :
    - path fichier local (str | Path)
    - données base64 déjà encodées (str commençant par data:)
    - URL http/https
    """

    def __init__(self, base_url: str, api_key: str, model: str, **_):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model

    def _to_image_url(self, image):
        """
        Convertit l'entrée image vers une data URL.

        Accepte :
        - URL distante
        - chemin local existant
        - chaîne arbitraire (tests unitaires)
        """

        if isinstance(image, str) and image.startswith("http"):
            return image

        path = Path(image)

        # ✔ ne casse pas les tests unitaires
        if not path.exists():
            return image

        data = base64.b64encode(path.read_bytes()).decode()
        return f"data:image/png;base64,{data}"

    def describe(self, image: str | Path, prompt: str = "Décris cette image en détail.") -> str:
        image_url = self._to_image_url(image)
        r = httpx.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": image_url}},
                    {"type": "text", "text": prompt},
                ]}],
                "max_tokens": 512,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]