# aria/llm/vision/groq_vision.py

import base64
import mimetypes
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

    def __init__(self, base_url: str, api_key: str, model: str, extra: dict | None = None, **_):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        # Champs propres au fournisseur fusionnés dans le payload
        # (ex. DeepSeek : {"thinking": {"type": "disabled"}}).
        self.extra = extra

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

        # Type MIME déduit de l'extension (Telegram envoie des .jpg).
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        data = base64.b64encode(path.read_bytes()).decode()
        return f"data:{mime};base64,{data}"

    def describe(self, image: str | Path, prompt: str = "Décris cette image en détail.") -> str:
        image_url = self._to_image_url(image)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": image_url}},
                {"type": "text", "text": prompt},
            ]}],
            "max_tokens": 1024,
        }
        payload.update(self.extra or {})
        r = httpx.post(
            self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        # Réponse vide = échec : le router passe au fournisseur suivant.
        if not content:
            raise ValueError(f"Réponse vision vide ({self.model})")
        return content