from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.seller import main_menu

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"Salom, {message.from_user.full_name}! 👋\n\n"
        "Man Market botiga xush kelibsiz! 🛒\n"
        "Quyidagi menyudan tanlang:",
        reply_markup=main_menu
    )
