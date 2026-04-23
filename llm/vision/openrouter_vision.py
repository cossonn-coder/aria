# aria/llm/vision/openrouter_vision.py

import base64
import httpx
from pathlib import Path


class OpenRouterVisionClient:
    """
    Fallback vision via OpenRouter.
    Tente les modèles dans l'ordre jusqu'au premier succès.
    """

    def __init__(self, base_url: str, api_key: str, models: str, **_):
        self.base_url = base_url
        self.api_key = api_key
        self.models = models or ["gpt-4o"]

    def _to_image_url(self, image: str | Path) -> str:
        if isinstance(image, Path) or (isinstance(image, str) and not image.startswith("http")):
            path = Path(image)
            data = base64.b64encode(path.read_bytes()).decode()
            mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
            return f"data:{mime};base64,{data}"
        return image

    def describe(self, image: str | Path, prompt: str = "Décris cette image en détail.") -> str:
        image_url = self._to_image_url(image)
        last_error = None

        for model in self.models:
            try:
                r = httpx.post(
                    self.base_url,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": model,
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
            except Exception as e:
                last_error = e
                continue

        raise RuntimeError(f"OpenRouterVision: tous les modèles ont échoué. Dernière erreur: {last_error}")