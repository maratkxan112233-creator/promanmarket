from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    OWNER_ID: int
    ADMIN_USERNAME: str = "Marufzxon"  # @siz, t.me/ havolasi uchun
    BOT_USERNAME: str = "promanmarketbot"  # @siz, ulashish (share) havolalari uchun
    PLATFORM_CARD: str = ""          # 10% oldi-to'lov tushadigan platforma kartasi
    PLATFORM_CARD_NAME: str = ""     # platforma kartasi egasining ismi
    COMMISSION_RATE: float = 0.10     # platforma komissiyasi (0.10 = 10%)
    # "AUKSION" guruhi — har bir yangi buyurtma (rasm + raqam + tel) shu yerga
    # to'g'ridan-to'g'ri tushadi. .env dagi AUCTION_GROUP_ID bilan almashtirish
    # mumkin; standart qiymat — AUKSION guruhining ID si. 0 — o'chirilgan.
    AUCTION_GROUP_ID: int = -1004222209334
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )


settings = Settings()
