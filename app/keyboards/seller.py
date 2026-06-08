from aiogram.types import (
    KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton,
)


def _build_main_menu() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🛍 Bozor"),         KeyboardButton(text="🔍 Qidirish")],
        [KeyboardButton(text="🏪 Seller bo'lish"), KeyboardButton(text="📦 Buyurtmalarim")],
        [KeyboardButton(text="👤 Profilim"),       KeyboardButton(text="📞 Aloqa")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


main_menu = _build_main_menu()

cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
    resize_keyboard=True
)

phone_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="❌ Bekor qilish")],
    ],
    resize_keyboard=True
)

def stars_kb(seller_id: int, order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⭐1", callback_data=f"rev_{seller_id}_{order_id}_1"),
            InlineKeyboardButton(text="⭐2", callback_data=f"rev_{seller_id}_{order_id}_2"),
            InlineKeyboardButton(text="⭐3", callback_data=f"rev_{seller_id}_{order_id}_3"),
            InlineKeyboardButton(text="⭐4", callback_data=f"rev_{seller_id}_{order_id}_4"),
            InlineKeyboardButton(text="⭐5", callback_data=f"rev_{seller_id}_{order_id}_5"),
        ]
    ])
