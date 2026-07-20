from aiogram import Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           WebAppInfo)

from app.keyboards.seller import menu_for, MENU_VERSION
from app.storage import register_user, set_user_field, get_product_by_id, track_event
from app.handlers.common import SELLER_INVITE_BANNER, send_product_card
from app.services import runtime_settings as rs
from app.app.config.settings import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext):
    await state.clear()
    uid = message.from_user.id
    register_user(uid, {
        "full_name": message.from_user.full_name,
        "username":  message.from_user.username,
    })
    # /start menyuni o'zi yuboradi — qayta yangilash kerak emas
    set_user_field(uid, "menu_ver", MENU_VERSION)
    track_event("start", uid)

    # Deep-link: t.me/bot?start=prod_N («📤 Do'stingizga ulashish» havolasi) —
    # mahsulot kartasi to'g'ridan-to'g'ri ochiladi.
    arg = (command.args or "").strip()
    if arg.startswith("prod_") and arg[5:].isdigit():
        p = get_product_by_id(int(arg[5:]))
        if p:
            await message.answer("👇 Sizga ulashilgan mahsulot:",
                                 reply_markup=menu_for(uid))
            await send_product_card(message, uid, p)
            return

    rows = []
    # Mini App (ilova) tugmasi — faqat HTTPS manzil bo'lsa ko'rsatiladi (Telegram
    # web_app faqat https:// URL'ni qabul qiladi). Manzil WEBAPP_URL yoki Railway
    # domenidan avtomatik olinadi (settings.webapp_url).
    web_url = settings.webapp_url
    if web_url.startswith("https://"):
        rows.append([InlineKeyboardButton(
            text="🛍 Do'konni ochish (ilova)",
            web_app=WebAppInfo(url=web_url))])
    rows += [
        [InlineKeyboardButton(
            text="➕ Botni guruhingizga qo'shing",
            url=f"https://t.me/{settings.BOT_USERNAME}?startgroup=true")],
        [InlineKeyboardButton(text="Sotuvchi bo'lish", callback_data="become_seller")],
        [InlineKeyboardButton(text="Admin bilan bog'lanish",
                              url=f"https://t.me/{settings.ADMIN_USERNAME}")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer(
        f"{rs.start_banner()}\n\n"
        "<b>Pro Man Market</b> — xush kelibsiz.\n\n"
        "Sifatli mahsulotlar, halol narxlar va tezkor yetkazib berish.\n\n"
        f"{SELLER_INVITE_BANNER}\n\n"
        "➕ Botni guruhingizga qo'shing — yangi mahsulot va aksiyalar "
        "guruhda ham chiqadi.",
        parse_mode="HTML",
        reply_markup=kb,
    )
    # Pastdagi doimiy menyuni ham qoldiramiz (Buyurtmalarim, Profil va h.k.)
    await message.answer(
        "Quyidagi menyudan bo'limni tanlang.",
        reply_markup=menu_for(uid),
    )
