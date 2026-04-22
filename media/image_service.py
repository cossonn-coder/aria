# aria/media/image_service.py

from memory.mempalace_writer import store_interaction
from .image_models import ImageMemory


class ImageService:

    def store_generated(self, img: ImageMemory):
        store_interaction(
            text=f"IMAGE_GENERATED\n{img.caption}\nPROMPT:\n{img.prompt}",
            intent_id=img.intent_id or "image_generation",
            metadata={
                "type": "image",
                "path": img.path,
                **img.metadata,
            },
        )

    def store_input(self, img_path: str, caption: str, metadata: dict):
        store_interaction(
            text=f"IMAGE_INPUT\n{caption}",
            intent_id="image_input",
            metadata={
                "type": "image_input",
                "path": img_path,
                **metadata,
            },
        )