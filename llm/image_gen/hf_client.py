# aria/llm/image_gen/hf_client.py

import httpx
import hashlib
from pathlib import Path


class HuggingFaceImageClient:
    """
    Fallback génération image via HuggingFace Inference API.
    Modèle sélectionné dans image router hf_image_model.

    Gratuit avec rate limiting.
    Sans HF_TOKEN : fonctionne en anonyme mais plus lentement.
    """

    def __init__(self, base_url, model, output_dir, api_key=None, **_):
        self.base_url = base_url
        self.model = model
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, prompt: str) -> "GenerationResult":
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        url = f"{self.base_url}/models/{self.model}"
        r = httpx.post(
            url,
            headers=headers,
            json={"inputs": prompt},
            timeout=120,
        )
        r.raise_for_status()

        slug = hashlib.md5(prompt.encode()).hexdigest()[:12]
        filename = self.output_dir / f"aria_hf_{slug}.png"
        filename.write_bytes(r.content)

        return GenerationResult(
            path=str(filename),
            caption=f"[generated via HF: {prompt[:60]}]",
        )


class GenerationResult:
    def __init__(self, path: str, caption: str):
        self.path = path
        self.caption = caption