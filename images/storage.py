#aria/images/storage.py

from pathlib import Path


class ImageStorage:
    def save(self, data: bytes) -> str:
        raise NotImplementedError

    def load(self, path: str) -> bytes:
        raise NotImplementedError


class DefaultImageStorage(ImageStorage):
    def save(self, data: bytes) -> str:
        path = Path("images/output.bin")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return str(path)

    def load(self, path: str) -> bytes:
        return Path(path).read_bytes()