from aiogram import Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message

from app.handlers.ads import router as ads_router
from app.handlers.auction import router as auction_router
from app.handlers.start import router as start_router
from app.handlers.seller.application import router as seller_app_router
from app.handlers.admin import router as admin_router
from app.handlers.admin_settings import router as admin_settings_router
from app.handlers.seller_panel import router as seller_panel_router
from app.handlers.info import router as info_router
from app.handlers.common import router as common_router


class MenuRefreshMiddleware(BaseMiddleware):
    """Bot yangilanganda foydalanuvchilarga menyuni /start bosmasdan yangilab beradi.

    Menyu tugmalari o'zgarganda keyboards/seller.py dagi MENU_VERSION 1 taga
    oshiriladi. Foydalanuvchi keyingi safar istalgan xabar yozganda eski
    klaviaturasi avtomatik yangisiga almashtiriladi.
    """

    async def __call__(self, handler, event: Message, data: dict):
        try:
            uid = event.from_user.id if event.from_user else None
            text = event.text or ""
            # FSM jarayonida (ariza, buyurtma, qidiruv...) klaviaturani
            # almashtirmaymiz — jarayon tugagach o'zi yangilanadi.
            # /start da ham shart emas — u menyuni o'zi yuboradi.
            # Faqat shaxsiy chatda ishlaydi — guruhda (masalan, AUKSION)
            # "Menyu yangilandi" xabari chiqib ketmasligi kerak.
            if (uid and event.chat.type == "private"
                    and data.get("raw_state") is None
                    and not text.startswith("/start")):
                from app.storage import get_user, set_user_field, get_runtime_config
                from app.keyboards.seller import MENU_VERSION, menu_for
                u = get_user(uid) or {}
                if u.get("menu_ver") != MENU_VERSION:
                    set_user_field(uid, "menu_ver", MENU_VERSION)
                    # MUHIM: reply-klaviatura uni olib kelgan xabarga bog'langan.
                    # Agar xabarni o'chirsak, klaviatura ham yo'qoladi (xaridorda
                    # panel ko'rinmay qolardi). Shuning uchun O'CHIRMAYMIZ — bu
                    # faqat versiya o'zgarganda bir marta yuboriladi.
                    await event.answer(
                        "Menyu yangilandi.",
                        reply_markup=menu_for(uid),
                    )
                # Admin sozlagan popup xabar — har foydalanuvchiga har popup-id
                # uchun BIR marta ko'rsatiladi (admin panel → ⚙️ Sozlamalar).
                pop = get_runtime_config().get("popup", {})
                if (pop.get("enabled") and pop.get("text")
                        and u.get("popup_seen_id") != pop.get("id")):
                    set_user_field(uid, "popup_seen_id", pop.get("id"))
                    await event.answer(pop["text"], parse_mode="HTML")
        except Exception:
            pass  # menyu yangilash xatosi asosiy ishga to'sqinlik qilmasin
        return await handler(event, data)


# Production uchun RedisStorage tavsiya etiladi:
# from aiogram.fsm.storage.redis import RedisStorage
# storage = RedisStorage.from_url("redis://localhost:6379")
storage = MemoryStorage()

dp = Dispatcher(storage=storage)

dp.message.outer_middleware(MenuRefreshMiddleware())

dp.include_router(auction_router)     # AUKSION guruhi — hammadan OLDIN
dp.include_router(ads_router)         # guruh reklamalari (owner) — common dan OLDIN
dp.include_router(admin_router)
dp.include_router(admin_settings_router)  # ⚙️ Sozlamalar (owner)
dp.include_router(seller_panel_router)
dp.include_router(seller_app_router)   # common dan OLDIN
dp.include_router(info_router)         # ℹ️ Ma'lumot — common dan OLDIN (label to'qnashuvi)
dp.include_router(common_router)
dp.include_router(start_router)
