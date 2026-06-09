from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.storage import (
    is_seller, get_seller, get_seller_products, add_product,
    delete_product, update_product, get_seller_orders, update_order_status,
    to_int, PRODUCT_CATEGORIES,
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
    category    = State()   # birinchi qadam: kategoriya tanlash
    name        = State()
    description = State()
    price       = State()
    old_price   = State()   # ixtiyoriy chegirma (eski narx)
    photo       = State()
    colors      = State()
    preview     = State()   # saqlashdan oldin ko'rib chiqish/tasdiq

class EditProductState(StatesGroup):
    waiting_value = State()


def seller_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 Mahsulotlarim",    callback_data="seller_products")],
        [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="seller_add_product")],
        [InlineKeyboardButton(text="🛒 Buyurtmalar",          callback_data="seller_orders")],
        [InlineKeyboardButton(text="🏪 Do'konim",          callback_data="seller_shop_info")],
    ])


# ─── /seller ─────────────────────────────────────────────────────────────────
@router.message(Command("seller"))
async def seller_panel(message: Message):
    if not is_seller(message.from_user.id):
        await message.answer("❌ Siz sotuvchi emassiz. Ariza bering: 🏪 Sotuvchi bo'lish")
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
    cat_line = f"🗂 {p['category']}\n" if p.get("category") else ""
    text = (
        f"📦 <b>{p['name']}</b>\n"
        f"{cat_line}"
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
    txt = (message.text or "").strip()
    if not txt:
        await message.answer("❌ Matn ko'rinishida kiriting:"); return
    mapping = {"name": "name", "price": "price", "desc": "description"}
    if field == "price":
        value = to_int(txt, -1)
        if value <= 0:
            await message.answer("❌ Narxni to'g'ri kiriting (masalan: 150000 yoki 150 000):"); return
    else:
        value = txt
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
def _category_kb() -> InlineKeyboardMarkup:
    """Kategoriya tanlash tugmalari (har qatorda 2 ta)."""
    rows = []
    for i in range(0, len(PRODUCT_CATEGORIES), 2):
        row = [
            InlineKeyboardButton(text=PRODUCT_CATEGORIES[j], callback_data=f"apcat_{j}")
            for j in range(i, min(i + 2, len(PRODUCT_CATEGORIES)))
        ]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "seller_add_product")
async def start_add_product(call: CallbackQuery, state: FSMContext):
    if not is_seller(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    await state.set_state(AddProductState.category)
    await call.message.answer("🗂 Mahsulot kategoriyasini tanlang:", reply_markup=_category_kb())
    await call.answer()


@router.callback_query(AddProductState.category, F.data.startswith("apcat_"))
async def product_category(call: CallbackQuery, state: FSMContext):
    idx = int(call.data.split("_")[1])
    if not (0 <= idx < len(PRODUCT_CATEGORIES)):
        await call.answer("Noto'g'ri kategoriya."); return
    category = PRODUCT_CATEGORIES[idx]
    await state.update_data(category=category)
    await state.set_state(AddProductState.name)
    try:
        await call.message.edit_text(f"🗂 Kategoriya: <b>{category}</b>", parse_mode="HTML")
    except Exception:
        pass
    await call.message.answer("📦 Mahsulot nomini kiriting:")
    await call.answer()


# ─── Mahsulot qo'shishni bo'lib yuboruvchi tugma/buyruqlarda AVTOMAT to'xtatish ──
# Foydalanuvchi nom/tavsif/narx/rasm/rang so'ralganda /start yoki menyu tugmasini
# bossa — uni input deb qabul qilmaymiz, jarayonni to'xtatamiz.
MENU_BUTTONS = {
    "🛍 Bozor", "🔎 Qidirish", "🏪 Sotuvchi bo'lish", "📦 Buyurtmalarim",
    "👤 Profil", "📞 Aloqa", "🛍 Do'kon (ilova)", "❌ Bekor qilish",
}

ADD_PRODUCT_STATES = StateFilter(
    AddProductState.category, AddProductState.name, AddProductState.description,
    AddProductState.price, AddProductState.old_price,
    AddProductState.photo, AddProductState.colors,
    AddProductState.preview,
)

# Rasm bosqichi uchun matn (bir necha joyda ishlatiladi)
_PHOTO_PROMPT = (
    "📸 Rasm(lar)ni yuboring — bittasini yoki bir nechtasini birga "
    "(albom) jo'nating.\nRasmsiz qo'shish uchun /skip yozing."
)


# /skip — rasm/rang bosqichida atayin ishlatiladi, uni to'xtatmaymiz
@router.message(ADD_PRODUCT_STATES, F.text.startswith("/"), F.text != "/skip")
async def addprod_interrupt_command(message: Message, state: FSMContext):
    # /start bo'lsa — odatdagidek tozalab, salomlashamiz
    if (message.text or "").startswith("/start"):
        from app.handlers.start import cmd_start
        await cmd_start(message, state)
        return
    await state.clear()
    await message.answer("⛔️ Mahsulot qo'shish to'xtatildi.", reply_markup=main_menu)


@router.message(ADD_PRODUCT_STATES, F.text.in_(MENU_BUTTONS))
async def addprod_interrupt_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⛔️ Mahsulot qo'shish to'xtatildi.", reply_markup=main_menu)


@router.message(AddProductState.name)
async def product_name(message: Message, state: FSMContext):
    if not (message.text or "").strip():
        await message.answer("❌ Mahsulot nomini matn ko'rinishida kiriting:"); return
    await state.update_data(name=message.text.strip())
    await state.set_state(AddProductState.description)
    await message.answer("📝 Tavsif kiriting (yoki /skip — tavsifsiz davom etish):")


@router.message(AddProductState.description, F.text == "/skip")
async def product_description_skip(message: Message, state: FSMContext):
    await state.update_data(description="")
    await state.set_state(AddProductState.price)
    await message.answer("💰 Narxini kiriting (masalan: 150000 yoki 150 000):")


@router.message(AddProductState.description)
async def product_description(message: Message, state: FSMContext):
    if not (message.text or "").strip():
        await message.answer("❌ Tavsifni matn ko'rinishida kiriting yoki /skip yozing:"); return
    await state.update_data(description=message.text.strip())
    await state.set_state(AddProductState.price)
    await message.answer("💰 Narxini kiriting (masalan: 150000 yoki 150 000):")


@router.message(AddProductState.price)
async def product_price(message: Message, state: FSMContext):
    price = to_int(message.text, -1)
    if price <= 0:
        await message.answer("❌ Narxni to'g'ri kiriting (masalan: 150000 yoki 150 000):"); return
    await state.update_data(price=price)
    await state.set_state(AddProductState.old_price)
    await message.answer(
        "🏷 <b>Chegirma (ixtiyoriy)</b>\n"
        "Chegirma ko'rsatmoqchi bo'lsangiz — <b>eski (chegirmasiz) narxni</b> kiriting.\n"
        f"U hozirgi narxdan ({price:,} so'm) yuqori bo'lishi kerak.\n\n"
        "Chegirmasiz davom etish uchun /skip yozing.",
        parse_mode="HTML"
    )


@router.message(AddProductState.old_price, F.text == "/skip")
async def product_old_price_skip(message: Message, state: FSMContext):
    await state.update_data(old_price=None)
    await state.set_state(AddProductState.photo)
    await message.answer(_PHOTO_PROMPT)


@router.message(AddProductState.old_price)
async def product_old_price(message: Message, state: FSMContext):
    data  = await state.get_data()
    price = data.get("price", 0)
    old   = to_int(message.text, -1)
    if old <= 0:
        await message.answer("❌ Eski narxni to'g'ri kiriting yoki /skip yozing:"); return
    if old <= price:
        await message.answer(
            f"❌ Eski narx hozirgi narxdan ({price:,} so'm) yuqori bo'lishi kerak. "
            "Qayta kiriting yoki /skip yozing:"
        ); return
    await state.update_data(old_price=old)
    await state.set_state(AddProductState.photo)
    await message.answer(_PHOTO_PROMPT)


def _build_product(user_id: int, data: dict, photos: list) -> dict:
    seller = get_seller(user_id)
    return {
        "seller_id":   user_id,
        "shop_name":   seller["shop_name"],
        "category":    data.get("category", ""),
        "name":        data["name"],
        "description": data.get("description", ""),
        "price":       data["price"],
        "old_price":   data.get("old_price"),
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
    await state.update_data(colors=[])
    await _show_preview(message, state)


@router.message(AddProductState.colors, F.text)
async def product_colors_enter(message: Message, state: FSMContext):
    colors = [c.strip() for c in (message.text or "").split(",") if c.strip()]
    if not colors:
        await message.answer("❌ Ranglarni vergul bilan ajratib yozing yoki /skip yozing:")
        return
    await state.update_data(colors=colors)
    await _show_preview(message, state)


# ─── Saqlashdan oldin ko'rib chiqish (preview) ───────────────────────────────
def _preview_text(data: dict) -> str:
    price = data.get("price", 0)
    old   = data.get("old_price")
    lines = ["👀 <b>Mahsulot shunday chiqadi:</b>\n", f"📦 <b>{data.get('name','')}</b>"]
    if data.get("category"):
        lines.append(f"🗂 {data['category']}")
    price_line = f"💰 <b>{price:,} so'm</b>"
    if old and old > price:
        pct = round((old - price) / old * 100)
        price_line += f"  <b>↓{pct}%</b>"
    lines.append(price_line)
    if old and old > price:
        lines.append(f"<s>{old:,} so'm</s>")
    desc = data.get("description")
    if desc:
        lines.append(f"\n📝 {desc}")
    colors = data.get("colors") or []
    if colors:
        lines.append(f"\n🎨 Ranglar: {', '.join(colors)}")
    photos = data.get("pending_photos") or []
    lines.append(f"\n🖼 {len(photos)} ta rasm" if photos else "\n🖼 Rasmsiz")
    return "\n".join(lines)


def _preview_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Saqlash",       callback_data="ap_save")],
        [InlineKeyboardButton(text="❌ Bekor qilish",  callback_data="ap_cancel")],
    ])


async def _show_preview(message: Message, state: FSMContext):
    await state.set_state(AddProductState.preview)
    data   = await state.get_data()
    text   = _preview_text(data)
    photos = data.get("pending_photos") or []
    if photos:
        try:
            await message.answer_photo(photos[0], caption=text, parse_mode="HTML", reply_markup=_preview_kb())
            return
        except Exception:
            pass
    await message.answer(text, parse_mode="HTML", reply_markup=_preview_kb())


@router.callback_query(AddProductState.preview, F.data == "ap_save")
async def product_preview_save(call: CallbackQuery, state: FSMContext):
    data   = await state.get_data()
    photos = data.get("pending_photos", [])
    add_product(_build_product(call.from_user.id, data, photos))
    await state.clear()
    photo_info = f"🖼 {len(photos)} ta rasm · " if photos else ""
    colors     = data.get("colors") or []
    colors_str = ", ".join(colors) if colors else "Rangsiz"
    disc_line  = ""
    old = data.get("old_price")
    if old and old > data.get("price", 0):
        disc_line = f"\n🏷 Chegirma: <s>{old:,}</s> → {data['price']:,} so'm"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yana mahsulot qo'shish", callback_data="seller_add_product")],
        [InlineKeyboardButton(text="📦 Mahsulotlarim",          callback_data="seller_products")],
    ])
    await call.message.answer(
        f"✅ <b>{data['name']}</b> qo'shildi!\n"
        f"💰 {data['price']:,} so'm · {photo_info}🎨 {colors_str}{disc_line}",
        parse_mode="HTML", reply_markup=kb
    )
    await call.answer("Saqlandi ✅")


@router.callback_query(AddProductState.preview, F.data == "ap_cancel")
async def product_preview_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.answer("❌ Mahsulot qo'shish bekor qilindi.", reply_markup=main_menu)
    await call.answer()


# ─── Buyurtmalar (seller) ───────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_orders")
async def seller_orders_list(call: CallbackQuery):
    if not is_seller(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    orders = get_seller_orders(call.from_user.id)
    if not orders:
        await call.message.edit_text("🛒 Hozircha buyurtma yo'q.", reply_markup=InlineKeyboardMarkup(
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
    await call.message.edit_text("🛒 <b>Buyurtmalar:</b>", parse_mode="HTML",
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
    # Pickup (o'zi olib ketadi) — ma'lumotlar HECH QACHON ko'rsatilmaydi.
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
        f"🛒 <b>Buyurtma #{oid}</b>\n\n"
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
        await call.message.answer_photo(o["receipt"], caption=f"🧾 Buyurtma #{oid} cheki")
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
            f"📦 <b>Buyurtma #{oid} holati yangilandi!</b>\n\n"
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
        await message.answer("🛒 Hozircha buyurtma yo'q."); return
    text = "🛒 <b>Buyurtmalaringiz:</b>\n\n"
    for o in orders[-10:]:
        status = ORDER_STATUSES.get(o.get("status",""), "—")
        text += f"<b>#{o['id']}</b> — {o.get('product_name','—')} | {status}\n"
    await message.answer(text, parse_mode="HTML")
