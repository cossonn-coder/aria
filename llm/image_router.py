# aria/llm/image_router.py

from images.image_types import ImageArtifact, ImageInput


class _StubCaptionModel:
    """Stub CPU-safe — remplacer par un vrai modèle BLIP/LLaVA si dispo."""
    def describe(self, path: str) -> str:
        return f"[caption: {path}]"


class _StubGenerationModel:
    """Stub sans GPU — remplacer par Stable Diffusion / DALL-E si dispo."""
    def generate(self, prompt: str):
        from dataclasses import dataclass

        @dataclass
        class _Result:
            path: str
            caption: str

        return _Result(
            path="/tmp/aria_generated.png",
            caption=f"[generated from: {prompt}]",
        )


class ImageRouter:

    def __init__(self, caption_model=None, generation_model=None):
        self.caption_model = caption_model or _StubCaptionModel()
        self.model = generation_model or _StubGenerationModel()

    def handle_input(self, image_input: ImageInput) -> ImageArtifact:
        caption = self.caption_model.describe(image_input.path)
        return ImageArtifact(
            source="input",
            path=image_input.path,
            caption=caption,
            metadata=image_input.metadata if hasattr(image_input, "metadata") else {},
        )

    def generate(self, message: str, intent_id=None) -> ImageArtifact:
        result = self.model.generate(message)
        return ImageArtifact(
            source="generated",
            path=result.path,
            caption=result.caption,
            prompt=message,
            intent_id=intent_id,
            metadata={},
        )