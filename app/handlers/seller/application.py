from aiogram import Router
from aiogram import F
from aiogram.types import Message, ContentType
from aiogram.fsm.context import FSMContext

from app.states.seller_application import SellerApplicationState
from app.keyboards.seller import cancel_keyboard, phone_keyboard, main_menu

router = Router()


@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Amaliyot bekor qilindi.",
        reply_markup=main_menu
    )


@router.message(F.text == "🏪 Seller bo'lish")
async def seller_application_start(message: Message, state: FSMContext):
    await state.set_state(SellerApplicationState.full_name)
    await message.answer(
        "📝 Seller arizasini boshlaylik!\n\n"
        "1/6 — To'liq ismingizni kiriting (F.I.Sh):",
        reply_markup=cancel_keyboard
    )


@router.message(SellerApplicationState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(SellerApplicationState.phone)
    await message.answer(
        "2/6 — Telefon raqamingizni yuboring:",
        reply_markup=phone_keyboard
    )


@router.message(
    SellerApplicationState.phone,
    F.content_type == ContentType.CONTACT
)
async def process_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await state.set_state(SellerApplicationState.shop_name)
    await message.answer(
        "3/6 — Do'koningiz nomini kiriting:",
        reply_markup=cancel_keyboard
    )


@router.message(SellerApplicationState.phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(SellerApplicationState.shop_name)
    await message.answer(
        "3/6 — Do'koningiz nomini kiriting:",
        reply_markup=cancel_keyboard
    )


@router.message(SellerApplicationState.shop_name)
async def process_shop_name(message: Message, state: FSMContext):
    await state.update_data(shop_name=message.text)
    await state.set_state(SellerApplicationState.card_number)
    await message.answer(
        "4/6 — Karta raqamingizni kiriting (16 raqam):",
        reply_markup=cancel_keyboard
    )


@router.message(SellerApplicationState.card_number)
async def process_card_number(message: Message, state: FSMContext):
    card = message.text.replace(" ", "").replace("-", "")
    if not card.isdigit() or len(card) != 16:
        await message.answer(
            "❌ Noto'g'ri karta raqami. 16 ta raqam kiriting:"
        )
        return
    await state.update_data(card_number=card)
    await state.set_state(SellerApplicationState.passport_photo)
    await message.answer(
        "5/6 — Pasportingiz rasmini yuboring (birinchi sahifa):",
        reply_markup=cancel_keyboard
    )


@router.message(
    SellerApplicationState.passport_photo,
    F.content_type == ContentType.PHOTO
)
async def process_passport_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(passport_photo=photo_id)
    await state.set_state(SellerApplicationState.selfie_photo)
    await message.answer(
        "6/6 — Pasportingiz bilan selfi rasmini yuboring:",
        reply_markup=cancel_keyboard
    )


@router.message(SellerApplicationState.passport_photo)
async def process_passport_photo_wrong(message: Message, state: FSMContext):
    await message.answer("❌ Iltimos, rasm yuboring (foto sifatida).")


@router.message(
    SellerApplicationState.selfie_photo,
    F.content_type == ContentType.PHOTO
)
async def process_selfie_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(selfie_photo=photo_id)

    data = await state.get_data()
    await state.clear()

    await message.answer(
        "✅ Arizangiz muvaffaqiyatli qabul qilindi!\n\n"
        f"👤 Ism: {data['full_name']}\n"
        f"📱 Telefon: {data['phone']}\n"
        f"🏪 Do'kon: {data['shop_name']}\n"
        f"💳 Karta: **** **** **** {data['card_number'][-4:]}\n\n"
        "⏳ Arizangiz ko'rib chiqiladi va natija sizga xabar qilinadi.",
        reply_markup=main_menu
    )


@router.message(SellerApplicationState.selfie_photo)
async def process_selfie_photo_wrong(message: Message, state: FSMContext):
    await message.answer("❌ Iltimos, selfi rasmini yuboring (foto sifatida).")
