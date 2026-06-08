from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.storage import (
    is_seller, get_seller, get_seller_products, add_product,
    delete_product, update_product, get_seller_orders, update_order_status
)
from app.album import collect
from app.keyboards.seller import main_menu, stars_kb

router = Router()

ORDER_STATUSES = {
    "pending":    "⏳ Kutilmoqda",
    "paid":       "💳 To'lov qilindi",
    "processing": "🔄 Tayyorlanmoqda",
    "shipped":    "🚚 Yo'lda",
    "delivered":  "✅ Yetkazildi",
    "cancelled":  "❌ Bekor qilindi",
}


class AddProductState(StatesGroup):
    name        = State()
    description = State()
    price       = State()
    photo       = State()
    colors      = State()

class EditProductState(StatesGroup):
    waiting_value = State()


def seller_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Mahsulotlarim",    callback_data="seller_products")],
        [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="seller_add_product")],
        [InlineKeyboardButton(text="🛒 Zakazlar",          callback_data="seller_orders")],
        [InlineKeyboardButton(text="🏪 Do'konim",          callback_data="seller_shop_info")],
    ])


# ─── /seller ─────────────────────────────────────────────────────────────────
@router.message(Command("seller"))
async def seller_panel(message: Message):
    if not is_seller(message.from_user.id):
        await message.answer("❌ Siz seller emassiz. Ariza bering: 🏪 Seller bo'lish")
        return
    seller = get_seller(message.from_user.id)
    await message.answer(
        f"🏪 <b>{seller['shop_name']}</b> — Seller Panel",
        reply_markup=seller_menu_kb(), parse_mode="HTML"
    )


# ─── Mahsulotlar ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_products")
async def seller_products(call: CallbackQuery):
    if not is_seller(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    products = get_seller_products(call.from_user.id)
    if not products:
        await call.message.edit_text(
            "📦 Hozircha mahsulot yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Qo'shish",  callback_data="seller_add_product")],
                [InlineKeyboardButton(text="🔙 Orqaga",    callback_data="seller_back")],
            ])
        )
        return
    rows = []
    for p in products:
        rows.append([
            InlineKeyboardButton(text=f"📦 {p['name']} — {p['price']:,} so'm",
                                 callback_data=f"sprod_{p['id']}"),
        ])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")])
    await call.message.edit_text("📦 <b>Mahsulotlaringiz:</b>", parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data.startswith("sprod_"))
async def seller_product_detail(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    from app.storage import get_product_by_id
    p = get_product_by_id(pid)
    if not p or p["seller_id"] != call.from_user.id:
        await call.answer("Topilmadi."); return
    text = (
        f"📦 <b>{p['name']}</b>\n"
        f"📝 {p.get('description','—')}\n"
        f"💰 {p['price']:,} so'm"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish",  callback_data=f"seprod_name_{pid}")],
        [InlineKeyboardButton(text="✏️ Narxini o'zgartirish", callback_data=f"seprod_price_{pid}")],
        [InlineKeyboardButton(text="✏️ Tavsifini o'zgartirish", callback_data=f"seprod_desc_{pid}")],
        [InlineKeyboardButton(text="🗑 O'chirish",             callback_data=f"del_product_{pid}")],
        [InlineKeyboardButton(text="🔙 Orqaga",                callback_data="seller_products")],
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("seprod_"))
async def seller_edit_product_start(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_")   # seprod_name_5
    field = parts[1]
    pid   = int(parts[2])
    labels = {"name": "Nom", "price": "Narx (raqam)", "desc": "Tavsif"}
    await state.set_state(EditProductState.waiting_value)
    await state.update_data(field=field, pid=pid)
    await call.message.answer(f"✏️ Yangi <b>{labels.get(field,'qiymat')}</b>ni kiriting:", parse_mode="HTML")
    await call.answer()


@router.message(EditProductState.waiting_value)
async def seller_edit_product_save(message: Message, state: FSMContext):
    data  = await state.get_data()
    field = data["field"]
    pid   = data["pid"]
    from app.storage import get_product_by_id
    p = get_product_by_id(pid)
    if not p or p["seller_id"] != message.from_user.id:
        await state.clear()
        await message.answer("❌ Ruxsat yo'q.")
        return
    mapping = {"name": "name", "price": "price", "desc": "description"}
    value = int(message.text) if field == "price" and message.text.isdigit() else message.text
    update_product(pid, {mapping[field]: value})
    await state.clear()
    await message.answer("✅ Mahsulot yangilandi!", reply_markup=seller_menu_kb())


@router.callback_query(F.data.startswith("del_product_"))
async def delete_product_handler(call: CallbackQuery):
    pid = int(call.data.split("_")[-1])
    if delete_product(pid, call.from_user.id):
        await call.answer("🗑 O'chirildi!")
        await seller_products(call)
    else:
        await call.answer("Topilmadi.")


# ─── Mahsulot qo'shish ───────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_add_product")
async def start_add_product(call: CallbackQuery, state: FSMContext):
    if not is_seller(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
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
    if not message.text.isdigit():
        await message.answer("❌ Faqat raqam kiriting:"); return
    await state.update_data(price=int(message.text))
    await state.set_state(AddProductState.photo)
    await message.answer(
        "📸 Rasm(lar)ni yuboring — bittasini yoki bir nechtasini birga "
        "(albom) jo'nating.\nRasmsiz qo'shish uchun /skip yozing."
    )


def _build_product(message: Message, data: dict, photos: list) -> dict:
    seller = get_seller(message.from_user.id)
    return {
        "seller_id":   message.from_user.id,
        "shop_name":   seller["shop_name"],
        "name":        data["name"],
        "description": data["description"],
        "price":       data["price"],
        "photos":      photos,
        "colors":      data.get("colors", []),
    }


def _colors_prompt() -> str:
    return (
        "🎨 Mavjud ranglarni kiriting (vergul bilan ajrating) yoki /skip yozing:\n"
        "Masalan: Qizil, Ko'k, Yashil"
    )


# ─── Albom (bir nechta rasm birga) ───────────────────────────────────────────
@router.message(AddProductState.photo, F.media_group_id)
async def product_photo_album(message: Message, state: FSMContext):
    data = await state.get_data()
    key  = (message.from_user.id, message.media_group_id)

    async def done(photos):
        await state.update_data(pending_photos=photos)
        await state.set_state(AddProductState.colors)
        await message.answer(_colors_prompt())

    collect(key, message.photo[-1].file_id, 1.5, done)


# ─── Bitta rasm ──────────────────────────────────────────────────────────────
@router.message(AddProductState.photo, F.photo)
async def product_photo_single(message: Message, state: FSMContext):
    await state.update_data(pending_photos=[message.photo[-1].file_id])
    await state.set_state(AddProductState.colors)
    await message.answer(_colors_prompt())


# ─── Rasmsiz (/skip) ─────────────────────────────────────────────────────────
@router.message(AddProductState.photo, F.text == "/skip")
async def product_photo_skip(message: Message, state: FSMContext):
    await state.update_data(pending_photos=[])
    await state.set_state(AddProductState.colors)
    await message.answer(_colors_prompt())


# ─── Noto'g'ri tur ───────────────────────────────────────────────────────────
@router.message(AddProductState.photo)
async def product_photo_wrong(message: Message, state: FSMContext):
    await message.answer("❌ Rasm yuboring yoki /skip yozing:")


# ─── Rang kiritish ────────────────────────────────────────────────────────────
@router.message(AddProductState.colors, F.text == "/skip")
async def product_colors_skip(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.update_data(colors=[])
    data["colors"] = []
    photos = data.get("pending_photos", [])
    add_product(_build_product(message, data, photos))
    await state.clear()
    photo_info = f"🖼 {len(photos)} ta rasm · " if photos else ""
    await message.answer(
        f"✅ <b>{data['name']}</b> qo'shildi!\n💰 {data['price']:,} so'm · {photo_info}🎨 Rangsiz",
        parse_mode="HTML", reply_markup=seller_menu_kb()
    )


@router.message(AddProductState.colors, F.text)
async def product_colors_enter(message: Message, state: FSMContext):
    text = message.text or ""
    if text.startswith("/") or text.startswith("🛍") or text.startswith("🏪") or text.startswith("❌"):
        await state.clear()
        await message.answer("❌ Mahsulot qo'shish bekor qilindi.", reply_markup=seller_menu_kb())
        return
    colors = [c.strip() for c in text.split(",") if c.strip()]
    if not colors:
        await message.answer("❌ Ranglarni vergul bilan ajratib yozing yoki /skip yozing:")
        return
    data = await state.get_data()
    data["colors"] = colors
    photos = data.get("pending_photos", [])
    add_product(_build_product(message, data, photos))
    await state.clear()
    photo_info = f"🖼 {len(photos)} ta rasm · " if photos else ""
    colors_str = ", ".join(colors)
    await message.answer(
        f"✅ <b>{data['name']}</b> qo'shildi!\n"
        f"💰 {data['price']:,} so'm · {photo_info}🎨 {colors_str}",
        parse_mode="HTML", reply_markup=seller_menu_kb()
    )


# ─── Zakazlar (seller) ───────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_orders")
async def seller_orders_list(call: CallbackQuery):
    if not is_seller(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    orders = get_seller_orders(call.from_user.id)
    if not orders:
        await call.message.edit_text("🛒 Hozircha zakaz yo'q.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")]]
        ))
        return
    rows = []
    for o in orders[-15:]:
        status = ORDER_STATUSES.get(o.get("status",""), "—")
        rows.append([InlineKeyboardButton(
            text=f"#{o['id']} {o.get('product_name','—')} | {status}",
            callback_data=f"sorder_{o['id']}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")])
    await call.message.edit_text("🛒 <b>Zakazlar:</b>", parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data.startswith("sorder_"))
async def seller_order_detail(call: CallbackQuery):
    oid = int(call.data.split("_")[1])
    from app.storage import get_order_by_id
    o = get_order_by_id(oid)
    if not o or o["seller_id"] != call.from_user.id:
        await call.answer("Topilmadi."); return
    status = ORDER_STATUSES.get(o.get("status",""), "—")
    dlv = {
        "pickup": "🚶 O'zi olib ketadi",
        "taxi": "🚕 Taksi pochta (shu bugunoq)",
        "btc": "📦 BTC Pochta", "emu": "🚀 EMU Express", "uzum": "🍊 Uzum Pochta",
    }.get(o.get("delivery",""), o.get("delivery","—"))
    receipt_line = "🧾 Chek: yuborilgan" if o.get("receipt") else "🧾 Chek: yo'q"

    # Xaridor kontakti faqat TAKSI + to'lov tasdiqlangan bo'lsa ko'rinadi.
    # Pickup (o'zi olib ketadi) — danniylar HECH QACHON ko'rsatilmaydi.
    is_pickup = o.get("delivery") == "pickup"
    paid_ok = o.get("status") in ("paid", "processing", "shipped", "delivered")
    unlocked = (not is_pickup) and paid_ok
    if unlocked:
        buyer_block = (
            f"👤 Xaridor: {o.get('buyer_name','—')}\n"
            f"📱 Tel: {o.get('phone','—')}\n"
            f"📍 Manzil: {o.get('address','—')}\n"
        )
    elif is_pickup:
        buyer_block = (
            f"🔒 <b>Xaridor o'zi olib ketadi — ma'lumotlari ko'rsatilmaydi.</b>\n"
            f"   (xaridor do'kon raqamiga o'zi bog'lanadi)\n"
        )
    else:
        buyer_block = (
            f"🔒 <b>Xaridor ma'lumotlari yashirin</b>\n"
            f"   (platforma to'lovi tasdiqlangach ochiladi)\n"
        )
    text = (
        f"🛒 <b>Zakaz #{oid}</b>\n\n"
        f"📦 {o.get('product_name','—')}\n"
        f"💰 {o.get('total',0):,} so'm\n"
        f"{buyer_block}"
        f"🚚 {dlv}\n"
        f"{receipt_line}\n"
        f"📌 Holat: {status}"
    )
    # Holat o'zgartirish tugmalari (to'lovni admin tasdiqlaydi, shu sabab "paid" yo'q)
    if o.get("delivery") == "pickup":
        next_statuses = {
            "pending":    ["cancelled"],
            "paid":       ["processing","cancelled"],
            "processing": ["delivered"],   # o'zi olib ketadi — to'g'ridan topshirildi
        }
    else:
        next_statuses = {
            "pending":    ["cancelled"],
            "paid":       ["processing","cancelled"],
            "processing": ["shipped"],
            "shipped":    ["delivered"],
        }
    rows = []
    if o.get("receipt"):
        rows.append([InlineKeyboardButton(text="🧾 Chekni ko'rish", callback_data=f"vrcpt_{oid}")])
    for s in next_statuses.get(o.get("status",""), []):
        rows.append([InlineKeyboardButton(
            text=ORDER_STATUSES[s],
            callback_data=f"ostatus_{oid}_{s}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_orders")])
    await call.message.edit_text(text, parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data.startswith("vrcpt_"))
async def seller_view_receipt(call: CallbackQuery):
    oid = int(call.data.split("_")[1])
    from app.storage import get_order_by_id
    o = get_order_by_id(oid)
    if not o or o["seller_id"] != call.from_user.id:
        await call.answer("Topilmadi."); return
    if not o.get("receipt"):
        await call.answer("Chek yo'q.", show_alert=True); return
    try:
        await call.message.answer_photo(o["receipt"], caption=f"🧾 Zakaz #{oid} cheki")
    except Exception:
        await call.answer("Chekni ko'rsatib bo'lmadi.", show_alert=True)
    await call.answer()


@router.callback_query(F.data.startswith("ostatus_"))
async def update_order(call: CallbackQuery):
    parts  = call.data.split("_")
    oid    = int(parts[1])
    status = parts[2]
    from app.storage import get_order_by_id
    o = get_order_by_id(oid)
    if not o or o["seller_id"] != call.from_user.id:
        await call.answer("Ruxsat yo'q."); return
    update_order_status(oid, status)
    status_label = ORDER_STATUSES[status]
    await call.answer(f"✅ Holat: {status_label}")

    # Xaridorga xabar
    try:
        from app.bot.bot import bot
        msg = (
            f"📦 <b>Zakaz #{oid} holati yangilandi!</b>\n\n"
            f"📌 Yangi holat: {status_label}\n"
            f"📦 {o.get('product_name','—')}"
        )
        if status == "delivered":
            # Baholash tugmasini qo'shish
            await bot.send_message(
                o["buyer_id"], msg + "\n\n⭐ Sellerni baholang:",
                parse_mode="HTML",
                reply_markup=stars_kb(o["seller_id"], oid)
            )
        else:
            await bot.send_message(o["buyer_id"], msg, parse_mode="HTML")
    except Exception:
        pass

    await seller_order_detail(call)


# ─── Do'kon info ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_shop_info")
async def seller_shop_info(call: CallbackQuery):
    seller = get_seller(call.from_user.id)
    if not seller:
        await call.answer("Seller topilmadi."); return
    from app.storage import get_seller_rating
    rating, cnt = get_seller_rating(call.from_user.id)
    products = get_seller_products(call.from_user.id)
    text = (
        f"🏪 <b>{seller['shop_name']}</b>\n\n"
        f"👤 {seller['full_name']}\n"
        f"📱 {seller['phone']}\n"
        f"💳 **** {seller.get('card_number','')[-4:]}\n"
        f"📦 Mahsulotlar: {len(products)} ta\n"
        f"⭐ Reyting: {rating} ({cnt} ta baho)"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")]]
    ))
    await call.answer()


@router.callback_query(F.data == "seller_back")
async def seller_back(call: CallbackQuery):
    seller = get_seller(call.from_user.id)
    if not seller:
        await call.answer(); return
    await call.message.edit_text(
        f"🏪 <b>{seller['shop_name']}</b> — Seller Panel",
        reply_markup=seller_menu_kb(), parse_mode="HTML"
    )
    await call.answer()


# ─── /orders (buyruq orqali) ─────────────────────────────────────────────────
@router.message(Command("orders"))
async def orders_cmd(message: Message):
    if not is_seller(message.from_user.id):
        await message.answer("Siz seller emassiz."); return
    orders = get_seller_orders(message.from_user.id)
    if not orders:
        await message.answer("🛒 Hozircha zakaz yo'q."); return
    text = "🛒 <b>Zakazlaringiz:</b>\n\n"
    for o in orders[-10:]:
        status = ORDER_STATUSES.get(o.get("status",""), "—")
        text += f"<b>#{o['id']}</b> — {o.get('product_name','—')} | {status}\n"
    await message.answer(text, parse_mode="HTML")
