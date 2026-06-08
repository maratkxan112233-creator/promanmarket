from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards.seller import main_menu
from app.storage import register_user
from app.handlers.common import FREE_DELIVERY_BANNER

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user.id, {
        "full_name": message.from_user.full_name,
        "username":  message.from_user.username,
    })
    await message.answer(
        f"Salom, {message.from_user.full_name}! 👋\n\n"
        "Man Market botiga xush kelibsiz! 🛒\n\n"
        f"{FREE_DELIVERY_BANNER}\n\n"
        "Quyidagi menyudan tanlang:",
        parse_mode="HTML",
        reply_markup=main_menu
    )
