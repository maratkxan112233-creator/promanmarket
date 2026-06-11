from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, ContentType, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext

from app.states.seller_application import SellerApplicationState
from app.keyboards.seller import cancel_keyboard, phone_keyboard, menu_for
from app.storage import save_application, get_application, is_seller, get_cities
from app.app.config.settings import settings

router = Router()

ALL_APP_STATES = [
    SellerApplicationState.full_name,
    SellerApplicationState.shop_name,
    SellerApplicationState.phone,
    SellerApplicationState.city,
    SellerApplicationState.card_number,
]


def _city_keyboard() -> ReplyKeyboardMarkup:
    rows, row = [], []
    for c in get_cities():
        row.append(KeyboardButton(text=c))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    rows.append([KeyboardButton(text="❌ Bekor qilish")])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


# ─── Bekor qilish ────────────────────────────────────────────────────────────
@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Amaliyot bekor qilindi.", reply_markup=menu_for(message.from_user.id))


# ─── Buyruq kelsa state ni tozalaymiz (masalan /start, /admin, /seller) ──────
@router.message(StateFilter(*ALL_APP_STATES), F.text.startswith("/"))
async def cancel_app_on_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⚠️ Ariza to'ldirish bekor qilindi.\n"
        "Qaytadan boshlash uchun: 🏪 Sotuvchi bo'lish",
        reply_markup=menu_for(message.from_user.id)
    )


# ─── Seller bo'lish ───────────────────────────────────────────────────────────
@router.message(F.text == "🏪 Sotuvchi bo'lish")
async def seller_application_start(message: Message, state: FSMContext):
    if is_seller(message.from_user.id):
        await message.answer(
            "✅ Siz allaqachon sellersiz!\n"
            "Seller panelini ochish uchun: /seller",
            reply_markup=menu_for(message.from_user.id)
        )
        return

    existing = get_application(message.from_user.id)
    if existing and existing.get("status") == "pending":
        await message.answer(
            "⏳ Arizangiz ko'rib chiqilmoqda. Iltimos kuting.",
            reply_markup=menu_for(message.from_user.id)
        )
        return

    await state.set_state(SellerApplicationState.full_name)
    await message.answer(
        "📝 Seller arizasini boshlaylik!\n\n"
        "1/5 — To'liq ismingizni kiriting (F.I.Sh):",
        reply_markup=cancel_keyboard
    )


# ─── 1: Ism ──────────────────────────────────────────────────────────────────
@router.message(SellerApplicationState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    if not (message.text or "").strip():
        await message.answer("❌ Ismingizni matn ko'rinishida kiriting:")
        return
    await state.update_data(full_name=message.text.strip())
    await state.set_state(SellerApplicationState.shop_name)
    await message.answer("2/5 — Do'kon nomini kiriting:", reply_markup=cancel_keyboard)


# ─── 2: Do'kon nomi ──────────────────────────────────────────────────────────
@router.message(SellerApplicationState.shop_name)
async def process_shop_name(message: Message, state: FSMContext):
    if not (message.text or "").strip():
        await message.answer("❌ Do'kon nomini matn ko'rinishida kiriting:")
        return
    await state.update_data(shop_name=message.text.strip())
    await state.set_state(SellerApplicationState.phone)
    await message.answer("3/5 — Telefon raqamingizni yuboring:", reply_markup=phone_keyboard)


# ─── 3: Telefon ──────────────────────────────────────────────────────────────
@router.message(SellerApplicationState.phone, F.content_type == ContentType.CONTACT)
async def process_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(SellerApplicationState.city)
    await message.answer("4/5 — Qaysi shaharda yashaysiz? Tanlang:", reply_markup=_city_keyboard())


@router.message(SellerApplicationState.phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(SellerApplicationState.city)
    await message.answer("4/5 — Qaysi shaharda yashaysiz? Tanlang:", reply_markup=_city_keyboard())


# ─── 4: Shahar ───────────────────────────────────────────────────────────────
@router.message(SellerApplicationState.city)
async def process_city(message: Message, state: FSMContext):
    if message.text not in get_cities():
        await message.answer("❌ Iltimos, pastdagi tugmalardan shaharingizni tanlang:",
                             reply_markup=_city_keyboard())
        return
    await state.update_data(city=message.text)
    await state.set_state(SellerApplicationState.card_number)
    await message.answer(
        "5/5 — Karta raqamingizni kiriting (16 raqam):\n"
        "Masalan: 8600 1234 5678 9012",
        reply_markup=cancel_keyboard
    )


# ─── 5: Karta raqami (yakuniy) ───────────────────────────────────────────────
@router.message(SellerApplicationState.card_number)
async def process_card_number(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Karta raqamini matn sifatida yuboring:")
        return
    card = message.text.replace(" ", "").replace("-", "")
    if not card.isdigit() or len(card) != 16:
        await message.answer(
            "❌ Noto'g'ri karta raqami.\n"
            "16 ta raqam kiriting (masalan: 8600 1234 5678 9012):"
        )
        return
    await state.update_data(card_number=card)
    data = await state.get_data()
    await state.clear()

    save_application(message.from_user.id, {
        "user_id":     message.from_user.id,
        "full_name":   data["full_name"],
        "shop_name":   data.get("shop_name", ""),
        "phone":       data["phone"],
        "city":        data.get("city", ""),
        "card_number": data["card_number"],
        "status":      "pending",
    })

    # Avval arizachiga tasdiq — u kutib qolmasin; owner'ga xabar keyin ketadi.
    await message.answer(
        f"✅ Arizangiz muvaffaqiyatli qabul qilindi!\n\n"
        f"👤 Ism: {data['full_name']}\n"
        f"🏪 Do'kon: {data.get('shop_name','—')}\n"
        f"📱 Telefon: {data['phone']}\n"
        f"🏙 Shahar: {data.get('city','—')}\n"
        f"💳 Karta: **** **** **** {data['card_number'][-4:]}\n\n"
        "⏳ Arizangiz ko'rib chiqiladi va natija sizga xabar qilinadi.\n"
        f"❓ Savol bo'lsa — admin: @{settings.ADMIN_USERNAME}",
        reply_markup=menu_for(message.from_user.id)
    )

    try:
        from app.bot.bot import bot
        from app.app.config.settings import settings
        await bot.send_message(
            settings.OWNER_ID,
            f"📋 Yangi seller arizasi!\n\n"
            f"👤 {data['full_name']}\n"
            f"🏪 Do'kon: {data.get('shop_name','—')}\n"
            f"🏙 Shahar: {data.get('city','—')}\n"
            f"📱 {data['phone']}\n"
            f"💳 **** {data['card_number'][-4:]}\n\n"
            f"Ko'rish: /admin"
        )
    except Exception:
        pass
