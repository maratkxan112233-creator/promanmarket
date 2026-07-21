from aiogram import Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           WebAppInfo)

from app.keyboards.seller import menu_for, MENU_VERSION
from app.storage import register_user, set_user_field, get_product_by_id, track_event
from app.handlers.common import send_product_card
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

    # /start — bannersiz, faqat 3 ta tugma:
    #   1) Sotuvchi bo'lish
    #   2) App (ilova) orqali ochish — Mini App
    #   3) Bot orqali ochish — botning katalog bosh sahifasi (ghome)
    rows = [
        [InlineKeyboardButton(text="🏪 Sotuvchi bo'lish", callback_data="become_seller")],
    ]
    # Mini App tugmasi faqat HTTPS manzil bo'lsa ko'rsatiladi (Telegram web_app
    # faqat https:// URL'ni qabul qiladi). Manzil settings.webapp_url'dan olinadi.
    web_url = settings.webapp_url
    if web_url.startswith("https://"):
        rows.append([InlineKeyboardButton(
            text="📱 App (ilova) orqali ochish",
            web_app=WebAppInfo(url=web_url))])
    rows.append([InlineKeyboardButton(
        text="🛍 Bot orqali ochish", callback_data="ghome")])

    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    await message.answer("<b>Pro Man Market</b>", parse_mode="HTML", reply_markup=kb)
