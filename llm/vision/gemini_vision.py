# aria/llm/vision/gemini_vision.py
#
# Client vision Gemini, appel natif generateContent (sprint 59, tronçon 01).
#
# Sert à lire une position d'échecs sur une image : la chaîne vision prod
# (deepseek, qwen) lit faux, Gemini lit juste. Le point d'accès compatible
# OpenAI a dépassé les 30 s de GroqVisionClient : on passe par l'API native.
# Même interface que GroqVisionClient : describe(image, prompt) -> str.

import base64
import mimetypes
from pathlib import Path

import httpx

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiVisionClient:
    """Analyse d'image via l'API native Gemini. Modèle injecté par le router."""

    def __init__(self, api_key: str, model: str, **_):
        self.api_key = api_key
        self.model = model

    def describe(self, image: str | Path, prompt: str) -> str:
        # Chemin local → base64 ; le type MIME est déduit de l'extension.
        path = Path(image)
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        data = base64.b64encode(path.read_bytes()).decode()
        body = {"contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": mime, "data": data}},
        ]}]}
        # Timeout large : ~10 s par lecture mesurés, parfois bien plus.
        r = httpx.post(
            _URL.format(model=self.model),
            params={"key": self.api_key},
            json=body,
            timeout=90,
        )
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][-1]["text"]
