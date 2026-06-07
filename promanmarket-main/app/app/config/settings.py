from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    OWNER_ID: int
    PLATFORM_CARD: str = ""          # 10% oldi-to'lov tushadigan platforma kartasi
    COMMISSION_RATE: float = 0.10     # platforma komissiyasi (0.10 = 10%)
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
