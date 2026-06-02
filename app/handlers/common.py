from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.storage import (
    is_seller, get_seller, get_all_products, get_seller_products,
    get_sellers, get_seller_rating, get_buyer_orders, get_order_by_id,
    search_products, register_user
)
from app.keyboards.seller import main_menu
from app.states.seller_application import SearchState

router = Router()

ORDER_STATUSES = {
    "pending":    "⏳ Kutilmoqda",
    "paid":       "💳 To'lov qilindi",
    "processing": "🔄 Tayyorlanmoqda",
    "shipped":    "🚚 Yo'lda",
    "delivered":  "✅ Yetkazildi",
    "cancelled":  "❌ Bekor qilindi",
}

DELIVERY_LABELS = {
    "btc":  "📦 BTC Pochta",
    "emu":  "🚀 EMU Express",
    "uzum": "🍊 Uzum Pochta",
}


# ─── User registration ────────────────────────────────────────────────────────
@router.message(F.text == "/start")
async def start_register(message: Message):
    register_user(message.from_user.id, {
        "full_name": message.from_user.full_name,
        "username":  message.from_user.username,
    })


# ─── Aloqa ───────────────────────────────────────────────────────────────────
@router.message(F.text == "📞 Aloqa")
async def contact_handler(message: Message):
    await message.answer(
        "📞 <b>Aloqa</b>\n\nSavol va takliflar: @promanmarketbot\nIsh vaqti: 09:00–18:00",
        parse_mode="HTML"
    )


# ─── Profil ──────────────────────────────────────────────────────────────────
@router.message(F.text == "👤 Profilim")
async def profile_handler(message: Message):
    user = message.from_user
    seller = get_seller(user.id)
    if seller:
        rating, cnt = get_seller_rating(user.id)
        stars = "⭐" * int(rating) if rating else "—"
        products = get_seller_products(user.id)
        extra = (
            f"\n🏪 Do'kon: {seller['shop_name']}\n"
            f"📦 Mahsulotlar: {len(products)} ta\n"
            f"⭐ Reyting: {stars} {rating} ({cnt} ta baho)\n\n"
            "/seller — seller panel"
        )
        role = "🏪 Seller"
    else:
        role  = "🛍 Xaridor"
        extra = "\n\nSeller bo'lish: 🏪 Seller bo'lish"

    await message.answer(
        f"👤 <b>Profilingiz</b>\n\n"
        f"Ism: {user.full_name}\n"
        f"Username: @{user.username or 'yoq'}\n"
        f"ID: {user.id}\n"
        f"Rol: {role}{extra}",
        parse_mode="HTML", reply_markup=main_menu
    )


# ─── Bozor — do'konlar ro'yxati ──────────────────────────────────────────────
@router.message(F.text == "🛍 Bozor")
async def market_handler(message: Message):
    sellers = get_sellers()
    if not sellers:
        await message.answer("🛒 Hozircha do'kon yo'q.")
        return
    rows = []
    for uid, s in sellers.items():
        rating, cnt = get_seller_rating(int(uid))
        stars = f"⭐{rating}" if cnt else ""
        prods = get_seller_products(int(uid))
        rows.append([InlineKeyboardButton(
            text=f"🏪 {s['shop_name']} {stars} ({len(prods)} ta mahsulot)",
            callback_data=f"shop_{uid}"
        )])
    await message.answer(
        "🛍 <b>Do'konlar</b>\nBitta do'konni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@router.callback_query(F.data.startswith("shop_"))
async def show_shop(call: CallbackQuery):
    uid = int(call.data.split("_")[1])
    seller = get_seller(uid)
    if not seller:
        await call.answer("Do'kon topilmadi."); return
    products = get_seller_products(uid)
    rating, cnt = get_seller_rating(uid)
    stars = "⭐" * int(rating) if cnt else "—"

    text = (
        f"🏪 <b>{seller['shop_name']}</b>\n"
        f"👤 {seller['full_name']}\n"
        f"⭐ Reyting: {stars} {rating} ({cnt} ta)\n"
        f"📦 Mahsulotlar: {len(products)} ta\n"
    )
    rows = []
    for p in products:
        rows.append([InlineKeyboardButton(
            text=f"📦 {p['name']} — {p['price']:,} so'm",
            callback_data=f"prod_{p['id']}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Do'konlar", callback_data="back_shops")])
    await call.message.edit_text(text, parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data == "back_shops")
async def back_to_shops(call: CallbackQuery):
    sellers = get_sellers()
    rows = []
    for uid, s in sellers.items():
        rating, cnt = get_seller_rating(int(uid))
        stars = f"⭐{rating}" if cnt else ""
        prods = get_seller_products(int(uid))
        rows.append([InlineKeyboardButton(
            text=f"🏪 {s['shop_name']} {stars} ({len(prods)} ta mahsulot)",
            callback_data=f"shop_{uid}"
        )])
    await call.message.edit_text(
        "🛍 <b>Do'konlar</b>\nBitta do'konni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await call.answer()


# ─── Mahsulot detail ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("prod_"))
async def product_detail(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    from app.storage import get_product_by_id
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Topilmadi."); return
    text = (
        f"📦 <b>{p['name']}</b>\n"
        f"🏪 {p.get('shop_name','—')}\n"
        f"📝 {p.get('description','—')}\n"
        f"💰 {p['price']:,} so'm\n\n"
        f"<b>⚠️ Yetkazib berish muddati: kamida 3 kun</b>\n"
        f"📮 BTC | EMU | Uzum Pochta orqali jo'natiladi"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Zakaz qilish", callback_data=f"order_{pid}")],
        [InlineKeyboardButton(text="🔙 Orqaga",       callback_data=f"shop_{p['seller_id']}")],
    ])
    if p.get("photo"):
        try:
            await call.message.answer_photo(p["photo"], caption=text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    else:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


# ─── Zakaz qilish ────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("order_"))
async def start_order(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    from app.storage import get_product_by_id
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    await state.set_state("OrderState:delivery")
    await state.update_data(pid=pid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 BTC Pochta",   callback_data="dlv_btc")],
        [InlineKeyboardButton(text="🚀 EMU Express",  callback_data="dlv_emu")],
        [InlineKeyboardButton(text="🍊 Uzum Pochta",  callback_data="dlv_uzum")],
    ])
    prepay = int(p["price"] * 0.1)
    await call.message.answer(
        f"🛒 <b>{p['name']}</b> — {p['price']:,} so'm\n\n"
        f"💳 Oldi-to'lov (10%): <b>{prepay:,} so'm</b>\n"
        f"<b>❗ Karta raqami: {get_seller(p['seller_id']).get('card_number','—')}</b>\n\n"
        f"🚚 Yetkazib berish usulini tanlang:",
        parse_mode="HTML", reply_markup=kb
    )
    await call.answer()


@router.callback_query(F.data.startswith("dlv_"))
async def choose_delivery(call: CallbackQuery, state: FSMContext):
    dlv = call.data.split("_")[1]
    await state.update_data(delivery=dlv)
    data = await state.get_data()
    pid  = data["pid"]
    from app.storage import get_product_by_id, save_order
    p = get_product_by_id(pid)
    seller = get_seller(p["seller_id"])
    prepay = int(p["price"] * 0.1)

    order_id = save_order({
        "buyer_id":     call.from_user.id,
        "seller_id":    p["seller_id"],
        "product_id":   pid,
        "product_name": p["name"],
        "total":        p["price"],
        "prepay":       prepay,
        "delivery":     dlv,
        "status":       "pending",
    })
    await state.clear()

    dlv_label = DELIVERY_LABELS.get(dlv, dlv)
    confirm_text = (
        f"✅ <b>Zakaz #{order_id} qabul qilindi!</b>\n\n"
        f"📦 {p['name']}\n"
        f"💰 Narx: {p['price']:,} so'm\n"
        f"💳 Oldi-to'lov (10%): <b>{prepay:,} so'm</b>\n"
        f"   → Karta: <code>{seller.get('card_number','—')}</code>\n\n"
        f"🚚 Yetkazib berish: {dlv_label}\n"
        f"<b>🔴 Yetkazib berish muddati: kamida 3 KUN</b>\n\n"
        f"⏳ Holat: {ORDER_STATUSES['pending']}\n"
        f"📦 Zakaz raqami: #{order_id}"
    )
    await call.message.answer(confirm_text, parse_mode="HTML")

    # Sellerga xabar
    try:
        from app.bot.bot import bot
        await bot.send_message(
            p["seller_id"],
            f"🛒 <b>Yangi zakaz #{order_id}!</b>\n\n"
            f"📦 {p['name']}\n"
            f"👤 Xaridor ID: {call.from_user.id}\n"
            f"🚚 {dlv_label}\n"
            f"💰 {p['price']:,} so'm\n\n"
            f"Holatni yangilash: /orders",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer()


# ─── Zakazlarim ──────────────────────────────────────────────────────────────
@router.message(F.text == "📦 Zakazlarim")
async def my_orders(message: Message):
    orders = get_buyer_orders(message.from_user.id)
    if not orders:
        await message.answer("📦 Hozircha zakaz yo'q.")
        return
    text = "📦 <b>Zakazlaringiz:</b>\n\n"
    for o in orders[-10:]:
        dlv = DELIVERY_LABELS.get(o.get("delivery",""), o.get("delivery",""))
        status = ORDER_STATUSES.get(o.get("status",""), o.get("status",""))
        text += (
            f"<b>#{o['id']}</b> — {o.get('product_name','—')}\n"
            f"   💰 {o.get('total',0):,} so'm\n"
            f"   🚚 {dlv}\n"
            f"   📌 {status}\n"
        )
        if o.get("status") not in ("delivered","cancelled"):
            text += f"   <b>🔴 Yetkazib berish: kamida 3 KUN</b>\n"
        text += "\n"
    await message.answer(text, parse_mode="HTML")


# ─── Qidirish ────────────────────────────────────────────────────────────────
@router.message(F.text == "🔍 Qidirish")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(SearchState.query)
    await message.answer("🔍 Mahsulot nomini kiriting:")


@router.message(SearchState.query)
async def do_search(message: Message, state: FSMContext):
    await state.clear()
    results = search_products(message.text)
    if not results:
        await message.answer("😔 Hech narsa topilmadi. Boshqa so'z bilan sinab ko'ring.", reply_markup=main_menu)
        return
    text = f"🔍 <b>Natijalar:</b> {len(results)} ta topildi\n\n"
    rows = []
    for p in results[:10]:
        text += f"📦 {p['name']} — {p['price']:,} so'm\n"
        rows.append([InlineKeyboardButton(
            text=f"📦 {p['name']} — {p['price']:,} so'm",
            callback_data=f"prod_{p['id']}"
        )])
    await message.answer(text, parse_mode="HTML",
                          reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ─── Baholash ────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("rev_"))
async def save_review(call: CallbackQuery):
    # rev_<seller_id>_<order_id>_<stars>
    parts = call.data.split("_")
    seller_id = int(parts[1])
    order_id  = int(parts[2])
    stars     = int(parts[3])
    from app.storage import add_review
    add_review({
        "seller_id": seller_id,
        "buyer_id":  call.from_user.id,
        "order_id":  order_id,
        "stars":     stars,
    })
    star_str = "⭐" * stars
    await call.message.edit_text(f"✅ Bahoyingiz qabul qilindi: {star_str} ({stars}/5)")
    await call.answer("Rahmat!")
