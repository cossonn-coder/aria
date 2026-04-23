# aria/llm/image_router.py

from images.image_types import ImageArtifact, ImageInput
from config import config
from llm.vision.groq_vision import GroqVisionClient
from llm.vision.openrouter_vision import OpenRouterVisionClient
from llm.image_gen.pollinations_client import PollinationsClient
from llm.image_gen.hf_client import HuggingFaceImageClient
from pathlib import Path

# ==========================
# ROUTING TABLES
# ==========================

VISION_ROUTING_TABLE = [
    {
        "provider": "groq1",
        "client": GroqVisionClient,
        "model": config.groq_vision_model,
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": lambda: config.groq_api_key,
    },
    {
        "provider": "groq2",
        "client": GroqVisionClient,
        "model": config.groq_vision_model,
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": lambda: config.groq_api_key_2,
    },
    {
        "provider": "groq3",
        "client": GroqVisionClient,
        "model": config.groq_vision_model,
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "api_key": lambda: config.groq_api_key_3,
    },
    {
        "provider": "openrouter",
        "client": OpenRouterVisionClient,
        "models": config.openrouter_vision_models,
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "api_key": lambda: config.openrouter_api_key,
    },
]

GENERATION_ROUTING_TABLE = [
    {
        "provider": "pollinations",
        "client": PollinationsClient,
        "base_url": "https://image.pollinations.ai",
    },
    {
        "provider": "huggingface",
        "client": HuggingFaceImageClient,
        "model": config.hf_image_model,
        "base_url": "https://api-inference.huggingface.co/models",
        "api_key": lambda: config.hf_token,
    },
]


# ==========================
# ROUTER
# ==========================

class ImageRouter:
    """
    Facade image du kernel.

    Routing tables :
    - VISION_ROUTING_TABLE     → analyse / caption d'image
    - GENERATION_ROUTING_TABLE → génération d'image depuis prompt

    Même pattern que LLMRouter : fallback automatique dans l'ordre de la table.
    Ne connaît pas MemPalace. Ne connaît pas IntentEngine.
    Retourne uniquement des ImageArtifact.
    """

    def __init__(
        self,
        vision_table=None,
        generation_table=None,
    ):
        # Injection dépendance → testable
        self.vision_table = vision_table or VISION_ROUTING_TABLE
        self.generation_table = generation_table or GENERATION_ROUTING_TABLE

    def handle_input(self, image_input: ImageInput) -> ImageArtifact:
        source = image_input.path or image_input.base64

        caption = self._run_vision(
            source,
            prompt="Describe this image."
        )

        return ImageArtifact(
            source=image_input.source,
            path=image_input.path,
            caption=caption,
            metadata={},
        )

    def generate(self, message: str, intent_id: str | None = None) -> ImageArtifact:
        result = self._run_generation(message)
        return ImageArtifact(
            source="generated",
            path=result.path,
            caption=result.caption,
            prompt=message,
            intent_id=intent_id,
            metadata={},
        )


    # ==========================
    # INTERNAL DISPATCH
    # ==========================

    def _dispatch(self, table, method, **kwargs):
        """
        Dispatcher générique provider → client.

        Tolère des entrées partielles afin de faciliter
        les tests unitaires et les mocks.
        """

        last_error = None

        for entry in table:
            try:
                client = entry["client"](
                    base_url=entry.get("base_url"),
                    model=entry.get("model"),
                    models=entry.get("models"),
                    api_key=entry.get("api_key", lambda: None)(),
                    output_dir=config.image_output_dir,
                )

                return getattr(client, method)(**kwargs)

            except Exception as e:
                print(f"[IMAGE ROUTER FALLBACK] {entry.get('provider')} failed: {e}")
                last_error = e

        raise RuntimeError(last_error)

    def _run_vision(self, image, prompt):
        return self._dispatch(
            self.vision_table,
            "describe",
            image=image,
            prompt=prompt,
        )

    def _run_generation(self, prompt):
        return self._dispatch(
            self.generation_table,
            "generate",
            prompt=prompt,
        )