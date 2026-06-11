from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from app.keyboards.seller import menu_for
from app.storage import register_user
from app.handlers.common import FREE_DELIVERY_BANNER, SELLER_INVITE_BANNER
from app.app.config.settings import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user.id, {
        "full_name": message.from_user.full_name,
        "username":  message.from_user.username,
    })
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏪 Seller bo'lish", callback_data="become_seller")],
        [InlineKeyboardButton(text="💬 Adminga yozish",
                              url=f"https://t.me/{settings.ADMIN_USERNAME}")],
    ])
    await message.answer(
        "👋 Salom!\n"
        "<b>Proman Market</b> botiga xush kelibsiz!\n\n"
        f"{FREE_DELIVERY_BANNER}\n"
        f"{SELLER_INVITE_BANNER}",
        parse_mode="HTML",
        reply_markup=kb,
    )
    # Pastdagi doimiy menyuni ham qoldiramiz (Buyurtmalarim, Profil va h.k.)
    await message.answer(
        "👇 Yoki quyidagi menyudan tanlang:",
        reply_markup=menu_for(message.from_user.id),
    )
