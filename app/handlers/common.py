from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext

from app.storage import (
    is_seller, get_seller, get_all_products, get_seller_products,
    get_sellers, get_seller_rating, get_buyer_orders, get_order_by_id,
    search_products, register_user, get_product_by_id,
    save_order, update_order_fields,
    get_user, set_user_field, get_cities, product_photos,
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
    "pickup": "🚶 O'zi olib ketadi",
    "taxi": "🚕 Taksi pochta (shu bugunoq)",
    # eski zakazlar uchun (tarixiy) — yangi zakazlarda ishlatilmaydi
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


def _shops_keyboard(city: str) -> InlineKeyboardMarkup:
    sellers = get_sellers()
    rows = []
    for uid, s in sellers.items():
        if s.get("city") != city:
            continue
        rating, cnt = get_seller_rating(int(uid))
        stars = f"⭐{rating}" if cnt else ""
        prods = get_seller_products(int(uid))
        rows.append([InlineKeyboardButton(
            text=f"🏪 {s['shop_name']} {stars} ({len(prods)} ta mahsulot)",
            callback_data=f"shop_{uid}"
        )])
    rows.append([InlineKeyboardButton(text="📍 Shaharni o'zgartirish", callback_data="changecity")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _city_picker() -> InlineKeyboardMarkup:
    rows, row = [], []
    for c in get_cities():
        row.append(InlineKeyboardButton(text=c, callback_data=f"bcity_{c}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── Aloqa ───────────────────────────────────────────────────────────────────
@router.message(F.text == "📞 Aloqa")
async def contact_handler(message: Message):
    await message.answer(
        "📞 <b>Aloqa</b>\n\nSavol va takliflar: @promanmarketbot\nAdmin: @Marufzxon\nIsh vaqti: 09:00–18:00",
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
        u = get_user(user.id)
        city = (u.get("city") if u else None) or "tanlanmagan"
        extra = f"\n📍 Shahar: {city}\n\nSeller bo'lish: 🏪 Seller bo'lish"

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
    u = get_user(message.from_user.id)
    city = u.get("city") if u else None
    if not city:
        await message.answer(
            "📍 <b>Avval shahringizni tanlang</b>\n"
            "Sizga shu shahardagi do'konlar ko'rsatiladi:",
            parse_mode="HTML", reply_markup=_city_picker()
        )
        return
    await _show_market(message, city)


async def _show_market(message: Message, city: str):
    sellers = [s for s in get_sellers().values() if s.get("city") == city]
    if not sellers:
        await message.answer(
            f"🛒 <b>{city}</b> shahrida hozircha do'kon yo'q.\n"
            "Boshqa shaharni tanlashingiz mumkin:",
            parse_mode="HTML", reply_markup=_city_picker()
        )
        return
    await message.answer(
        f"🛍 <b>Do'konlar</b> — 📍 {city}\nBitta do'konni tanlang:",
        parse_mode="HTML",
        reply_markup=_shops_keyboard(city)
    )


@router.callback_query(F.data == "changecity")
async def change_city(call: CallbackQuery):
    await call.message.answer("📍 Shaharingizni tanlang:", reply_markup=_city_picker())
    await call.answer()


@router.callback_query(F.data.startswith("bcity_"))
async def buyer_set_city(call: CallbackQuery):
    city = call.data.split("_", 1)[1]
    if city not in get_cities():
        await call.answer("Shahar topilmadi.", show_alert=True); return
    register_user(call.from_user.id, {
        "full_name": call.from_user.full_name,
        "username":  call.from_user.username,
    })
    set_user_field(call.from_user.id, "city", city)
    await call.answer(f"📍 {city} tanlandi")
    try:
        await call.message.delete()
    except Exception:
        pass
    await _show_market(call.message, city)


@router.callback_query(F.data.startswith("shop_"))
async def show_shop(call: CallbackQuery):
    uid = int(call.data.split("_")[1])
    seller = get_seller(uid)
    if not seller:
        await call.answer("Do'kon topilmadi."); return
    # "Orqaga" mahsulotdan kelganda — uning albom rasmlarini ham tozalaymiz.
    await _clear_last_product(call.message.bot, call.message.chat.id)
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
        price = p.get("price", 0)
        old   = p.get("old_price", 0)
        disc  = f" ↓{round((old-price)/old*100)}%" if old and old > price else ""
        label = f"📦 {p['name']} — {price:,} so'm{disc}"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"prod_{p['id']}")])
    rows.append([InlineKeyboardButton(text="🔙 Do'konlar", callback_data="back_shops")])
    await _safe_nav(call, text, InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data == "back_shops")
async def back_to_shops(call: CallbackQuery):
    u = get_user(call.from_user.id)
    city = (u.get("city") if u else None)
    if not city:
        await _safe_nav(call, "📍 Shaharingizni tanlang:", _city_picker())
        await call.answer(); return
    await _safe_nav(call, f"🛍 <b>Do'konlar</b> — 📍 {city}\nBitta do'konni tanlang:",
                    _shops_keyboard(city))
    await call.answer()


# ─── Mahsulot detail ─────────────────────────────────────────────────────────
def _product_caption(p: dict) -> str:
    """Tezkor uslubida mahsulot kartochkasi matni."""
    price     = p.get("price", 0)
    old_price = p.get("old_price", 0)
    name      = p.get("name", "—")
    shop      = p.get("shop_name", "—")
    desc      = p.get("description", "")
    city      = p.get("city", "")

    # Chegirma hisoblash
    disc_pct = 0
    if old_price and old_price > price:
        disc_pct = round((old_price - price) / old_price * 100)

    # Reyting
    rating, rev_cnt = get_seller_rating(p.get("seller_id", 0))

    lines = []
    lines.append(f"📦 <b>{name}</b>")
    lines.append(f"🏪 {shop}" + (f"  ·  📍 {city}" if city else ""))

    # Narx qatori
    price_line = f"💰 <b>{price:,} so'm</b>"
    if disc_pct:
        price_line += f"  <b>↓{disc_pct}%</b>"
    lines.append(price_line)
    if old_price and disc_pct:
        lines.append(f"<s>{old_price:,} so'm</s>")

    if desc:
        lines.append(f"\n📝 {desc}")

    # Reyting
    if rev_cnt:
        stars = "⭐" * min(int(rating), 5)
        lines.append(f"\n{stars} {rating}  💬 {rev_cnt} ta sharh")

    lines.append("\n🚕 Bugun yetkazib beramiz  |  🚶 O'zingiz olib keta olasiz")
    return "\n".join(lines)


def _product_kb(p: dict) -> InlineKeyboardMarkup:
    """Mahsulot xabari uchun tugmalar: buyurtma va orqaga."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Zakaz qilish", callback_data=f"order_{p['id']}")],
        [InlineKeyboardButton(text="🔙 Orqaga",       callback_data=f"shop_{p['seller_id']}")],
    ])


# chat_id -> hozir ko'rsatilgan mahsulotning barcha xabar id'lari (albom rasmlari + tugmalar).
# Yangi mahsulot ochilganda hammasini o'chiramiz — chatda bir vaqtda faqat bitta
# mahsulot rasmlari turadi, shunda Telegram rasm ko'ruvchisida (surganda) boshqa
# mahsulot rasmlari aralashib ketmaydi (qaysi yo'l bilan ochilganidan qat'i nazar).
_last_product_msgs: dict = {}


async def _clear_last_product(bot, chat_id: int):
    for mid in _last_product_msgs.pop(chat_id, []):
        try:
            await bot.delete_message(chat_id, mid)
        except Exception:
            pass


@router.callback_query(F.data.startswith("prod_"))
async def product_detail(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Topilmadi."); return

    text    = _product_caption(p)
    photos  = product_photos(p)
    kb      = _product_kb(p)
    chat_id = call.message.chat.id

    # Oldingi mahsulot xabarlarini (albom + tugmalar) o'chiramiz, keyin bosilgan
    # xabarni (do'kon ro'yxati / qidiruv natijasi) ham.
    await _clear_last_product(call.message.bot, chat_id)
    try:
        await call.message.delete()
    except Exception:
        pass

    ids = []
    if len(photos) > 1:
        media = [InputMediaPhoto(media=ph) for ph in photos[:10]]
        media[0] = InputMediaPhoto(media=photos[0], caption=text, parse_mode="HTML")
        try:
            sent = await call.message.answer_media_group(media)
            ids.extend(m.message_id for m in sent)
            btn = await call.message.answer("👆 Mahsulot rasmlari. Buyurtma uchun:", reply_markup=kb)
            ids.append(btn.message_id)
        except Exception:
            btn = await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
            ids.append(btn.message_id)
    elif len(photos) == 1:
        try:
            sent = await call.message.answer_photo(photos[0], caption=text, parse_mode="HTML", reply_markup=kb)
            ids.append(sent.message_id)
        except Exception:
            sent = await call.message.answer(text + "\n\n<i>(rasm yuklanmadi)</i>", parse_mode="HTML", reply_markup=kb)
            ids.append(sent.message_id)
    else:
        sent = await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
        ids.append(sent.message_id)

    _last_product_msgs[chat_id] = ids
    await call.answer()


# ─── Zakaz qilish: rang tanlash (agar ranglar bo'lsa) ───────────────────────
async def _ask_color(message: Message, state: FSMContext, p: dict):
    colors = p.get("colors") or []
    if not colors:
        await _ask_fulfillment(message, state, p)
        return
    await state.set_state(OrderState.color)
    await state.update_data(pid=p["id"])
    buttons = [[InlineKeyboardButton(text=c, callback_data=f"color_{i}_{c[:30]}")] for i, c in enumerate(colors)]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(
        f"🎨 <b>{p['name']}</b> uchun rang tanlang:",
        parse_mode="HTML", reply_markup=kb
    )


@router.callback_query(OrderState.color, F.data.startswith("color_"))
async def choose_color(call: CallbackQuery, state: FSMContext):
    parts = call.data.split("_", 2)
    color = parts[2] if len(parts) > 2 else parts[-1]
    await state.update_data(selected_color=color)
    data = await state.get_data()
    p = get_product_by_id(data["pid"])
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    await _ask_fulfillment(call.message, state, p)
    await call.answer()


# ─── Zakaz qilish: 0) olib ketish usuli (o'zi / dostavka) ───────────────────
async def _ask_fulfillment(message: Message, state: FSMContext, p: dict):
    await state.set_state(OrderState.fulfillment)
    await state.update_data(pid=p["id"])
    data = await state.get_data()
    color_line = f"🎨 Rang: <b>{data['selected_color']}</b>\n" if data.get("selected_color") else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚶 O'zim olib ketaman", callback_data="flf_pickup")],
        [InlineKeyboardButton(text="🚚 Dostavka qildiraman", callback_data="flf_delivery")],
    ])
    await message.answer(
        f"🛒 <b>{p['name']}</b> — {p['price']:,} so'm\n"
        f"{color_line}\n"
        f"Mahsulotni qanday olmoqchisiz?",
        parse_mode="HTML", reply_markup=kb
    )


@router.callback_query(F.data.startswith("order_"))
async def start_order(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    await state.clear()
    await _ask_color(call.message, state, p)
    await call.answer()


# ─── 0a) O'zim olib ketaman → pochta usuli/manzil shart emas, telefon so'raymiz ─
@router.callback_query(OrderState.fulfillment, F.data == "flf_pickup")
async def fulfillment_pickup(call: CallbackQuery, state: FSMContext):
    await state.update_data(fulfillment="pickup", delivery="pickup",
                            address="🚶 O'zi olib ketadi (do'kondan)")
    await state.set_state(OrderState.phone)
    await call.message.answer(
        "📱 <b>Telefon raqamingizni yuboring</b>\n"
        "(pastdagi tugma orqali yoki qo'lda yozing):\n\n"
        "<i>To'lov tasdiqlangach do'kon bilan bog'lanib, mahsulotni o'zingiz olib ketasiz.</i>",
        parse_mode="HTML", reply_markup=phone_keyboard
    )
    await call.answer()


# ─── 0b) Dostavka → pochta usulini tanlash bosqichiga o'tamiz ───────────────
@router.callback_query(OrderState.fulfillment, F.data == "flf_delivery")
async def fulfillment_delivery(call: CallbackQuery, state: FSMContext):
    await state.update_data(fulfillment="delivery")
    await state.set_state(OrderState.delivery)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Taksi pochta (shu bugunoq)", callback_data="dlv_taxi")],
    ])
    await call.message.answer(
        "🚚 <b>Yetkazib berish usulini tanlang:</b>\n\n"
        "🚕 <b>Taksi pochta</b> — mahsulot shu bugunoq taksi orqali "
        "manzilingizga yetkaziladi.\n\n"
        "ℹ️ <i>Eslatma: taksi (yetkazib berish) haqi xaridor tomonidan "
        "to'lanadi va masofaga qarab belgilanadi. Mahsulot narxiga "
        "kirmaydi — taksi haqini yetkazilganda haydovchiga to'laysiz.</i>",
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
    OrderState.color, F.text == "❌ Bekor qilish"
)
@router.message(
    OrderState.fulfillment, F.text == "❌ Bekor qilish"
)
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
    dlv  = data.get("delivery", "pickup")
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
        "fulfillment":  data.get("fulfillment", "delivery"),
        "delivery":     dlv,
        "address":      data.get("address", "—"),
        "phone":        phone,
        "color":        data.get("selected_color", ""),
        "status":       "pending",
        "receipt":      None,
    })
    await state.update_data(order_id=order_id)
    await state.set_state(OrderState.receipt)

    dlv_label   = DELIVERY_LABELS.get(dlv, dlv)
    platform_card = settings.PLATFORM_CARD or "⚠️ admin kartani sozlamagan"
    card_name_line = f"   → Karta egasi: <b>{settings.PLATFORM_CARD_NAME}</b>\n" if settings.PLATFORM_CARD_NAME else ""
    pct = int(settings.COMMISSION_RATE * 100)
    is_pickup = data.get("fulfillment") == "pickup"

    # ── Xaridorga: oldi-to'lov PLATFORMA kartasiga ──
    if is_pickup:
        deliver_line = (
            f"🚶 Olish usuli: O'zingiz olib ketasiz\n"
            f"<b>🔵 To'lov tasdiqlangach do'kon bilan bog'lanasiz.</b>\n\n"
        )
    else:
        deliver_line = (
            f"🚚 Yetkazib berish: {dlv_label}\n"
            f"📍 Manzil: {data['address']}\n"
            f"📱 Tel: {phone}\n"
            f"<b>🟢 Yetkazib berish: SHU BUGUNOQ (taksi pochta)</b>\n"
            f"<i>ℹ️ Taksi haqi xaridor tomonidan to'lanadi (masofaga qarab) "
            f"va mahsulot narxiga kirmaydi.</i>\n\n"
        )
    await message.answer(
        f"✅ <b>Zakaz #{order_id} qabul qilindi!</b>\n\n"
        f"📦 {p['name']}\n"
        f"💰 Narx: {p['price']:,} so'm\n"
        f"💳 Oldi-to'lov ({pct}%): <b>{commission:,} so'm</b>\n"
        f"   → Karta: <code>{platform_card}</code>\n"
        f"{card_name_line}\n"
        f"{deliver_line}"
        f"🧾 <b>Endi to'lov chekining rasmini (skrinshot) shu yerga yuboring.</b>\n"
        f"Chek tasdiqlangach buyurtmangiz tayyorlanadi.",
        parse_mode="HTML", reply_markup=cancel_keyboard
    )

    # ── Sellerga: faqat MAHSULOT haqida. Xaridor kontakti YASHIRIN! ──
    # Telefon/manzil faqat admin 10% to'lovni tasdiqlagandan keyin ochiladi.
    # Bu seller bilan xaridor to'g'ridan-to'g'ri kelishib, komissiyani
    # chetlab o'tishining oldini oladi.
    try:
        from app.bot.bot import bot
        await bot.send_message(
            p["seller_id"],
            f"🛒 <b>Yangi zakaz #{order_id}!</b>\n\n"
            f"📦 {p['name']}\n"
            f"💰 {p['price']:,} so'm\n"
            f"🚚 {dlv_label}\n\n"
            f"🔒 <b>Xaridor ma'lumotlari (ism, tel, manzil) yashirin.</b>\n"
            f"Platforma to'lovi (oldi-to'lov) tasdiqlangach avtomatik ochiladi.\n\n"
            f"💡 <b>Eslatma:</b> Bot orqali sotilgan har bir zakaz uchun "
            f"mahsulot narxining {pct}% qismi platforma xizmat haqi sifatida olinadi.\n"
            f"Bu summa ({commission:,} so'm) xaridorning oldi-to'lovidan to'g'ridan-to'g'ri "
            f"platformaga o'tadi — sizdan keyinchalik alohida hech narsa so'ralmaydi. "
            f"Hamkorligingiz uchun rahmat! 🙏\n\n"
            f"⏳ Holat: to'lov tasdig'i kutilmoqda.\n"
            f"Zakazlar: /orders",
            parse_mode="HTML"
        )
    except Exception:
        pass

    # ── Adminga: yangi zakaz xabari (to'liq) ──
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
            if o.get("delivery") == "pickup":
                text += f"   <b>🔵 To'lov tasdiqlangach do'kon bilan bog'lanasiz</b>\n"
            else:
                text += f"   <b>🟢 Yetkazib berish: SHU BUGUNOQ</b>\n"
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

    await message.answer(
        f"🔍 <b>{len(results)} ta natija topildi</b>",
        parse_mode="HTML"
    )

    for p in results[:5]:
        caption = _product_caption(p)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Zakaz qilish", callback_data=f"order_{p['id']}")],
            [InlineKeyboardButton(text="🔍 Batafsil",     callback_data=f"prod_{p['id']}")],
        ])
        photos = product_photos(p)
        if photos:
            try:
                await message.answer_photo(photos[0], caption=caption, parse_mode="HTML", reply_markup=kb)
                continue
            except Exception:
                pass
        await message.answer(caption, parse_mode="HTML", reply_markup=kb)

    if len(results) > 5:
        rows = []
        for p in results[5:15]:
            price = p.get("price", 0)
            old   = p.get("old_price", 0)
            disc  = f" ↓{round((old-price)/old*100)}%" if old and old > price else ""
            rows.append([InlineKeyboardButton(
                text=f"📦 {p['name']} — {price:,} so'm{disc}",
                callback_data=f"prod_{p['id']}"
            )])
        await message.answer(
            f"📋 Qolgan natijalar:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
        )


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
