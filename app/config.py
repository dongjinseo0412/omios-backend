import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


def get_cors_origins() -> list[str]:
    raw_origins = os.getenv("OMIOS_CORS_ORIGINS", "").strip()
    if not raw_origins:
        return DEFAULT_CORS_ORIGINS
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


def get_cors_allow_credentials() -> bool:
    return os.getenv("OMIOS_CORS_ALLOW_CREDENTIALS", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
