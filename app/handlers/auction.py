"""AUKSION guruhidagi maxfiy takliflar — hammasi guruh ICHIDA.

Guruhga tushgan buyurtmaga ulgurji sotuvchilar narx taklif qiladilar.
Konflikt bo'lmasligi uchun takliflar boshqa qatnashchilarga ko'rinmaydi:

1. Sotuvchi buyurtma postiga REPLY qilib taklifini yozadi.
2. Bot yozuvni DARHOL o'chiradi va taklifni saqlab qo'yadi.
3. Post ostidagi «📋 Takliflar (N)» tugmasi bosilganda chiqadigan oyna
   FAQAT bosgan odamning o'ziga ko'rinadi (Telegram callback-alert):
   • admin bossa — HAMMA takliflar chiqadi;
   • taklif bergan sotuvchi bossa — faqat O'Z taklifi chiqadi;
   • boshqalar bossa — «takliflar maxfiy» deyiladi.

Hech qanday shaxsiy xabar (DM) ishlatilmaydi — hammasi guruh ichida.

MUHIM: bot guruhda ADMIN bo'lishi va «Delete messages» huquqiga ega
bo'lishi shart, aks holda taklif yozuvlarini o'chira olmaydi.
"""
import asyncio
import re

from aiogram import Router, F
from aiogram.types import (CallbackQuery, InlineKeyboardButton,
                           InlineKeyboardMarkup, Message)

from app.app.config.settings import settings
from app.storage import add_auction_offer, get_auction_offers

router = Router()

# Telegram callback-alert oynasi ~200 belgigacha matn ko'rsatadi
ALERT_LIMIT = 195


def _offers_kb(order_id, count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=f"📋 Takliflar ({count})",
                             callback_data=f"aucoff_{order_id}")
    ]])


def _order_id_from(message: Message) -> str | None:
    """Reply qilingan buyurtma postidan raqamni (#123) topadi."""
    r = message.reply_to_message
    if not r:
        return None
    src = (r.caption or r.text) or ""
    m = re.search(r"#(\w+)", src)
    return m.group(1) if m else None


async def _temp_note(chat_id: int, text: str, seconds: int = 6):
    """Guruhga qisqa eslatma yozib, bir necha soniyadan keyin o'chiradi."""
    from app.bot.bot import bot
    try:
        note = await bot.send_message(chat_id, text)
    except Exception:
        return

    async def _cleanup():
        await asyncio.sleep(seconds)
        try:
            await note.delete()
        except Exception:
            pass

    asyncio.create_task(_cleanup())


@router.message(F.chat.id == settings.AUCTION_GROUP_ID,
                ~F.text.regexp(r"^/id(@\w+)?\b"))
async def auction_offer(message: Message):
    u = message.from_user
    # Service-xabarlar (a'zo qo'shildi/chiqdi va h.k.) — e'tiborsiz
    if not u or u.is_bot:
        return

    # Adminlarning o'z yozuvlariga tegmaymiz — ular guruhda qoladi
    from app.handlers.admin import is_admin
    if is_admin(u.id):
        return

    text = (message.text or message.caption or "").strip()
    order_id = _order_id_from(message)

    # 1) Yozuvni DARHOL o'chiramiz — boshqalar ko'rmasin
    deleted = True
    try:
        await message.delete()
    except Exception:
        deleted = False  # bot guruhda admin emas yoki huquq yo'q

    if not deleted:
        # O'chira olmadik — hech bo'lmasa adminni ogohlantiramiz (bir marta emas,
        # har safar: muammo hal bo'lguncha ko'rinib tursin)
        await _temp_note(
            message.chat.id,
            "⚠️ Bot xabarlarni o'chira olmayapti. Botga guruhda admin va "
            "«Delete messages» huquqini bering!", 15)
        return

    # 2) Buyurtma postiga reply qilinmagan bo'lsa — qanday yozishni eslatamiz
    if not order_id or not text:
        await _temp_note(
            message.chat.id,
            "ℹ️ Narx taklifini buyurtma postiga REPLY qilib, matn bilan yozing.")
        return

    # 3) Taklifni saqlaymiz
    who = u.full_name + (f" (@{u.username})" if u.username else "")
    count = add_auction_offer(order_id, u.id, who, text[:300])

    # 4) Post tugmasidagi sonni yangilaymiz: «📋 Takliflar (N)»
    r = message.reply_to_message
    if r:
        from app.bot.bot import bot
        try:
            await bot.edit_message_reply_markup(
                chat_id=message.chat.id, message_id=r.message_id,
                reply_markup=_offers_kb(order_id, count))
        except Exception:
            pass

    # 5) Qisqa tasdiq (taklif matni KO'RSATILMAYDI, o'zi o'chib ketadi)
    await _temp_note(
        message.chat.id,
        f"✅ #{order_id} ga taklif qabul qilindi. "
        f"«📋 Takliflar» tugmasidan ko'ring.")


@router.callback_query(F.data.startswith("aucoff_"))
async def show_offers(call: CallbackQuery):
    """«📋 Takliflar» tugmasi — alert oynasi FAQAT bosgan odamga ko'rinadi."""
    order_id = call.data.split("_", 1)[1]
    offers = get_auction_offers(order_id)

    from app.handlers.admin import is_admin
    uid = call.from_user.id

    if is_admin(uid):
        visible = offers                      # admin — hammasini ko'radi
        empty = "Hozircha taklif yo'q."
    else:
        visible = [o for o in offers if o.get("uid") == uid]  # faqat o'ziniki
        empty = ("🔒 Takliflar maxfiy — faqat admin va taklif berganlar "
                 "ko'radi. Taklif berish uchun postga reply yozing.")

    if not visible:
        await call.answer(empty, show_alert=True)
        return

    # Oxirgi takliflardan boshlab, alert sig'imiga (~200 belgi) sig'diramiz
    lines = []
    used = len(f"📋 #{order_id}:\n")
    for o in reversed(visible):
        line = f"• {o.get('name','—')}: {o.get('text','')}"
        if used + len(line) + 1 > ALERT_LIMIT:
            lines.append("…")
            break
        lines.append(line)
        used += len(line) + 1
    body = f"📋 #{order_id}:\n" + "\n".join(lines)
    await call.answer(body[:ALERT_LIMIT + 5], show_alert=True)
