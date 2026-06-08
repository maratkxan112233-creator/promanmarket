"""Albom (media group) rasmlarini bitta to'plamga yig'uvchi yordamchi.

Telegram albomdagi har bir rasmni alohida xabar qilib yuboradi. Ular deyarli
bir vaqtda kelganligi sababli, har biri uchun alohida mahsulot yaratilib
qolardi. Bu modul rasmlarni media_group bo'yicha yig'ib, oxirgi rasmdan
keyin qisqa pauza bilan bitta marta `on_complete(photos)` ni chaqiradi.
"""
import asyncio

_buffers: dict = {}   # key -> {"photos": [...], "task": Task|None}


def collect(key, file_id: str, delay: float, on_complete):
    """Bitta rasmni buferga qo'shadi va finalize taymerini qayta qo'yadi.

    key          : unikal kalit (masalan (user_id, media_group_id))
    file_id      : Telegram rasm file_id
    delay        : oxirgi rasmdan keyin necha soniya kutiladi
    on_complete  : async funksiya, photos ro'yxati bilan chaqiriladi
    """
    buf = _buffers.setdefault(key, {"photos": [], "task": None})
    buf["photos"].append(file_id)
    if buf["task"]:
        buf["task"].cancel()
    buf["task"] = asyncio.create_task(_finalize(key, delay, on_complete))


async def _finalize(key, delay: float, on_complete):
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return
    buf = _buffers.pop(key, None)
    if not buf or not buf["photos"]:
        return
    await on_complete(buf["photos"])
