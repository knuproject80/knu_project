from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    APP_NAME: str = "Kiosk AI Server"
    APP_VERSION: str = "1.0.0"

    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    OPENAI_TIMEOUT: float = _get_float("OPENAI_TIMEOUT", 20.0)
    OPENAI_MAX_RETRIES: int = _get_int("OPENAI_MAX_RETRIES", 2)
    OPENAI_MAX_OUTPUT_TOKENS: int = _get_int("OPENAI_MAX_OUTPUT_TOKENS", 1000)
    OPENAI_REASONING_EFFORT: str = os.getenv("OPENAI_REASONING_EFFORT", "low")
    OPENAI_USE_STRUCTURED_OUTPUT: bool = _get_bool("OPENAI_USE_STRUCTURED_OUTPUT", True)

    USER_TYPE_CONFIDENCE_THRESHOLD: float = _get_float("USER_TYPE_CONFIDENCE_THRESHOLD", 0.60)
    SERVICE_CONFIDENCE_THRESHOLD: float = _get_float("SERVICE_CONFIDENCE_THRESHOLD", 0.60)
    AUTO_CONFIRM_CONFIDENCE_THRESHOLD: float = _get_float("AUTO_CONFIRM_CONFIDENCE_THRESHOLD", 0.85)

    DEBUG_LOGS: bool = _get_bool("DEBUG_LOGS", False)
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "*")

    @property
    def allowed_origins_list(self) -> list[str]:
        if self.ALLOWED_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]


settings = Settings()
