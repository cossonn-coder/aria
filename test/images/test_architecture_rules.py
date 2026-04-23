import inspect

from llm.vision.groq_vision import GroqVisionClient
from llm.vision.openrouter_vision import OpenRouterVisionClient
from llm.image_gen.pollinations_client import PollinationsClient
from llm.image_gen.hf_client import HuggingFaceImageClient


CLIENTS = [
    GroqVisionClient,
    OpenRouterVisionClient,
    PollinationsClient,
    HuggingFaceImageClient,
]


def test_clients_do_not_import_config():
    for client in CLIENTS:
        source = inspect.getsource(client)
        assert "config" not in source


def test_clients_are_transport_only():
    forbidden = ["Intent", "Kernel", "Memory", "Agent"]

    for client in CLIENTS:
        source = inspect.getsource(client)
        for f in forbidden:
            assert f not in source