from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext

from app.storage import (
    is_seller, get_seller, get_all_products, get_seller_products,
    get_sellers, get_seller_rating, get_buyer_orders, get_order_by_id,
    search_products, register_user, get_product_by_id,
    save_order, update_order_fields,
)
from app.keyboards.seller import main_menu, phone_keyboard, cancel_keyboard
from app.states.seller_application import SearchState, OrderState
from app.app.config.settings import settings

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


# ─── Rasm/matn xabarlar uchun XAVFSIZ navigatsiya ────────────────────────────
# Rasmli xabarni edit_text qilib bo'lmaydi (TelegramBadRequest).
# Shuning uchun rasm bo'lsa — eski xabarni o'chirib, yangisini yuboramiz.
# Aynan shu "Orqaga" tugmasi yo'qolib qolishi muammosini hal qiladi.
async def _safe_nav(call: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    msg = call.message
    try:
        if msg.photo or msg.video or msg.document:
            try:
                await msg.delete()
            except Exception:
                pass
            await msg.answer(text, parse_mode="HTML", reply_markup=kb)
        else:
            await msg.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        try:
            await msg.answer(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass


def _shops_keyboard() -> InlineKeyboardMarkup:
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
    return InlineKeyboardMarkup(inline_keyboard=rows)


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
    await message.answer(
        "🛍 <b>Do'konlar</b>\nBitta do'konni tanlang:",
        parse_mode="HTML",
        reply_markup=_shops_keyboard()
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
    await _safe_nav(call, text, InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data == "back_shops")
async def back_to_shops(call: CallbackQuery):
    await _safe_nav(call, "🛍 <b>Do'konlar</b>\nBitta do'konni tanlang:", _shops_keyboard())
    await call.answer()


# ─── Mahsulot detail ─────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("prod_"))
async def product_detail(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
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
            # file_id eskirgan yoki noto'g'ri bo'lsa — matn bilan ko'rsatamiz
            await call.message.answer(
                text + "\n\n<i>(rasm yuklanmadi)</i>",
                parse_mode="HTML", reply_markup=kb
            )
    else:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


# ─── Zakaz qilish: 1) yetkazib berish usuli ─────────────────────────────────
@router.callback_query(F.data.startswith("order_"))
async def start_order(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    await state.set_state(OrderState.delivery)
    await state.update_data(pid=pid)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 BTC Pochta",   callback_data="dlv_btc")],
        [InlineKeyboardButton(text="🚀 EMU Express",  callback_data="dlv_emu")],
        [InlineKeyboardButton(text="🍊 Uzum Pochta",  callback_data="dlv_uzum")],
    ])
    await call.message.answer(
        f"🛒 <b>{p['name']}</b> — {p['price']:,} so'm\n\n"
        f"🚚 Yetkazib berish usulini tanlang:",
        parse_mode="HTML", reply_markup=kb
    )
    await call.answer()


# ─── 2) yetkazib berish tanlandi → manzil so'raymiz ─────────────────────────
@router.callback_query(OrderState.delivery, F.data.startswith("dlv_"))
async def choose_delivery(call: CallbackQuery, state: FSMContext):
    dlv = call.data.split("_")[1]
    await state.update_data(delivery=dlv)
    await state.set_state(OrderState.address)
    await call.message.answer(
        "📍 <b>Yetkazib berish manzilini kiriting:</b>\n"
        "(viloyat, tuman, ko'cha, uy — to'liq yozing)",
        parse_mode="HTML", reply_markup=cancel_keyboard
    )
    await call.answer()


# ─── Bekor qilish (har qanday buyurtma bosqichida) ──────────────────────────
@router.message(
    OrderState.delivery, F.text == "❌ Bekor qilish"
)
@router.message(OrderState.address, F.text == "❌ Bekor qilish")
@router.message(OrderState.phone,   F.text == "❌ Bekor qilish")
@router.message(OrderState.receipt, F.text == "❌ Bekor qilish")
async def cancel_order(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=main_menu)


# ─── 3) manzil qabul qilindi → telefon so'raymiz ────────────────────────────
@router.message(OrderState.address)
async def order_address(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("❌ Manzilni matn ko'rinishida kiriting:")
        return
    await state.update_data(address=message.text.strip())
    await state.set_state(OrderState.phone)
    await message.answer(
        "📱 <b>Telefon raqamingizni yuboring</b>\n"
        "(pastdagi tugma orqali yoki qo'lda yozing):",
        parse_mode="HTML", reply_markup=phone_keyboard
    )


# ─── 4) telefon qabul → buyurtma saqlanadi, oldi-to'lov ko'rsatiladi ────────
@router.message(OrderState.phone)
async def order_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    elif message.text and message.text.strip():
        phone = message.text.strip()
    else:
        await message.answer("❌ Telefon raqamni yuboring yoki yozing:")
        return

    data = await state.get_data()
    pid  = data["pid"]
    dlv  = data["delivery"]
    p = get_product_by_id(pid)
    if not p:
        await state.clear()
        await message.answer("❌ Mahsulot topilmadi.", reply_markup=main_menu)
        return

    commission = int(p["price"] * settings.COMMISSION_RATE)
    order_id = save_order({
        "buyer_id":     message.from_user.id,
        "buyer_name":   message.from_user.full_name,
        "buyer_username": message.from_user.username,
        "seller_id":    p["seller_id"],
        "product_id":   pid,
        "product_name": p["name"],
        "total":        p["price"],
        "prepay":       commission,       # 10% = platforma komissiyasi
        "commission":   commission,
        "delivery":     dlv,
        "address":      data["address"],
        "phone":        phone,
        "status":       "pending",
        "receipt":      None,
    })
    await state.update_data(order_id=order_id)
    await state.set_state(OrderState.receipt)

    dlv_label   = DELIVERY_LABELS.get(dlv, dlv)
    platform_card = settings.PLATFORM_CARD or "⚠️ admin kartani sozlamagan"
    pct = int(settings.COMMISSION_RATE * 100)

    # ── Xaridorga: oldi-to'lov PLATFORMA kartasiga ──
    await message.answer(
        f"✅ <b>Zakaz #{order_id} qabul qilindi!</b>\n\n"
        f"📦 {p['name']}\n"
        f"💰 Narx: {p['price']:,} so'm\n"
        f"💳 Oldi-to'lov ({pct}%): <b>{commission:,} so'm</b>\n"
        f"   → Karta: <code>{platform_card}</code>\n\n"
        f"🚚 Yetkazib berish: {dlv_label}\n"
        f"📍 Manzil: {data['address']}\n"
        f"📱 Tel: {phone}\n"
        f"<b>🔴 Yetkazib berish muddati: kamida 3 KUN</b>\n\n"
        f"🧾 <b>Endi to'lov chekining rasmini (skrinshot) shu yerga yuboring.</b>\n"
        f"Chek tasdiqlangach buyurtmangiz tayyorlanadi.",
        parse_mode="HTML", reply_markup=cancel_keyboard
    )

    # ── Sellerga: TO'LIQ ma'lumot (kim, qayerga, telefon) ──
    try:
        from app.bot.bot import bot
        await bot.send_message(
            p["seller_id"],
            f"🛒 <b>Yangi zakaz #{order_id}!</b>\n\n"
            f"📦 {p['name']}\n"
            f"💰 {p['price']:,} so'm\n"
            f"👤 Xaridor: {message.from_user.full_name}\n"
            f"📱 Tel: {phone}\n"
            f"📍 Manzil: {data['address']}\n"
            f"🚚 {dlv_label}\n\n"
            f"⏳ Holat: to'lov tasdig'i kutilmoqda.\n"
            f"Zakazlar: /orders",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # ── Adminga: yangi zakaz xabari ──
    try:
        from app.bot.bot import bot
        await bot.send_message(
            settings.OWNER_ID,
            f"🆕 <b>Yangi zakaz #{order_id}</b>\n\n"
            f"📦 {p['name']} — {p['price']:,} so'm\n"
            f"💵 Komissiya ({pct}%): {commission:,} so'm\n"
            f"👤 {message.from_user.full_name} (ID: {message.from_user.id})\n"
            f"📱 {phone}\n"
            f"📍 {data['address']}\n"
            f"🚚 {dlv_label}\n\n"
            f"🧾 To'lov cheki kutilmoqda...",
            parse_mode="HTML"
        )
    except Exception:
        pass


# ─── 5) chek rasmi qabul qilinadi → admin tasdig'iga yuboriladi ─────────────
@router.message(OrderState.receipt, F.photo)
async def order_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    o = get_order_by_id(order_id) if order_id else None
    if not o:
        await state.clear()
        await message.answer("❌ Buyurtma topilmadi.", reply_markup=main_menu)
        return

    receipt_id = message.photo[-1].file_id
    update_order_fields(order_id, {"receipt": receipt_id})
    await state.clear()

    await message.answer(
        f"🧾 Chek qabul qilindi! Zakaz #{order_id} to'lovi tekshirilmoqda.\n"
        f"Tasdiqlangach xabar beramiz. ⏳",
        reply_markup=main_menu
    )

    # Adminga chek + tasdiqlash tugmalari
    pct = int(settings.COMMISSION_RATE * 100)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ To'lovni tasdiqlash", callback_data=f"paycfm_{order_id}"),
            InlineKeyboardButton(text="❌ Rad etish",            callback_data=f"payrej_{order_id}"),
        ]
    ])
    caption = (
        f"🧾 <b>Zakaz #{order_id} — to'lov cheki</b>\n\n"
        f"📦 {o.get('product_name','—')}\n"
        f"💵 Oldi-to'lov ({pct}%): {o.get('prepay',0):,} so'm\n"
        f"👤 {o.get('buyer_name','—')}\n"
        f"📱 {o.get('phone','—')}\n"
        f"📍 {o.get('address','—')}"
    )
    try:
        from app.bot.bot import bot
        await bot.send_photo(settings.OWNER_ID, receipt_id, caption=caption,
                             parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass


@router.message(OrderState.receipt)
async def order_receipt_invalid(message: Message):
    await message.answer(
        "🧾 Iltimos, to'lov chekining <b>rasmini</b> yuboring "
        "(yoki ❌ Bekor qilish).",
        parse_mode="HTML"
    )


# ─── Zakazlarim ──────────────────────────────────────────────────────────────
@router.message(F.text == "📦 Zakazlarim")
async def my_orders(message: Message):
    orders = get_buyer_orders(message.from_user.id)
    if not orders:
        await message.answer("📦 Hozircha zakaz yo'q.")
        return
    text = "📦 <b>Zakazlaringiz:</b>\n\n"
    rows = []
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
        # Chek hali yuborilmagan pending buyurtmaga — chek yuborish tugmasi
        if o.get("status") == "pending" and not o.get("receipt"):
            rows.append([InlineKeyboardButton(
                text=f"🧾 #{o['id']} uchun chek yuborish",
                callback_data=f"sendrcpt_{o['id']}"
            )])
        text += "\n"
    kb = InlineKeyboardMarkup(inline_keyboard=rows) if rows else None
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


@router.callback_query(F.data.startswith("sendrcpt_"))
async def resend_receipt(call: CallbackQuery, state: FSMContext):
    oid = int(call.data.split("_")[1])
    o = get_order_by_id(oid)
    if not o or o.get("buyer_id") != call.from_user.id:
        await call.answer("Topilmadi."); return
    await state.set_state(OrderState.receipt)
    await state.update_data(order_id=oid)
    await call.message.answer(
        f"🧾 Zakaz #{oid} uchun to'lov chekining rasmini yuboring:",
        reply_markup=cancel_keyboard
    )
    await call.answer()


# ─── Qidirish ────────────────────────────────────────────────────────────────
@router.message(F.text == "🔍 Qidirish")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(SearchState.query)
    await message.answer("🔍 Mahsulot nomini kiriting:")


@router.message(SearchState.query)
async def do_search(message: Message, state: FSMContext):
    await state.clear()
    results = search_products(message.text or "")
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
    try:
        await call.message.edit_text(f"✅ Bahoyingiz qabul qilindi: {star_str} ({stars}/5)")
    except Exception:
        await call.message.answer(f"✅ Bahoyingiz qabul qilindi: {star_str} ({stars}/5)")
    await call.answer("Rahmat!")
