from aiogram.types import (
    KeyboardButton, ReplyKeyboardMarkup,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# Menyu versiyasi: menyu tugmalari o'zgarganda shu raqamni 1 taga oshiring.
# Shunda foydalanuvchilar /start bosmasdan ham yangi menyuni avtomatik oladi
# (dispatcher.py dagi MenuRefreshMiddleware orqali).
MENU_VERSION = 5


def _build_main_menu() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="🛍 Katalog"),        KeyboardButton(text="🔍 Qidiruv")],
        [KeyboardButton(text="🧺 Savat"),          KeyboardButton(text="📦 Buyurtmalarim")],
        [KeyboardButton(text="❤️ Sevimlilar"),     KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="🏪 Sotuvchi bo'lish")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


main_menu = _build_main_menu()


def _build_seller_main_menu() -> ReplyKeyboardMarkup:
    rows = [
        [KeyboardButton(text="📊 Sotuvchi paneli"), KeyboardButton(text="👥 Shahrim sellerlari")],
        [KeyboardButton(text="👤 Profil")],
    ]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


seller_main_menu = _build_seller_main_menu()


def menu_for(user_id: int) -> ReplyKeyboardMarkup:
    """Seller yoki yordamchi bo'lsa seller menyusi, aks holda xaridor menyusi."""
    from app.storage import is_shop_member
    return seller_main_menu if is_shop_member(user_id) else main_menu


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

def admin_contact_kb() -> InlineKeyboardMarkup:
    """Bir bosishda admin chatini ochadigan kompakt tugma."""
    from app.app.config.settings import settings
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Admin bilan bog'lanish",
                              url=f"https://t.me/{settings.ADMIN_USERNAME}")]
    ])


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
