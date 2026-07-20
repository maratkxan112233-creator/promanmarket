import os
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
    # ─── Mini App (Web App / ilova) ───
    # Ilovaning ochiq HTTPS manzili (Railway domeni). Telegram web_app tugmasi
    # faqat https:// bilan boshlansa ko'rsatiladi. Bo'sh bo'lsa — tugma chiqmaydi.
    WEBAPP_URL: str = ""
    # Lokal/dev port. Railway ishlab chiqarishda $PORT ni beradi (main.py da o'qiladi).
    WEB_PORT: int = 8080
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    @property
    def webapp_url(self) -> str:
        """Mini App ochiq HTTPS manzili. WEBAPP_URL berilgan bo'lsa — o'sha; aks
        holda Railway avtomatik beradigan domendan quriladi (qo'lda sozlash shart
        emas — domen generatsiya qilingan zahoti tugma o'zi paydo bo'ladi)."""
        if self.WEBAPP_URL:
            return self.WEBAPP_URL
        dom = (os.getenv("RAILWAY_PUBLIC_DOMAIN")
               or os.getenv("RAILWAY_STATIC_URL") or "").strip()
        if not dom:
            return ""
        if not dom.startswith("http"):
            dom = "https://" + dom
        return dom


settings = Settings()
