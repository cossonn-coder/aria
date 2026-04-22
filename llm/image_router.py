# aria/llm/image_router.py

from images.image_types import ImageInput
from media.image_models import ImageMemory


class ImageRouter:

    def handle_input(self, image_path: str, metadata: dict):

        caption = self.caption_model.describe(image_path)

        self.service.store_input(
            img_path=image_path,
            caption=caption,
            metadata=metadata
        )

        return caption

    def generate(self, message: str, intent_id=None):

        result = self.model.generate(message)

        image = ImageMemory(
            path=result.path,
            caption=result.caption,
            prompt=message,
            intent_id=intent_id,
            metadata={}
        )

        self.service.store_generated(image)

        return image