from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    app_name: str = "AI 产品运营 Copilot"
    app_version: str = "0.1.0"
    llm_api_key: str = ""
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    data_file: str = "data/state.json"
    rate_limit: int = 120
    rate_window_seconds: int = 60

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def demo_mode(self) -> bool:
        return not bool(self.llm_api_key.strip())

    @property
    def data_path(self) -> Path:
        path = Path(self.data_file)
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
