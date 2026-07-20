"""Telegram Mini App `initData` imzosini tekshirish (xavfsizlik uchun eng muhim qism).

Telegram Web App ochilganda `window.Telegram.WebApp.initData` — imzolangan
query-string beradi. Server uni BOT_TOKEN yordamida HMAC-SHA256 bilan tekshiradi.
Faqat Telegram (tokenni biladi) to'g'ri imzo yasay oladi — shuning uchun tekshiruvdan
o'tgan `user.id` ga ishonsa bo'ladi. Zakaz beruvchi (buyer_id) shu id'dan olinadi,
hech qachon mijoz yuborgan tanadan emas.
"""

import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.app.config.settings import settings


class InitDataError(Exception):
    """initData bo'sh, buzuq, imzosi noto'g'ri yoki eskirgan bo'lsa."""


def validate_init_data(init_data: str, max_age: int = 86400) -> dict:
    """initData imzosini tekshiradi. To'g'ri bo'lsa — `user` dict qaytaradi
    (ishonchli `id` bilan), aks holda InitDataError ko'taradi.

    max_age — soniyada; eskirgan (replay) auth_date rad etiladi. 0 bo'lsa —
    yosh tekshirilmaydi.
    """
    if not init_data:
        raise InitDataError("bo'sh initData")

    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError as e:
        raise InitDataError(f"buzuq initData: {e}") from e

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise InitDataError("hash yo'q")

    # data_check_string — hash'dan boshqa hamma maydon, kalit bo'yicha saralangan,
    # "\n" bilan birlashtirilgan.
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))

    # secret_key = HMAC_SHA256(key="WebAppData", msg=BOT_TOKEN)
    secret_key = hmac.new(b"WebAppData", settings.BOT_TOKEN.encode(),
                          hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(),
                         hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        raise InitDataError("imzo noto'g'ri")

    # Replay himoyasi: juda eski auth_date rad etiladi.
    if max_age:
        try:
            auth_date = int(pairs.get("auth_date", "0"))
        except ValueError:
            auth_date = 0
        if auth_date and (time.time() - auth_date) > max_age:
            raise InitDataError("initData eskirgan")

    try:
        user = json.loads(pairs.get("user", "{}"))
    except json.JSONDecodeError as e:
        raise InitDataError(f"user JSON buzuq: {e}") from e

    if not user.get("id"):
        raise InitDataError("user id yo'q")

    return user
