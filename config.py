# aria/config.py
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


@dataclass
class Config:
    # ── Telegram ──────────────────────────────────────────────────────────────
    telegram_bot_token: str = ""
    allowed_user_id: int = 0

    # ── Clés API ──────────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    groq_api_key: str = ""
    groq_api_key_2: str = ""
    groq_api_key_3: str = ""
    mistral_api_key: str = ""
    cerebras_api_key: str = ""
    sambanova_api_key: str = ""
    openrouter_api_key: str = ""
    hf_token: str = ""

    # ── Modèles texte ─────────────────────────────────────────────────────────
    groq_model: str = "llama-3.3-70b-versatile"
    cerebras_model: str = "qwen-3-235b-a22b-instruct-2507"
    gemini_model: str = "gemini-2.0-flash"
    mistral_model: str = "mistral-small-latest"
    sambanova_model: str = "Meta-Llama-3.3-70B-Instruct"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"

    # ── Modèles vision ────────────────────────────────────────────────────────
    groq_vision_model: str = "meta-llama/llama-4-scout-17b-16e-instruct"
    openrouter_vision_models: tuple = (
        "nvidia/nemotron-nano-12b-v2-vl:free",
        "baidu/qianfan-ocr-fast:free",
    )

    # ── Modèles génération image ──────────────────────────────────────────────
    hf_image_model: str = "black-forest-labs/FLUX.1-schnell"
    image_output_dir: str = ""

    # ── Mémoire ChromaDB ──────────────────────────────────────────────────────
    chroma_path: str = ""
    max_memories_injected: int = 10
    memory_relevance_threshold: float = 0.55
    extract_every_n_turns: int = 5
    mempalace_path: str = ""

    # ── Agents ────────────────────────────────────────────────────────────────
    max_dialogue_questions: int = 3
    dialogue_timeout_minutes: int = 30

    # ── Fichiers d'identité ───────────────────────────────────────────────────
    soul_path: str = ""
    user_path: str = ""
    pending_path: str = ""

    # ── OpenRouter ────────────────────────────────────────────────────────────
    openrouter_models_refresh_hours: int = 24

    # ── Conversation ──────────────────────────────────────────────────────────
    max_history_turns: int = 10

    def __post_init__(self):
        self.telegram_bot_token = os.getenv("ARIA_BOT_TOKEN", "")
        self.allowed_user_id = int(os.getenv("ALLOWED_USER_ID", "0"))
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.groq_api_key_2 = os.getenv("GROQ_API_KEY_2", "")
        self.groq_api_key_3 = os.getenv("GROQ_API_KEY_3", "")
        self.mistral_api_key = os.getenv("MISTRAL_API_KEY", "")
        self.cerebras_api_key = os.getenv("CEREBRAS_API_KEY", "")
        self.sambanova_api_key = os.getenv("SAMBANOVA_API_KEY", "")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY", "")
        self.hf_token = os.getenv("HF_TOKEN", "")
        self.mempalace_path = "/home/nico/.mempalace/palace"
        self.chroma_path = str(BASE_DIR / "chroma_db")
        self.soul_path = str(BASE_DIR / "soul.md")
        self.user_path = str(BASE_DIR / "user.md")
        self.pending_path = str(BASE_DIR / "pending_memories.json")
        self.image_output_dir = str(BASE_DIR / "generated_images")
        self.image_receive_dir = str(BASE_DIR / "received_images")


config = Config()