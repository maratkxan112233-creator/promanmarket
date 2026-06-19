from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

from app.keyboards.seller import menu_for, MENU_VERSION
from app.storage import register_user, set_user_field
from app.handlers.common import (
    FREE_DELIVERY_BANNER, SELLER_INVITE_BANNER,
    DELIVERY_FEE, FREE_DELIVERY_THRESHOLD,
)
from app.ui import money
from app.app.config.settings import settings

router = Router()


# ─── Pilot: ikki tilli (uz/ru) start ekrani matnlari ─────────────────────────
# Hozircha faqat /start ekrani tarjima qilinadi. Menyu va qolgan bo'limlar
# o'zbekcha. Yoqsa, keyin xaridor oqimiga kengaytiramiz (storage.get_lang +
# markaziy TEXTS moduli orqali).
def _delivery_banner(lang: str) -> str:
    if lang == "ru":
        fee = money(DELIVERY_FEE).replace("so'm", "сум")
        free = money(FREE_DELIVERY_THRESHOLD).replace("so'm", "сум")
        return (
            f"🚚 <b>Доставка — всего {fee}!</b>\n"
            f"🎉 <b>При покупке от {free} — БЕСПЛАТНО!</b>\n"
            "Закажите сегодня — доставим сегодня."
        )
    return FREE_DELIVERY_BANNER


def _seller_banner(lang: str) -> str:
    if lang == "ru":
        return (
            "🤝 <b>Приглашаем продавцов к сотрудничеству!</b>\n"
            f"Связь: @{settings.ADMIN_USERNAME}"
        )
    return SELLER_INVITE_BANNER


TEXTS = {
    "uz": {
        "welcome": "👋 Salom!\n<b>Proman Market</b> botiga xush kelibsiz!",
        "become_seller": "🏪 Seller bo'lish",
        "write_admin": "💬 Adminga yozish",
        "pick_from_menu": "👇 Yoki quyidagi menyudan tanlang:",
    },
    "ru": {
        "welcome": "👋 Здравствуйте!\nДобро пожаловать в бот <b>Proman Market</b>!",
        "become_seller": "🏪 Стать продавцом",
        "write_admin": "💬 Написать админу",
        "pick_from_menu": "👇 Или выберите из меню ниже:",
    },
}


def _lang_picker() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="setlang_uz")],
        [InlineKeyboardButton(text="🇷🇺 Русский",   callback_data="setlang_ru")],
    ])


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user.id, {
        "full_name": message.from_user.full_name,
        "username":  message.from_user.username,
    })
    # /start menyuni o'zi yuboradi — qayta yangilash kerak emas
    set_user_field(message.from_user.id, "menu_ver", MENU_VERSION)
    # Avval tilni so'raymiz; salomlashish tanlovdan keyin yuboriladi.
    await message.answer(
        "Tilni tanlang / Выберите язык:",
        reply_markup=_lang_picker(),
    )


@router.callback_query(F.data.startswith("setlang_"))
async def set_language(call: CallbackQuery):
    lang = call.data.split("_", 1)[1]
    if lang not in ("uz", "ru"):
        lang = "uz"
    set_user_field(call.from_user.id, "lang", lang)
    t = TEXTS[lang]
    await call.answer()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t["become_seller"], callback_data="become_seller")],
        [InlineKeyboardButton(text=t["write_admin"],
                              url=f"https://t.me/{settings.ADMIN_USERNAME}")],
    ])
    await call.message.answer(
        f"{t['welcome']}\n\n"
        f"{_delivery_banner(lang)}\n"
        f"{_seller_banner(lang)}",
        parse_mode="HTML",
        reply_markup=kb,
    )
    # Pastdagi doimiy menyu (Buyurtmalarim, Profil va h.k.) — hozircha o'zbekcha.
    await call.message.answer(
        t["pick_from_menu"],
        reply_markup=menu_for(call.from_user.id),
    )
