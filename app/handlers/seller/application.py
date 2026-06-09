from aiogram import Router, F
from aiogram.filters import StateFilter
from aiogram.types import Message, ContentType, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext

from app.states.seller_application import SellerApplicationState
from app.keyboards.seller import cancel_keyboard, phone_keyboard, main_menu
from app.storage import save_application, get_application, is_seller, get_cities

router = Router()

ALL_APP_STATES = [
    SellerApplicationState.full_name,
    SellerApplicationState.phone,
    SellerApplicationState.city,
    SellerApplicationState.shop_name,
    SellerApplicationState.card_number,
    SellerApplicationState.passport_photo,
    SellerApplicationState.selfie_photo,
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
    await message.answer("Amaliyot bekor qilindi.", reply_markup=main_menu)


# ─── Buyruq kelsa state ni tozalaymiz (masalan /start, /admin, /seller) ──────
@router.message(StateFilter(*ALL_APP_STATES), F.text.startswith("/"))
async def cancel_app_on_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "⚠️ Ariza to'ldirish bekor qilindi.\n"
        "Qaytadan boshlash uchun: 🏪 Sotuvchi bo'lish",
        reply_markup=main_menu
    )


# ─── Seller bo'lish ───────────────────────────────────────────────────────────
@router.message(F.text == "🏪 Sotuvchi bo'lish")
async def seller_application_start(message: Message, state: FSMContext):
    if is_seller(message.from_user.id):
        await message.answer(
            "✅ Siz allaqachon sellersiz!\n"
            "Seller panelini ochish uchun: /seller",
            reply_markup=main_menu
        )
        return

    existing = get_application(message.from_user.id)
    if existing and existing.get("status") == "pending":
        await message.answer(
            "⏳ Arizangiz ko'rib chiqilmoqda. Iltimos kuting.",
            reply_markup=main_menu
        )
        return

    await state.set_state(SellerApplicationState.full_name)
    await message.answer(
        "📝 Seller arizasini boshlaylik!\n\n"
        "1/7 — To'liq ismingizni kiriting (F.I.Sh):",
        reply_markup=cancel_keyboard
    )


# ─── 1: Ism ──────────────────────────────────────────────────────────────────
@router.message(SellerApplicationState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(SellerApplicationState.phone)
    await message.answer("2/7 — Telefon raqamingizni yuboring:", reply_markup=phone_keyboard)


# ─── 2: Telefon ──────────────────────────────────────────────────────────────
@router.message(SellerApplicationState.phone, F.content_type == ContentType.CONTACT)
async def process_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(SellerApplicationState.city)
    await message.answer("3/7 — Do'koningiz qaysi shaharda? Tanlang:", reply_markup=_city_keyboard())


@router.message(SellerApplicationState.phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(SellerApplicationState.city)
    await message.answer("3/7 — Do'koningiz qaysi shaharda? Tanlang:", reply_markup=_city_keyboard())


# ─── 3: Shahar ───────────────────────────────────────────────────────────────
@router.message(SellerApplicationState.city)
async def process_city(message: Message, state: FSMContext):
    if message.text not in get_cities():
        await message.answer("❌ Iltimos, pastdagi tugmalardan shaharingizni tanlang:",
                             reply_markup=_city_keyboard())
        return
    await state.update_data(city=message.text)
    await state.set_state(SellerApplicationState.shop_name)
    await message.answer("4/7 — Do'koningiz nomini kiriting:", reply_markup=cancel_keyboard)


# ─── 4: Do'kon nomi ──────────────────────────────────────────────────────────
@router.message(SellerApplicationState.shop_name)
async def process_shop_name(message: Message, state: FSMContext):
    await state.update_data(shop_name=message.text)
    await state.set_state(SellerApplicationState.card_number)
    await message.answer("5/7 — Karta raqamingizni kiriting (16 raqam):", reply_markup=cancel_keyboard)


# ─── 5: Karta raqami ─────────────────────────────────────────────────────────
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
    await state.set_state(SellerApplicationState.passport_photo)
    await message.answer("6/7 — Pasportingiz rasmini yuboring (birinchi sahifa):", reply_markup=cancel_keyboard)


# ─── 6: Pasport rasmi ────────────────────────────────────────────────────────
@router.message(SellerApplicationState.passport_photo, F.content_type == ContentType.PHOTO)
async def process_passport_photo(message: Message, state: FSMContext):
    await state.update_data(passport_photo=message.photo[-1].file_id)
    await state.set_state(SellerApplicationState.selfie_photo)
    await message.answer("7/7 — Pasportingiz bilan selfi rasmini yuboring:", reply_markup=cancel_keyboard)


@router.message(SellerApplicationState.passport_photo)
async def process_passport_photo_wrong(message: Message, state: FSMContext):
    await message.answer("❌ Iltimos, rasm yuboring (foto sifatida).")


# ─── 6: Selfi ────────────────────────────────────────────────────────────────
@router.message(SellerApplicationState.selfie_photo, F.content_type == ContentType.PHOTO)
async def process_selfie_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(selfie_photo=photo_id)
    data = await state.get_data()
    await state.clear()

    save_application(message.from_user.id, {
        "user_id":        message.from_user.id,
        "full_name":      data["full_name"],
        "phone":          data["phone"],
        "city":           data.get("city", ""),
        "shop_name":      data["shop_name"],
        "card_number":    data["card_number"],
        "passport_photo": data["passport_photo"],
        "selfie_photo":   photo_id,
        "status":         "pending",
    })

    try:
        from app.bot.bot import bot
        from app.app.config.settings import settings
        await bot.send_message(
            settings.OWNER_ID,
            f"📋 Yangi seller arizasi!\n\n"
            f"👤 {data['full_name']}\n"
            f"🏪 {data['shop_name']}\n"
            f"🏙 Shahar: {data.get('city','—')}\n"
            f"📱 {data['phone']}\n\n"
            f"Ko'rish: /admin"
        )
    except Exception:
        pass

    await message.answer(
        f"✅ Arizangiz muvaffaqiyatli qabul qilindi!\n\n"
        f"👤 Ism: {data['full_name']}\n"
        f"📱 Telefon: {data['phone']}\n"
        f"🏙 Shahar: {data.get('city','—')}\n"
        f"🏪 Do'kon: {data['shop_name']}\n"
        f"💳 Karta: **** **** **** {data['card_number'][-4:]}\n\n"
        "⏳ Arizangiz ko'rib chiqiladi va natija sizga xabar qilinadi.",
        reply_markup=main_menu
    )


@router.message(SellerApplicationState.selfie_photo)
async def process_selfie_photo_wrong(message: Message, state: FSMContext):
    await message.answer("❌ Iltimos, selfi rasmini yuboring (foto sifatida).")
