from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.storage import is_seller, get_seller, get_seller_products, add_product, delete_product

router = Router()


class AddProductState(StatesGroup):
    name        = State()
    description = State()
    price       = State()
    photo       = State()


def seller_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Mahsulotlarim",    callback_data="seller_products")],
        [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="seller_add_product")],
        [InlineKeyboardButton(text="🏪 Do'konim",          callback_data="seller_shop_info")],
    ])


# ─── /seller ─────────────────────────────────────────────────────────────────
@router.message(Command("seller"))
async def seller_panel(message: Message, state: FSMContext):
    await state.clear()                          # ← aktiv state ni tozalaymiz
    if not is_seller(message.from_user.id):
        await message.answer("❌ Siz seller emassiz. Avval ariza bering: 🏪 Seller bo'lish")
        return
    seller = get_seller(message.from_user.id)
    await message.answer(
        f"🏪 <b>{seller['shop_name']}</b> — Seller Panel\n\n"
        f"Quyidagi bo'limlardan birini tanlang:",
        reply_markup=seller_menu_kb(),
        parse_mode="HTML"
    )


# ─── Bekor qilish (ixtiyoriy state dan) ──────────────────────────────────────
@router.message(
    StateFilter(AddProductState.name, AddProductState.description,
                AddProductState.price, AddProductState.photo),
    F.text == "❌ Bekor qilish"
)
async def cancel_add_product(message: Message, state: FSMContext):
    await state.clear()
    from app.keyboards.seller import main_menu
    await message.answer("Amaliyot bekor qilindi.", reply_markup=main_menu)


# ─── /start yoki /admin kelsa — state ni tozalaymiz ─────────────────────────
@router.message(
    StateFilter(AddProductState.name, AddProductState.description,
                AddProductState.price, AddProductState.photo),
    F.text.startswith("/")
)
async def cancel_on_command(message: Message, state: FSMContext):
    """Seller mahsulot qo'shayotganda buyruq yuborganida state ni tozalab, buyruqni o'tkazib yuborish"""
    await state.clear()
    # Buyruqni qayta jo'natish — dispatcher o'zi hal qiladi
    # Lekin biz shunchaki state ni tozalaymiz, xabar qoladi
    await message.answer("⚠️ Mahsulot qo'shish bekor qilindi.")


# ─── Mahsulotlar ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_products")
async def seller_products(call: CallbackQuery):
    if not is_seller(call.from_user.id):
        await call.answer("Siz seller emassiz.")
        return
    products = get_seller_products(call.from_user.id)
    if not products:
        await call.message.edit_text(
            "📦 Hozircha mahsulot yo'q.\n\nQo'shish uchun '➕ Mahsulot qo'shish' tugmasini bosing.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Qo'shish",  callback_data="seller_add_product")],
                [InlineKeyboardButton(text="🔙 Orqaga",    callback_data="seller_back")],
            ])
        )
        return

    text = "📦 <b>Mahsulotlaringiz:</b>\n\n"
    kb_rows = []
    for p in products:
        text += f"• {p['name']} — {p['price']:,} so'm\n"
        kb_rows.append([InlineKeyboardButton(
            text=f"🗑 {p['name']} o'chirish",
            callback_data=f"del_product_{p['id']}"
        )])
    kb_rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")])
    await call.message.edit_text(text, parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))
    await call.answer()


@router.callback_query(F.data.startswith("del_product_"))
async def delete_product_handler(call: CallbackQuery):
    product_id = int(call.data.split("_")[-1])
    if delete_product(product_id, call.from_user.id):
        await call.answer("🗑 Mahsulot o'chirildi!")
        await seller_products(call)
    else:
        await call.answer("Mahsulot topilmadi.")


# ─── Mahsulot qo'shish ───────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_add_product")
async def start_add_product(call: CallbackQuery, state: FSMContext):
    if not is_seller(call.from_user.id):
        await call.answer("Siz seller emassiz.")
        return
    await state.set_state(AddProductState.name)
    await call.message.answer("📦 Mahsulot nomini kiriting:")
    await call.answer()


@router.message(AddProductState.name)
async def product_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AddProductState.description)
    await message.answer("📝 Tavsif kiriting:")


@router.message(AddProductState.description)
async def product_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AddProductState.price)
    await message.answer("💰 Narxini kiriting (so'mda, faqat raqam):")


@router.message(AddProductState.price)
async def product_price(message: Message, state: FSMContext):
    # Raqam emas → xato
    if not message.text or not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting (masalan: 50000):")
        return
    await state.update_data(price=int(message.text))
    await state.set_state(AddProductState.photo)
    await message.answer("📸 Mahsulot rasmini yuboring (yoki /skip yozing):")


@router.message(AddProductState.photo)
async def product_photo(message: Message, state: FSMContext):
    data   = await state.get_data()
    seller = get_seller(message.from_user.id)

    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.strip() == "/skip":
        photo_id = None
    else:
        await message.answer("❌ Rasm yuboring yoki /skip yozing:")
        return

    add_product({
        "seller_id":   message.from_user.id,
        "shop_name":   seller["shop_name"],
        "name":        data["name"],
        "description": data["description"],
        "price":       data["price"],
        "photo":       photo_id,
    })
    await state.clear()
    await message.answer(
        f"✅ <b>{data['name']}</b> mahsuloti qo'shildi!\n\n"
        f"💰 Narx: {data['price']:,} so'm",
        parse_mode="HTML",
        reply_markup=seller_menu_kb()
    )


# ─── Do'kon ma'lumoti ────────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_shop_info")
async def seller_shop_info(call: CallbackQuery):
    seller = get_seller(call.from_user.id)
    if not seller:
        await call.answer("Seller topilmadi.")
        return
    products = get_seller_products(call.from_user.id)
    text = (
        f"🏪 <b>{seller['shop_name']}</b>\n\n"
        f"👤 {seller['full_name']}\n"
        f"📱 {seller['phone']}\n"
        f"📦 Mahsulotlar: {len(products)} ta"
    )
    await call.message.edit_text(text, parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                      [InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")]
                                  ]))
    await call.answer()


# ─── Orqaga ──────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_back")
async def seller_back(call: CallbackQuery):
    seller = get_seller(call.from_user.id)
    if not seller:
        await call.answer()
        return
    await call.message.edit_text(
        f"🏪 <b>{seller['shop_name']}</b> — Seller Panel\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=seller_menu_kb(),
        parse_mode="HTML"
    )
    await call.answer()
