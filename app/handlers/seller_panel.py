from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.storage import (
    is_seller, get_seller, get_sellers, get_seller_products, add_product,
    delete_product, update_product, update_seller, get_seller_orders, update_order_status,
    to_int, get_owner_id, get_shop_seller, is_shop_member, get_assistants,
    add_assistant, remove_assistant, get_user, set_user_field, find_user_id_by_phone,
)
from app.album import collect
from app.keyboards.seller import main_menu, seller_main_menu, stars_kb, cancel_keyboard
from app.ui import money, divider, product_emoji, product_sort_key, product_group_label

router = Router()


async def _ack(call: CallbackQuery):
    """Tugma spinnerini DARHOL o'chiradi — og'ir ishlar (fayl o'qish, xabar
    yuborish) tugashini kutmasdan. Handler boshqa handlerdan qayta chaqirilganda
    callback allaqachon javoblangan bo'lishi mumkin — shunda xato bermaydi."""
    try:
        await call.answer()
    except Exception:
        pass


ORDER_STATUSES = {
    "pending":    "⏳ Kutilmoqda",
    "paid":       "💳 To'lov qilindi",
    "processing": "🔄 Tayyorlanmoqda",
    "shipped":    "🚚 Yo'lda",
    "delivered":  "✅ Yetkazildi",
    "cancelled":  "❌ Bekor qilindi",
}

# Seller buyurtma kartochkasidagi harakat tugmalari uchun maxsus yozuvlar
# (holat nomidan farqli — masalan "Yo'lda" o'rniga "Kurierga berdim").
SELLER_ACTION_LABELS = {
    "shipped": "🚚 Kurierga berdim",
}


class AddProductState(StatesGroup):
    name        = State()
    description = State()
    price       = State()
    stock       = State()   # ombordagi son (yoki /skip = cheksiz)
    photo       = State()
    colors      = State()
    video       = State()   # ixtiyoriy qisqa video (yoki /skip)
    preview     = State()   # saqlashdan oldin ko'rib chiqish/tasdiq

class EditProductState(StatesGroup):
    waiting_value = State()
    waiting_photo = State()
    waiting_video = State()


class EditCardState(StatesGroup):
    waiting_value = State()


class AddAssistantState(StatesGroup):
    waiting_user = State()


def seller_menu_kb(user_id: int | None = None):
    rows = [
        [InlineKeyboardButton(text="📦 Mahsulotlarim",    callback_data="seller_products")],
        [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="seller_add_product")],
        [InlineKeyboardButton(text="🛒 Buyurtmalar",          callback_data="seller_orders")],
        [InlineKeyboardButton(text="📊 Statistika",           callback_data="seller_stats")],
    ]
    # Yordamchilarni faqat do'kon egasi boshqaradi
    if user_id is not None and is_seller(user_id):
        rows.append([InlineKeyboardButton(text="👥 Yordamchilar", callback_data="seller_assistants")])
    rows.append([InlineKeyboardButton(text="🏪 Do'konim", callback_data="seller_shop_info")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── /seller ─────────────────────────────────────────────────────────────────
@router.message(Command("seller"))
@router.message(F.text == "🛒 Sotuvchi paneli")
async def seller_panel(message: Message):
    if not is_shop_member(message.from_user.id):
        await message.answer("❌ Siz sotuvchi emassiz. Ariza bering: 🏪 Sotuvchi bo'lish")
        return
    seller = get_shop_seller(message.from_user.id)
    await message.answer(
        f"🏪 <b>{seller['shop_name']}</b> — Seller Panel",
        reply_markup=seller_menu_kb(message.from_user.id), parse_mode="HTML"
    )


# ─── Shahrim sellerlari (shahar bo'yicha sellerlar ro'yxati) ─────────────────
@router.message(F.text == "👥 Shahrim sellerlari")
async def my_city_sellers(message: Message):
    if not is_shop_member(message.from_user.id):
        await message.answer("❌ Siz sotuvchi emassiz.")
        return
    me = get_shop_seller(message.from_user.id)
    city = (me.get("city") or "").strip()
    if not city:
        await message.answer(
            "🏙 Shahringiz aniqlanmadi. Admin bilan bog'laning.",
            reply_markup=seller_main_menu
        )
        return

    peers = [s for s in get_sellers().values() if (s.get("city") or "").strip() == city]
    if not peers:
        await message.answer(
            f"🏙 <b>{city}</b> shahrida hozircha boshqa sotuvchi yo'q.",
            parse_mode="HTML", reply_markup=seller_main_menu
        )
        return

    text = f"👥 <b>{city}</b> shahridagi sotuvchilar ({len(peers)} ta):\n\n"
    for s in peers:
        text += (
            f"🏪 {s.get('shop_name','—')}\n"
            f"   👤 {s.get('full_name','—')}\n"
            f"   📞 {s.get('phone','—')}\n\n"
        )
    await message.answer(text, parse_mode="HTML", reply_markup=seller_main_menu)


# ─── Mahsulotlar ─────────────────────────────────────────────────────────────
# Bitta sahifadagi mahsulotlar soni. Telegram juda ko'p tugmani qabul qilmaydi
# (mahsulot 100 dan oshsa ro'yxat ochilmay qoladi) — shuning uchun sahifalaymiz.
_SELLER_PER_PAGE = 40


def _seller_products_content(owner_id: int, page: int):
    """(matn, klaviatura) — sotuvchi mahsulotlarining `page`-sahifasi."""
    products = get_seller_products(owner_id)
    if not products:
        return (
            "📦 Hozircha mahsulot yo'q.",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Qo'shish",  callback_data="seller_add_product")],
                [InlineKeyboardButton(text="🔙 Orqaga",    callback_data="seller_back")],
            ])
        )
    # Kategoriya bo'yicha guruhlab, har guruh ichida arzonidan qimmatiga.
    products = sorted(products, key=lambda p: (product_sort_key(p), p.get("price", 0)))
    total = len(products)
    pages = max(1, (total + _SELLER_PER_PAGE - 1) // _SELLER_PER_PAGE)
    page = max(0, min(page, pages - 1))
    start = page * _SELLER_PER_PAGE
    rows = []
    cur_group = object()
    for p in products[start:start + _SELLER_PER_PAGE]:
        grp = product_sort_key(p)
        if grp != cur_group:
            cur_group = grp
            rows.append([InlineKeyboardButton(
                text=f"➖  {product_emoji(p)} {product_group_label(p)}",
                callback_data="noop"
            )])
        finished = "❌ " if p.get("is_finished") else ""
        rows.append([
            InlineKeyboardButton(text=f"{finished}{product_emoji(p)} {p['name']} — {p['price']:,} so'm",
                                 callback_data=f"sprod_{p['id']}"),
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"sprodpg_{page-1}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"sprodpg_{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")])
    page_info = f"  (sahifa {page+1}/{pages})" if pages > 1 else ""
    return f"📦 <b>Mahsulotlaringiz</b> — {total} ta{page_info}:", InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "seller_products")
async def seller_products(call: CallbackQuery):
    if not is_shop_member(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    await _ack(call)
    text, kb = _seller_products_content(get_owner_id(call.from_user.id), 0)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("sprodpg_"))
async def seller_products_page(call: CallbackQuery):
    if not is_shop_member(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    await _ack(call)
    page = int(call.data.split("_")[1])
    text, kb = _seller_products_content(get_owner_id(call.from_user.id), page)
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("sprod_"))
async def seller_product_detail(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    from app.storage import get_product_by_id
    p = get_product_by_id(pid)
    if not p or p["seller_id"] != get_owner_id(call.from_user.id):
        await call.answer("Topilmadi."); return
    await _ack(call)
    finished = bool(p.get("is_finished"))
    status_line = "❌ Tugagan" if finished else "✅ Sotuvda"
    video_line = "\n🎬 Video: bor" if p.get("video") else ""
    stock = p.get("stock")
    stock_line = f"\n📦 Omborda: {to_int(stock, 0)} dona" if stock is not None else "\n📦 Ombor: cheksiz"
    text = (
        f"📦 <b>{p['name']}</b>\n"
        f"📝 {p.get('description','—')}\n"
        f"💰 {p['price']:,} so'm\n"
        f"📌 Holati: {status_line}"
        f"{stock_line}"
        f"{video_line}"
    )
    toggle_text = "✅ Bor deb belgilash" if finished else "❌ Tugadi deb belgilash"
    vid_btn = "🎬 Videoni o'zgartirish" if p.get("video") else "🎬 Video qo'shish"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish",  callback_data=f"seprod_name_{pid}")],
        [InlineKeyboardButton(text="✏️ Narxini o'zgartirish", callback_data=f"seprod_price_{pid}")],
        [InlineKeyboardButton(text="✏️ Tavsifini o'zgartirish", callback_data=f"seprod_desc_{pid}")],
        [InlineKeyboardButton(text="📦 Zaxira (sonini) o'zgartirish", callback_data=f"seprod_stock_{pid}")],
        [InlineKeyboardButton(text="🖼 Rasmlarni o'zgartirish", callback_data=f"sphoto_{pid}")],
        [InlineKeyboardButton(text=vid_btn,                     callback_data=f"svideo_{pid}")],
        [InlineKeyboardButton(text=toggle_text,                callback_data=f"pfin_{pid}")],
        [InlineKeyboardButton(text="🗑 O'chirish",             callback_data=f"del_product_{pid}")],
        [InlineKeyboardButton(text="🔙 Orqaga",                callback_data="seller_products")],
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("seprod_"))
async def seller_edit_product_start(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_")   # seprod_name_5
    field = parts[1]
    pid   = int(parts[2])
    await _ack(call)
    labels = {"name": "Nom", "price": "Narx (raqam)", "desc": "Tavsif",
              "stock": "Ombordagi son (raqam)"}
    await state.set_state(EditProductState.waiting_value)
    await state.update_data(field=field, pid=pid)
    hint = ""
    if field == "stock":
        hint = "\n(0 — tugagan; cheksiz qilish uchun «cheksiz» deb yozing)"
    await call.message.answer(
        f"✏️ Yangi <b>{labels.get(field,'qiymat')}</b>ni kiriting:{hint}",
        parse_mode="HTML")


@router.message(EditProductState.waiting_value)
async def seller_edit_product_save(message: Message, state: FSMContext):
    data  = await state.get_data()
    field = data["field"]
    pid   = data["pid"]
    from app.storage import get_product_by_id
    p = get_product_by_id(pid)
    if not p or p["seller_id"] != get_owner_id(message.from_user.id):
        await state.clear()
        await message.answer("❌ Ruxsat yo'q.")
        return
    txt = (message.text or "").strip()
    if not txt:
        await message.answer("❌ Matn ko'rinishida kiriting:"); return
    mapping = {"name": "name", "price": "price", "desc": "description", "stock": "stock"}
    if field == "price":
        value = to_int(txt, -1)
        if value <= 0:
            await message.answer("❌ Narxni to'g'ri kiriting (masalan: 150000 yoki 150 000):"); return
        update_product(pid, {"price": value})
    elif field == "stock":
        if txt.lower() in ("cheksiz", "∞", "-"):
            # Cheksiz: zaxira hisobini o'chiramiz, tugagan belgisini ham olib tashlaymiz
            update_product(pid, {"stock": None, "is_finished": False})
        else:
            value = to_int(txt, -1)
            if value < 0:
                await message.answer("❌ Sonni to'g'ri kiriting (masalan: 10) yoki «cheksiz»:"); return
            # Zaxira 0 → tugagan; >0 → yana sotuvda
            update_product(pid, {"stock": value, "is_finished": (value == 0)})
    else:
        update_product(pid, {mapping[field]: txt})
    await state.clear()
    await message.answer("✅ Mahsulot yangilandi!", reply_markup=seller_menu_kb(message.from_user.id))


# ─── Seller: mahsulot RASMLARINI o'zgartirish ────────────────────────────────
def _sphoto_save_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Saqlash", callback_data="sphoto_save")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="sphoto_cancel")],
    ])


def _own_product(user_id: int, pid: int):
    """Mahsulotni egasi (yoki yordamchisi) ekanini tekshirib qaytaradi."""
    from app.storage import get_product_by_id
    p = get_product_by_id(pid)
    if not p or p["seller_id"] != get_owner_id(user_id):
        return None
    return p


@router.callback_query(F.data.startswith("sphoto_") & ~F.data.in_({"sphoto_save", "sphoto_cancel"}))
async def seller_edit_photo_start(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    if not _own_product(call.from_user.id, pid):
        await call.answer("Topilmadi."); return
    await _ack(call)
    await state.set_state(EditProductState.waiting_photo)
    await state.update_data(pid=pid, new_photos=[])
    await call.message.answer(
        "🖼 Yangi rasm(lar)ni yuboring — albom qilib yoki bittalab.\n"
        "Tugagach «✅ Saqlash» tugmasini bosing.\n"
        "⚠️ Eski rasmlar yangilari bilan to'liq almashtiriladi."
    )


@router.message(EditProductState.waiting_photo, F.media_group_id, F.photo)
async def seller_edit_photo_album(message: Message, state: FSMContext):
    key = (message.from_user.id, message.media_group_id)

    async def done(photos):
        d = await state.get_data()
        allp = (d.get("new_photos") or []) + photos
        await state.update_data(new_photos=allp)
        await message.answer(f"✅ {len(allp)} ta rasm qabul qilindi.", reply_markup=_sphoto_save_kb())

    collect(key, message.photo[-1].file_id, 1.5, done)


@router.message(EditProductState.waiting_photo, F.photo)
async def seller_edit_photo_single(message: Message, state: FSMContext):
    data = await state.get_data()
    allp = (data.get("new_photos") or []) + [message.photo[-1].file_id]
    await state.update_data(new_photos=allp)
    await message.answer(f"✅ {len(allp)} ta rasm qabul qilindi.", reply_markup=_sphoto_save_kb())


@router.message(EditProductState.waiting_photo)
async def seller_edit_photo_other(message: Message, state: FSMContext):
    if (message.text or "").strip() in ("/cancel", "❌ Bekor qilish"):
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=seller_main_menu)
        return
    await message.answer("🖼 Iltimos, rasm yuboring (yoki «✅ Saqlash» / /cancel).")


@router.callback_query(EditProductState.waiting_photo, F.data == "sphoto_save")
async def seller_edit_photo_save(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pid = data.get("pid")
    photos = data.get("new_photos") or []
    if not photos:
        await call.answer("Avval kamida 1 ta rasm yuboring.", show_alert=True); return
    if not _own_product(call.from_user.id, pid):
        await state.clear(); await call.answer("Ruxsat yo'q."); return
    update_product(pid, {"photos": photos})
    await state.clear()
    await call.answer("✅ Rasmlar saqlandi")
    await call.message.answer(
        f"✅ Rasmlar yangilandi! ({len(photos)} ta)",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Mahsulotni ko'rish", callback_data=f"sprod_{pid}")],
            [InlineKeyboardButton(text="📦 Mahsulotlarim", callback_data="seller_products")],
        ])
    )


@router.callback_query(EditProductState.waiting_photo, F.data == "sphoto_cancel")
async def seller_edit_photo_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Bekor qilindi")
    await call.message.answer("❌ Rasm o'zgartirish bekor qilindi.", reply_markup=seller_main_menu)


# ─── Seller: mahsulot VIDEOSINI o'zgartirish ─────────────────────────────────
@router.callback_query(F.data.startswith("svideo_") & ~F.data.in_({"svideo_del"}))
async def seller_edit_video_start(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    p = _own_product(call.from_user.id, pid)
    if not p:
        await call.answer("Topilmadi."); return
    await _ack(call)
    await state.set_state(EditProductState.waiting_video)
    await state.update_data(pid=pid)
    kb = None
    if p.get("video"):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Videoni o'chirish", callback_data="svideo_del")],
        ])
    await call.message.answer(
        "🎬 Qisqa videoni yuboring (mahsulot kartochkasida ko'rinadi).\n"
        "Bekor qilish: /cancel",
        reply_markup=kb,
    )


@router.message(EditProductState.waiting_video, F.video)
async def seller_edit_video_save(message: Message, state: FSMContext):
    data = await state.get_data()
    pid = data.get("pid")
    if not _own_product(message.from_user.id, pid):
        await state.clear(); await message.answer("Ruxsat yo'q."); return
    update_product(pid, {"video": message.video.file_id})
    await state.clear()
    await message.answer(
        "✅ Video saqlandi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Mahsulotni ko'rish", callback_data=f"sprod_{pid}")],
            [InlineKeyboardButton(text="📦 Mahsulotlarim", callback_data="seller_products")],
        ])
    )


@router.callback_query(EditProductState.waiting_video, F.data == "svideo_del")
async def seller_edit_video_del(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    pid = data.get("pid")
    update_product(pid, {"video": None})
    await state.clear()
    await call.answer("🗑 Video o'chirildi")
    await call.message.answer("🗑 Video o'chirildi.", reply_markup=seller_main_menu)


@router.message(EditProductState.waiting_video)
async def seller_edit_video_other(message: Message, state: FSMContext):
    if (message.text or "").strip() in ("/cancel", "❌ Bekor qilish"):
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=seller_main_menu)
        return
    await message.answer("🎬 Iltimos, video yuboring (yoki /cancel).")


@router.callback_query(F.data.startswith("del_product_"))
async def delete_product_handler(call: CallbackQuery):
    pid = int(call.data.split("_")[-1])
    if delete_product(pid, get_owner_id(call.from_user.id)):
        await call.answer("🗑 O'chirildi!")
        await seller_products(call)
    else:
        await call.answer("Topilmadi.")


# ─── "Tugadi" / "Bor" belgilash ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("pfin_"))
async def toggle_product_finished(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    from app.storage import get_product_by_id
    p = get_product_by_id(pid)
    if not p or p["seller_id"] != get_owner_id(call.from_user.id):
        await call.answer("Topilmadi."); return
    new_val = not p.get("is_finished")
    update_product(pid, {"is_finished": new_val})
    await call.answer("❌ Tugagan deb belgilandi" if new_val else "✅ Sotuvda deb belgilandi")
    await seller_product_detail(call)


# ─── Mahsulot qo'shish ───────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_add_product")
async def start_add_product(call: CallbackQuery, state: FSMContext):
    if not is_shop_member(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    await _ack(call)
    await state.set_data({})   # oldingi chala urinishdan rasm va boshqa ma'lumot qolmasin
    await state.set_state(AddProductState.name)
    await call.message.answer("📦 Mahsulot nomini kiriting:")


# ─── Mahsulot qo'shishni bo'lib yuboruvchi tugma/buyruqlarda AVTOMAT to'xtatish ──
# Foydalanuvchi nom/tavsif/narx/rasm/rang so'ralganda /start yoki menyu tugmasini
# bossa — uni input deb qabul qilmaymiz, jarayonni to'xtatamiz.
MENU_BUTTONS = {
    "🛒 Market", "🛍 Bozor", "🔎 Qidirish", "🏪 Sotuvchi bo'lish", "📦 Buyurtmalarim",
    "👤 Profil", "ℹ️ Ma'lumot", "📞 Aloqa", "🛍 Do'kon (ilova)", "❌ Bekor qilish",
}

ADD_PRODUCT_STATES = StateFilter(
    AddProductState.name, AddProductState.description,
    AddProductState.price, AddProductState.stock,
    AddProductState.photo, AddProductState.colors,
    AddProductState.video, AddProductState.preview,
)

# Rasm bosqichi uchun matn (bir necha joyda ishlatiladi)
_PHOTO_PROMPT = (
    "📸 Kamida 2 ta rasm yuboring — albom qilib birga yoki bittadan."
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
    await message.answer("📝 Tavsif kiriting (kamida 8 ta so'z):")


@router.message(AddProductState.description, F.text == "/skip")
async def product_description_skip(message: Message, state: FSMContext):
    await message.answer("❌ Tavsif majburiy — kamida 8 ta so'z yozing:")


@router.message(AddProductState.description)
async def product_description(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    if not txt:
        await message.answer("❌ Tavsifni matn ko'rinishida kiriting:"); return
    if len(txt.split()) < 8:
        await message.answer("❌ Tavsif kamida 8 ta so'zdan iborat bo'lsin. To'liqroq yozing:"); return
    await state.update_data(description=txt)
    await state.set_state(AddProductState.price)
    await message.answer("💰 Narxini kiriting (masalan: 150000 yoki 150 000):")


@router.message(AddProductState.price)
async def product_price(message: Message, state: FSMContext):
    price = to_int(message.text, -1)
    if price <= 0:
        await message.answer("❌ Narxni to'g'ri kiriting (masalan: 150000 yoki 150 000):"); return
    await state.update_data(price=price)
    await state.set_state(AddProductState.stock)
    await message.answer(
        "📦 Omborda nechta bor? Sonini kiriting (masalan: 10),\n"
        "yoki hisob yuritmasangiz /skip yozing (cheksiz):"
    )


@router.message(AddProductState.stock, F.text == "/skip")
async def product_stock_skip(message: Message, state: FSMContext):
    await state.update_data(stock=None)
    await state.set_state(AddProductState.photo)
    await message.answer(_PHOTO_PROMPT)


@router.message(AddProductState.stock)
async def product_stock_enter(message: Message, state: FSMContext):
    stock = to_int(message.text, -1)
    if stock < 0:
        await message.answer("❌ Sonni to'g'ri kiriting (masalan: 10) yoki /skip yozing:"); return
    await state.update_data(stock=stock)
    await state.set_state(AddProductState.photo)
    await message.answer(_PHOTO_PROMPT)


def _build_product(user_id: int, data: dict, photos: list) -> dict:
    owner = get_owner_id(user_id)
    seller = get_seller(owner)
    stock = data.get("stock")
    return {
        "seller_id":   owner,
        "shop_name":   seller["shop_name"],
        "name":        data["name"],
        "category":    data.get("category", "other"),
        "description": data.get("description", ""),
        "price":       data["price"],
        "old_price":   data.get("old_price"),
        "photos":      photos,
        "colors":      data.get("colors", []),
        "video":       data.get("video"),
        "stock":       stock,
        # Zaxira 0 bo'lsa — darhol "tugagan" deb belgilaymiz
        "is_finished": (stock == 0),
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
        all_photos = (data.get("pending_photos") or []) + photos
        await state.update_data(pending_photos=all_photos)
        await state.set_state(AddProductState.colors)
        await message.answer(_colors_prompt())

    collect(key, message.photo[-1].file_id, 1.5, done)


# ─── Bitta rasm (kamida 2 ta bo'lguncha yig'amiz) ────────────────────────────
@router.message(AddProductState.photo, F.photo)
async def product_photo_single(message: Message, state: FSMContext):
    data   = await state.get_data()
    photos = (data.get("pending_photos") or []) + [message.photo[-1].file_id]
    await state.update_data(pending_photos=photos)
    if len(photos) < 2:
        await message.answer(
            f"✅ {len(photos)}-rasm qabul qilindi. Yana kamida {2 - len(photos)} ta rasm yuboring:"
        )
        return
    await state.set_state(AddProductState.colors)
    await message.answer(_colors_prompt())


# ─── /skip endi ishlamaydi — rasm majburiy ───────────────────────────────────
@router.message(AddProductState.photo, F.text == "/skip")
async def product_photo_skip(message: Message, state: FSMContext):
    await message.answer("❌ Rasmsiz qo'shib bo'lmaydi — kamida 2 ta rasm yuboring:")


# ─── Noto'g'ri tur ───────────────────────────────────────────────────────────
@router.message(AddProductState.photo)
async def product_photo_wrong(message: Message, state: FSMContext):
    await message.answer("❌ Rasm yuboring (kamida 2 ta):")


# ─── Rang kiritish ────────────────────────────────────────────────────────────
@router.message(AddProductState.colors, F.text == "/skip")
async def product_colors_skip(message: Message, state: FSMContext):
    await state.update_data(colors=[])
    await _ask_video(message, state)


@router.message(AddProductState.colors, F.text)
async def product_colors_enter(message: Message, state: FSMContext):
    colors = [c.strip() for c in (message.text or "").split(",") if c.strip()]
    if not colors:
        await message.answer("❌ Ranglarni vergul bilan ajratib yozing yoki /skip yozing:")
        return
    await state.update_data(colors=colors)
    await _ask_video(message, state)


# ─── Qisqa video (ixtiyoriy) ─────────────────────────────────────────────────
async def _ask_video(message: Message, state: FSMContext):
    await state.set_state(AddProductState.video)
    await message.answer(
        "🎬 Mahsulot uchun qisqa video yuboring (mahsulot kartochkasida ko'rinadi),\n"
        "yoki video kerak bo'lmasa /skip yozing."
    )


@router.message(AddProductState.video, F.text == "/skip")
async def product_video_skip(message: Message, state: FSMContext):
    await state.update_data(video=None)
    await _show_preview(message, state)


@router.message(AddProductState.video, F.video)
async def product_video_add(message: Message, state: FSMContext):
    await state.update_data(video=message.video.file_id)
    await _show_preview(message, state)


@router.message(AddProductState.video)
async def product_video_wrong(message: Message, state: FSMContext):
    await message.answer("🎬 Video yuboring yoki /skip yozing:")


# ─── Saqlashdan oldin ko'rib chiqish (preview) ───────────────────────────────
def _preview_text(data: dict) -> str:
    price = data.get("price", 0)
    lines = ["👀 <b>Mahsulot shunday chiqadi:</b>\n", f"📦 <b>{data.get('name','')}</b>"]
    lines.append(f"💰 <b>{price:,} so'm</b>")
    desc = data.get("description")
    if desc:
        lines.append(f"\n📝 {desc}")
    colors = data.get("colors") or []
    if colors:
        lines.append(f"\n🎨 Ranglar: {', '.join(colors)}")
    stock = data.get("stock")
    lines.append(f"\n📦 Omborda: {stock} dona" if stock is not None else "\n📦 Ombor: cheksiz")
    photos = data.get("pending_photos") or []
    lines.append(f"\n🖼 {len(photos)} ta rasm" if photos else "\n🖼 Rasmsiz")
    lines.append("🎬 Video: bor" if data.get("video") else "🎬 Video: yo'q")
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
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yana mahsulot qo'shish", callback_data="seller_add_product")],
        [InlineKeyboardButton(text="📦 Mahsulotlarim",          callback_data="seller_products")],
    ])
    await call.message.answer(
        f"✅ <b>{data['name']}</b> qo'shildi!\n"
        f"💰 {data['price']:,} so'm · {photo_info}🎨 {colors_str}",
        parse_mode="HTML", reply_markup=kb
    )
    await call.answer("Saqlandi ✅")


@router.callback_query(AddProductState.preview, F.data == "ap_cancel")
async def product_preview_cancel(call: CallbackQuery, state: FSMContext):
    await _ack(call)
    await state.clear()
    await call.message.answer("❌ Mahsulot qo'shish bekor qilindi.", reply_markup=main_menu)


# ─── Buyurtmalar (seller) ───────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_orders")
async def seller_orders_list(call: CallbackQuery):
    if not is_shop_member(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    await _ack(call)
    orders = get_seller_orders(get_owner_id(call.from_user.id))
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


@router.callback_query(F.data.startswith("sorder_"))
async def seller_order_detail(call: CallbackQuery):
    oid = int(call.data.split("_")[1])
    from app.storage import get_order_by_id
    o = get_order_by_id(oid)
    if not o or o["seller_id"] != get_owner_id(call.from_user.id):
        await call.answer("Topilmadi."); return
    await _ack(call)
    status = ORDER_STATUSES.get(o.get("status",""), "—")
    dlv = {
        "pickup": "🚶 O'zi olib ketadi",
        "taxi": "🚕 Taksi pochta (shu bugunoq)",
        "btc": "📦 BTC Pochta", "emu": "🚀 EMU Express", "uzum": "🍊 Uzum Pochta",
    }.get(o.get("delivery",""), o.get("delivery","—"))
    receipt_line = "🧾 Chek: yuborilgan" if o.get("receipt") else "🧾 Chek: yo'q"

    # Xaridor ma'lumotlari sellerga HECH QACHON ko'rsatilmaydi — endi seller bilan
    # xaridor o'rtasida to'g'ridan aloqa yo'q. Manzil/tel/ism faqat KURIERGA
    # ko'rinadi (mahsulotni kurier do'kondan olib, xaridorga yetkazadi).
    buyer_block = (
        f"🔒 <b>Xaridor ma'lumotlari kurierда — ko'rsatilmaydi.</b>\n"
        f"   (mahsulotni kurier do'kondan olib, xaridorga yetkazadi)\n"
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
        # Delivery (yetkazib berish) buyurtmada YAKUNIY "delivered"ni KURIER oqimi
        # bajaradi (kurier "Yetkazib berildi" → seller "To'lovni oldim" / 3 daqiqa).
        # Shuning uchun seller bu yerda faqat "Yo'lda"gacha o'zgartiradi — aks holda
        # xaridorga qolgan to'lov so'rovi va baholash ikki marta borardi.
        next_statuses = {
            "pending":    ["cancelled"],
            "paid":       ["processing","cancelled"],
            "processing": ["shipped"],
        }
    rows = []
    if o.get("receipt"):
        rows.append([InlineKeyboardButton(text="🧾 Chekni ko'rish", callback_data=f"vrcpt_{oid}")])
    for s in next_statuses.get(o.get("status",""), []):
        rows.append([InlineKeyboardButton(
            text=SELLER_ACTION_LABELS.get(s, ORDER_STATUSES[s]),
            callback_data=f"ostatus_{oid}_{s}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_orders")])
    await call.message.edit_text(text, parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


@router.callback_query(F.data.startswith("vrcpt_"))
async def seller_view_receipt(call: CallbackQuery):
    oid = int(call.data.split("_")[1])
    from app.storage import get_order_by_id
    o = get_order_by_id(oid)
    if not o or o["seller_id"] != get_owner_id(call.from_user.id):
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
    if not o or o["seller_id"] != get_owner_id(call.from_user.id):
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
            # Qolgan to'lov (90%) haqida toza xabar + baholash tugmalari.
            total   = o.get("total", 0)
            prepay  = o.get("prepay", 0)
            remain  = max(total - prepay, 0)
            remain_pct = round(remain / total * 100) if total else 0
            seller_card = (get_seller(o["seller_id"]) or {}).get("card_number", "")
            card_line = (
                f"💳 Seller karta/raqami:  <code>{seller_card}</code>  "
                f"<i>(bossangiz — nusxa olinadi)</i>\n"
                if seller_card else ""
            )
            remain_line = (
                f"\n{divider()}\n"
                f"💰 Qolgan to'lov:  <b>{money(remain)}</b>  ({remain_pct}%)\n"
                f"{card_line}"
                "Mahsulotni tekshirib, qolgan summani do'konga to'lang "
                "(naqd yoki karta).\n"
                if remain else "\n"
            )
            await bot.send_message(
                o["buyer_id"],
                f"📦 <b>Buyurtmangiz yetkazildi!</b>  (#{oid})\n"
                f"{divider()}\n"
                f"📦 {o.get('product_name', '—')}"
                f"{remain_line}\n"
                "⭐ Sellerni baholang:",
                parse_mode="HTML",
                reply_markup=stars_kb(o["seller_id"], oid)
            )
        elif status == "shipped":
            # Seller "Kurierga berdim" bosdi → xaridorga "yo'lda" xabari
            await bot.send_message(
                o["buyer_id"],
                f"🚚 <b>Mahsulotingiz yo'lda!</b>  (#{oid})\n"
                f"📦 {o.get('product_name','—')}\n\n"
                f"Kurier mahsulotni manzilingizga yetkazmoqda. "
                f"Tez orada bog'lanadi. 📍",
                parse_mode="HTML"
            )
        else:
            await bot.send_message(o["buyer_id"], msg, parse_mode="HTML")
    except Exception:
        pass

    await seller_order_detail(call)


# ─── Statistika (sotuvchi uchun) ─────────────────────────────────────────────
@router.callback_query(F.data == "seller_stats")
async def seller_stats(call: CallbackQuery):
    if not is_shop_member(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    await _ack(call)
    owner_id = get_owner_id(call.from_user.id)
    orders   = get_seller_orders(owner_id)
    products = get_seller_products(owner_id)

    # Holatlar bo'yicha sanab chiqamiz
    by_status = {}
    for o in orders:
        by_status[o.get("status", "")] = by_status.get(o.get("status", ""), 0) + 1
    delivered = [o for o in orders if o.get("status") == "delivered"]
    active    = [o for o in orders if o.get("status") in ("paid", "processing", "shipped")]

    # Daromad: yetkazilgan buyurtmalar summasi (komissiyadan keyingi qism sellerга)
    gross    = sum(to_int(o.get("total", 0)) for o in delivered)
    commission = sum(to_int(o.get("commission", 0)) for o in delivered)
    net = max(gross - commission, 0)

    # Eng ko'p sotilgan mahsulot (yetkazilgan + faol buyurtmalar bo'yicha)
    sold = {}
    for o in orders:
        if o.get("status") in ("paid", "processing", "shipped", "delivered"):
            name = o.get("product_name", "—")
            sold[name] = sold.get(name, 0) + to_int(o.get("quantity", 1))
    top_line = "—"
    if sold:
        top_name, top_qty = max(sold.items(), key=lambda x: x[1])
        top_line = f"{top_name} ({top_qty} dona)"

    from app.storage import get_seller_rating
    rating, cnt = get_seller_rating(owner_id)

    text = (
        f"📊 <b>Statistika</b>\n"
        f"{divider()}\n"
        f"📦 Mahsulotlar:  {len(products)} ta\n"
        f"🛒 Jami buyurtma:  {len(orders)} ta\n"
        f"   ✅ Yetkazilgan:  {len(delivered)} ta\n"
        f"   🔄 Jarayonda:  {len(active)} ta\n"
        f"   ⏳ Kutilmoqda:  {by_status.get('pending', 0)} ta\n"
        f"   ❌ Bekor:  {by_status.get('cancelled', 0)} ta\n"
        f"{divider()}\n"
        f"💰 Sotuv (yetkazilgan):  {gross:,} so'm\n"
        f"💵 Platforma xizmat haqi:  {commission:,} so'm\n"
        f"🟢 Sof tushum:  <b>{net:,} so'm</b>\n"
        f"{divider()}\n"
        f"🔥 Eng ko'p sotilgan:  {top_line}\n"
        f"⭐ Reyting:  {rating} ({cnt} ta baho)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")],
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


# ─── Do'kon info ─────────────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_shop_info")
async def seller_shop_info(call: CallbackQuery):
    seller = get_shop_seller(call.from_user.id)
    if not seller:
        await call.answer("Seller topilmadi."); return
    await _ack(call)
    owner_id = get_owner_id(call.from_user.id)
    from app.storage import get_seller_rating
    rating, cnt = get_seller_rating(owner_id)
    products = get_seller_products(owner_id)
    text = (
        f"🏪 <b>{seller['shop_name']}</b>\n\n"
        f"👤 {seller['full_name']}\n"
        f"📱 {seller['phone']}\n"
        f"💳 **** {seller.get('card_number','')[-4:]}\n"
        f"📦 Mahsulotlar: {len(products)} ta\n"
        f"⭐ Reyting: {rating} ({cnt} ta baho)"
    )
    rows = []
    # Kartani faqat do'kon egasi o'zgartiradi
    if is_seller(call.from_user.id):
        rows.append([InlineKeyboardButton(text="✏️ Karta raqamini o'zgartirish", callback_data="seller_edit_card")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")])
    await call.message.edit_text(text, parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ─── Karta raqamini o'zgartirish (seller o'zi) ───────────────────────────────
@router.callback_query(F.data == "seller_edit_card")
async def seller_edit_card_start(call: CallbackQuery, state: FSMContext):
    if not is_seller(call.from_user.id):
        await call.answer("Siz seller emassiz."); return
    await _ack(call)
    await state.set_state(EditCardState.waiting_value)
    await call.message.answer(
        "💳 Yangi karta yoki telefon raqamingizni kiriting:\n\n"
        "💳 Karta (16 raqam): 8600 1234 5678 9012\n"
        "📱 Telefon: +998 90 123 45 67"
    )


@router.message(EditCardState.waiting_value)
async def seller_edit_card_save(message: Message, state: FSMContext):
    if not is_seller(message.from_user.id):
        await state.clear()
        await message.answer("❌ Ruxsat yo'q.")
        return
    cleaned = (message.text or "").replace(" ", "").replace("-", "").replace("+", "")
    if not cleaned.isdigit():
        await message.answer(
            "❌ Noto'g'ri raqam.\n"
            "💳 Karta (16 raqam) yoki 📱 telefon raqamingizni kiriting:"
        )
        return
    # 16 raqam — karta; 9–13 raqam — telefon.
    if len(cleaned) == 16:
        payment = cleaned
        ok_line = f"✅ Karta raqami yangilandi: **** **** **** {cleaned[-4:]}"
    elif 9 <= len(cleaned) <= 13:
        payment = (message.text or "").strip()
        ok_line = f"✅ To'lov raqami yangilandi: {payment}"
    else:
        await message.answer(
            "❌ Noto'g'ri raqam.\n"
            "💳 Karta — 16 ta raqam, yoki 📱 telefon raqamingizni kiriting:"
        )
        return
    update_seller(message.from_user.id, {"card_number": payment})
    await state.clear()
    await message.answer(ok_line, reply_markup=seller_main_menu)


# ─── Yordamchilar (faqat do'kon egasi) ───────────────────────────────────────
def _assistants_view(owner_id: int):
    assistants = get_assistants(owner_id)
    if assistants:
        text = f"👥 <b>Yordamchilar</b> ({len(assistants)} ta):\n\nChiqarish uchun tugmani bosing."
    else:
        text = "👥 <b>Yordamchilar</b>\n\nHozircha yordamchi yo'q."
    rows = []
    for uid in assistants:
        u = get_user(uid) or {}
        name = u.get("full_name") or str(uid)
        extra = u.get("phone") or uid
        rows.append([InlineKeyboardButton(text=f"🗑 {name} ({extra})", callback_data=f"asst_del_{uid}")])
    rows.append([InlineKeyboardButton(text="➕ Yordamchi qo'shish", callback_data="asst_add")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="seller_back")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "seller_assistants")
async def seller_assistants_list(call: CallbackQuery):
    if not is_seller(call.from_user.id):
        await call.answer("Faqat do'kon egasi uchun."); return
    await _ack(call)
    text, kb = _assistants_view(call.from_user.id)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "asst_add")
async def assistant_add_start(call: CallbackQuery, state: FSMContext):
    if not is_seller(call.from_user.id):
        await call.answer("Faqat do'kon egasi uchun."); return
    await _ack(call)
    await state.set_state(AddAssistantState.waiting_user)
    await call.message.answer(
        "👥 Yordamchining <b>telefon raqamini</b> yuboring\n"
        "(masalan: +998 90 123 45 67),\n"
        "yoki 📎 orqali uning <b>kontaktini</b> ulashing.\n\n"
        "⚠️ Yordamchi avval botga /start bosgan bo'lishi kerak.",
        parse_mode="HTML", reply_markup=cancel_keyboard
    )


@router.message(AddAssistantState.waiting_user, F.text == "❌ Bekor qilish")
async def assistant_add_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⛔️ Yordamchi qo'shish bekor qilindi.", reply_markup=seller_main_menu)


@router.message(AddAssistantState.waiting_user, F.text.startswith("/"))
async def assistant_add_interrupt(message: Message, state: FSMContext):
    if (message.text or "").startswith("/start"):
        from app.handlers.start import cmd_start
        await cmd_start(message, state)
        return
    await state.clear()
    await message.answer("⛔️ Yordamchi qo'shish to'xtatildi.", reply_markup=seller_main_menu)


@router.message(AddAssistantState.waiting_user, F.text.in_(MENU_BUTTONS))
async def assistant_add_interrupt_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("⛔️ Yordamchi qo'shish to'xtatildi.", reply_markup=seller_main_menu)


@router.message(AddAssistantState.waiting_user)
async def assistant_add_save(message: Message, state: FSMContext):
    owner_id = message.from_user.id
    if not is_seller(owner_id):
        await state.clear()
        await message.answer("❌ Ruxsat yo'q.")
        return

    # Foydalanuvchini aniqlash: kontakt → forward → telefon raqami (matn)
    uid = None
    phone_txt = None
    if message.contact:
        uid = message.contact.user_id
        phone_txt = message.contact.phone_number
    elif message.forward_from:
        uid = message.forward_from.id
    elif message.text:
        phone_txt = message.text.strip()

    if uid is None and phone_txt:
        uid = find_user_id_by_phone(phone_txt)

    if not uid:
        await message.answer(
            "❌ Bu raqam bo'yicha foydalanuvchi topilmadi.\n\n"
            "Sabablari: yordamchi botga hali kirmagan yoki botda telefon "
            "raqamini hech qachon kiritmagan bo'lishi mumkin.\n\n"
            "✅ Eng ishonchli usul — 📎 (skrepka) orqali yordamchining "
            "<b>kontaktini</b> ulashing, yoki boshqa raqamini yuboring:",
            parse_mode="HTML"
        )
        return

    if uid == owner_id:
        await message.answer("❌ O'zingizni yordamchi qilib qo'sha olmaysiz.")
        return
    if get_owner_id(uid) is not None:
        await message.answer("❌ Bu foydalanuvchi allaqachon seller yoki boshqa do'kon yordamchisi.")
        return

    from app.bot.bot import bot
    try:
        await bot.get_chat(uid)
    except Exception:
        await message.answer(
            "❌ Bu foydalanuvchi topilmadi.\n"
            "U avval botga kirib /start bosishi kerak, keyin qayta urinib ko'ring."
        )
        return

    add_assistant(owner_id, uid)
    if phone_txt:
        # Raqamini profilga yozib qo'yamiz — keyingi safar shu raqam bilan topiladi
        set_user_field(uid, "phone", phone_txt)
    await state.clear()
    seller = get_seller(owner_id)
    u = get_user(uid) or {}
    name = u.get("full_name") or str(uid)
    extra = phone_txt or u.get("phone") or uid
    await message.answer(
        f"✅ <b>{name}</b> ({extra}) do'koningizga yordamchi qilib qo'shildi!",
        parse_mode="HTML", reply_markup=seller_main_menu
    )
    try:
        await bot.send_message(
            uid,
            f"✅ Siz <b>{seller['shop_name']}</b> do'koniga yordamchi qilib qo'shildingiz!\n"
            "Endi sizda sotuvchi paneli ochiq: 🛒 Sotuvchi paneli",
            parse_mode="HTML", reply_markup=seller_main_menu
        )
    except Exception:
        pass


@router.callback_query(F.data.startswith("asst_del_"))
async def assistant_remove(call: CallbackQuery):
    if not is_seller(call.from_user.id):
        await call.answer("Faqat do'kon egasi uchun."); return
    uid = int(call.data.split("_")[2])
    owner_id = call.from_user.id
    if not remove_assistant(owner_id, uid):
        await call.answer("Topilmadi."); return
    await call.answer("🗑 Yordamchi chiqarildi.")
    seller = get_seller(owner_id)
    try:
        from app.bot.bot import bot
        await bot.send_message(
            uid,
            f"ℹ️ Siz <b>{seller['shop_name']}</b> do'koni yordamchiligidan chiqarildingiz.",
            parse_mode="HTML", reply_markup=main_menu
        )
    except Exception:
        pass
    text, kb = _assistants_view(owner_id)
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data == "seller_back")
async def seller_back(call: CallbackQuery):
    seller = get_shop_seller(call.from_user.id)
    if not seller:
        await call.answer(); return
    await _ack(call)
    await call.message.edit_text(
        f"🏪 <b>{seller['shop_name']}</b> — Seller Panel",
        reply_markup=seller_menu_kb(call.from_user.id), parse_mode="HTML"
    )


# ─── /orders (buyruq orqali) ─────────────────────────────────────────────────
@router.message(Command("orders"))
async def orders_cmd(message: Message):
    if not is_shop_member(message.from_user.id):
        await message.answer("Siz seller emassiz."); return
    orders = get_seller_orders(get_owner_id(message.from_user.id))
    if not orders:
        await message.answer("🛒 Hozircha buyurtma yo'q."); return
    text = "🛒 <b>Buyurtmalaringiz:</b>\n\n"
    for o in orders[-10:]:
        status = ORDER_STATUSES.get(o.get("status",""), "—")
        text += f"<b>#{o['id']}</b> — {o.get('product_name','—')} | {status}\n"
    await message.answer(text, parse_mode="HTML")
