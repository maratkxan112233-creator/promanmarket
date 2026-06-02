from aiogram.types import KeyboardButton
from aiogram.types import ReplyKeyboardMarkup


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🏪 Seller bo'lish"),
            KeyboardButton(text="🛍 Bozor"),
        ],
        [
            KeyboardButton(text="👤 Profilim"),
            KeyboardButton(text="📞 Aloqa"),
        ]
    ],
    resize_keyboard=True
)

seller_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="🏪 Seller bo'lish")
        ]
    ],
    resize_keyboard=True
)

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="❌ Bekor qilish")
        ]
    ],
    resize_keyboard=True
)

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="📱 Telefon raqamni yuborish",
                request_contact=True
            )
        ],
        [
            KeyboardButton(text="❌ Bekor qilish")
        ]
    ],
    resize_keyboard=True
)
