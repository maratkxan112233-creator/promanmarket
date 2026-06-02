from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.keyboards.seller import main_menu
from app.storage import register_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    register_user(message.from_user.id, {
        "full_name": message.from_user.full_name,
        "username":  message.from_user.username,
    })
    await message.answer(
        f"Salom, {message.from_user.full_name}! 👋\n\n"
        "Man Market botiga xush kelibsiz! 🛒\n"
        "Quyidagi menyudan tanlang:",
        reply_markup=main_menu
    )
