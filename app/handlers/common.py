import asyncio

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
    set_view_msgs, pop_view_msgs, get_view_msgs,
    get_favorites, is_favorite, toggle_favorite,
    is_shop_member, get_shop_seller, get_owner_id, shop_notify_ids,
)
from app.keyboards.seller import (
    main_menu, seller_main_menu, menu_for, phone_keyboard, cancel_keyboard,
    admin_contact_kb,
)
from app.states.seller_application import SearchState, OrderState
from app.app.config.settings import settings
from app.ui import (
    money, divider, title, category_label, product_category,
    product_emoji,
)

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
    # eski buyurtmalar uchun (tarixiy) — yangi buyurtmalarda ishlatilmaydi
    "btc":  "📦 BTC Pochta",
    "emu":  "🚀 EMU Express",
    "uzum": "🍊 Uzum Pochta",
}

# Shu summa va undan ortiq xaridga shahar ichida yetkazib berish bepul.
FREE_DELIVERY_MIN = 300_000
# Bepul yetkazib berish buyurtmalarida platforma sellerga shu foizni qaytaradi
# (seller taksini o'zi to'laydi, platforma esa 5% ni kartasiga o'tkazib beradi).
DELIVERY_REFUND_RATE = 0.05
# Xaridorni qiziqtirish uchun har joyda chiqadigan doimiy reklama yozuvi.
FREE_DELIVERY_BANNER = (
    f"🚚 <b>{money(FREE_DELIVERY_MIN)}dan ortiq xaridga — "
    f"shahar ichida yetkazish BEPUL!</b>"
)
# Sellerlarni jalb qilish uchun doimiy ko'rinib turadigan taklif yozuvi.
SELLER_INVITE_BANNER = (
    "🤝 <b>Sellerlarni hamkorlikka taklif qilamiz!</b>\n"
    f"Murojaat: @{settings.ADMIN_USERNAME}"
)


def _shops_keyboard(city: str) -> InlineKeyboardMarkup:
    sellers = get_sellers()
    rows = []
    for uid, s in sellers.items():
        if s.get("city") != city:
            continue
        rating, cnt = get_seller_rating(int(uid))
        stars = f"⭐{rating}" if cnt else ""
        prods = get_seller_products(int(uid))
        suffix = f"  {stars}" if stars else ""
        rows.append([InlineKeyboardButton(
            text=f"🏪 {s['shop_name']}{suffix}  ·  {len(prods)} ta mahsulot",
            callback_data=f"shop_{uid}"
        )])
    rows.append([InlineKeyboardButton(text="📍 Shaharni o'zgartirish", callback_data="changecity")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _city_picker() -> InlineKeyboardMarkup:
    # Rasmdagidek: har qatorda bitta shahar.
    rows = [
        [InlineKeyboardButton(text=c, callback_data=f"bcity_{c}")]
        for c in get_cities()
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ─── 🚀 Start tugmasi (salomlashish xabaridan) ───────────────────────────────
@router.callback_query(F.data == "go_start")
async def go_start(call: CallbackQuery):
    if is_shop_member(call.from_user.id):
        await call.message.answer(
            "🛒 Siz sotuvchisiz. Quyidagi menyudan foydalaning:",
            reply_markup=seller_main_menu
        )
        await call.answer()
        return
    u = get_user(call.from_user.id)
    city = u.get("city") if u else None
    if not city:
        await call.message.answer(
            f"{title('📍', 'Shaharni tanlang')}\n"
            f"{divider()}\n"
            "Iltimos, yashash shahringizni tanlang:",
            parse_mode="HTML", reply_markup=_city_picker()
        )
    else:
        await _show_market(call.message, city)
    await call.answer()


# ─── Ma'lumot (Aloqa) ────────────────────────────────────────────────────────
# Eski "📞 Aloqa" yozuvi ham qabul qilinadi (eski klaviaturasi ochiq foydalanuvchilar uchun).
@router.message(F.text.in_({"ℹ️ Ma'lumot", "📞 Aloqa"}))
async def contact_handler(message: Message):
    info_title = title("ℹ️", "Ma'lumot")
    await message.answer(
        f"{info_title}\n"
        f"{divider()}\n"
        "💬 Savol va takliflar:  @promanmarketbot\n"
        f"👤 Admin:  @{settings.ADMIN_USERNAME}\n"
        "🕘 Ish vaqti:  09:00 – 18:00",
        parse_mode="HTML",
        reply_markup=admin_contact_kb()
    )


# ─── Profil ──────────────────────────────────────────────────────────────────
@router.message(F.text == "👤 Profil")
async def profile_handler(message: Message):
    user = message.from_user
    seller = get_shop_seller(user.id)
    if seller:
        owner_id = get_owner_id(user.id)
        rating, cnt = get_seller_rating(owner_id)
        stars = "⭐" * int(rating) if rating else "—"
        products = get_seller_products(owner_id)
        extra = (
            f"{divider()}\n"
            f"🏪 Do'kon:  {seller['shop_name']}\n"
            f"📦 Mahsulotlar:  {len(products)} ta\n"
            f"⭐ Reyting:  {stars} {rating}  ({cnt} ta baho)\n"
            f"{divider()}\n"
            "/seller — sotuvchi paneli"
        )
        role = "🏪 Sotuvchi" if is_seller(user.id) else "🏪 Sotuvchi (yordamchi)"
    else:
        role  = "🛍 Xaridor"
        u = get_user(user.id)
        city = (u.get("city") if u else None) or "tanlanmagan"
        extra = (
            f"{divider()}\n"
            f"📍 Shahar:  {city}\n"
            f"{divider()}\n"
            f"🤝 Sotuvchi bo'lib hamkorlik qilish uchun adminga yozing: @{settings.ADMIN_USERNAME}"
        )

    await message.answer(
        f"{title('👤', 'Profilingiz')}\n"
        f"{divider()}\n"
        f"🙍 Ism:  {user.full_name}\n"
        f"🔗 Username:  @{user.username or 'yoq'}\n"
        f"🆔 ID:  {user.id}\n"
        f"🎭 Rol:  {role}\n{extra}",
        parse_mode="HTML", reply_markup=admin_contact_kb()
    )


# ─── Market — do'konlar ro'yxati ─────────────────────────────────────────────
# Eski "🛍 Bozor" yozuvi ham qabul qilinadi (eski klaviaturasi ochiq foydalanuvchilar uchun).
@router.message(F.text.in_({"🛒 Market", "🛍 Bozor"}))
async def market_handler(message: Message):
    if is_shop_member(message.from_user.id):
        await message.answer(
            "🛒 Siz sotuvchisiz. Quyidagi menyudan foydalaning:",
            reply_markup=seller_main_menu
        )
        return
    u = get_user(message.from_user.id)
    city = u.get("city") if u else None
    if not city:
        await message.answer(
            f"{title('📍', 'Avval shahringizni tanlang')}\n"
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
        f"{FREE_DELIVERY_BANNER}\n"
        f"{SELLER_INVITE_BANNER}\n"
        f"{divider()}\n"
        f"🛍 <b>Do'konlar</b>   📍 {city}\n"
        "Bitta do'konni tanlang:",
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


async def _send_shop_menu(call: CallbackQuery, seller_id: int):
    """Do'konga kirilganda TO'G'RIDAN-TO'G'RI barcha mahsulotlar ro'yxatini
    yuboradi (bo'limlar menyusisiz): har bir mahsulot nomi + narxi alohida
    tugma (prod_<id>)."""
    chat_id = call.message.chat.id
    await _clear_last_product(call.message.bot, chat_id, [call.message.message_id])

    seller    = get_seller(seller_id)
    shop_name = seller["shop_name"] if seller else "Do'kon"
    rating, cnt = get_seller_rating(seller_id)
    stars = f"   ⭐ {rating} ({cnt})" if cnt else ""

    products = get_seller_products(seller_id)
    if not products:
        await call.message.answer(
            f"{title('🏪', shop_name)}\n{divider()}\n📦 Hozircha mahsulot yo'q.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="‹  Do'konlarga qaytish", callback_data="back_shops")]
            ])
        )
        return

    rows = []
    for p in products:
        name = p.get("name", "—")
        if len(name) > 30:
            name = name[:30].rstrip() + "…"
        finished = "  ·  ❌ Tugagan" if p.get("is_finished") else ""
        rows.append([InlineKeyboardButton(
            text=f"{product_emoji(p)} {name}  ·  {money(p.get('price', 0))}{finished}",
            callback_data=f"prod_{p['id']}"
        )])
    rows.append([InlineKeyboardButton(text="‹  Orqaga", callback_data="back_shops")])

    await call.message.answer(
        f"{title('🏪', shop_name)}{stars}\n{divider()}\n"
        f"📦 {len(products)} ta mahsulot — birini tanlang 👇",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


async def _send_category_products(message: Message, seller_id: int, code: str):
    """Bo'lim mahsulotlarini AVVALGIDEK oddiy ro'yxat qilib yuboradi:
    har bir mahsulot nomi + narxi alohida tugma (prod_<id>)."""
    products  = [p for p in get_seller_products(seller_id) if product_category(p) == code]
    seller    = get_seller(seller_id)
    shop_name = seller["shop_name"] if seller else "Do'kon"
    label     = category_label(code)

    if not products:
        await message.answer(
            f"{title('🏪', shop_name)}\n{divider()}\n{label}: mahsulot qolmadi.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="‹  Orqaga", callback_data=f"shop_{seller_id}")]
            ])
        )
        return

    rows = []
    for p in products:
        name = p.get("name", "—")
        if len(name) > 30:
            name = name[:30].rstrip() + "…"
        finished = "  ·  ❌ Tugagan" if p.get("is_finished") else ""
        rows.append([InlineKeyboardButton(
            text=f"{product_emoji(p)} {name}  ·  {money(p.get('price', 0))}{finished}",
            callback_data=f"prod_{p['id']}"
        )])
    rows.append([InlineKeyboardButton(text="‹  Orqaga", callback_data=f"shop_{seller_id}")])

    await message.answer(
        f"{title('🏪', shop_name)}   {label}\n{divider()}\n"
        f"📦 {len(products)} ta mahsulot — birini tanlang 👇",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@router.callback_query(F.data.startswith("cat_"))
async def show_category(call: CallbackQuery):
    parts = call.data.split("_", 2)
    if len(parts) < 3:
        await call.answer("Topilmadi."); return
    seller_id, code = int(parts[1]), parts[2]
    if not get_seller(seller_id):
        await call.answer("Do'kon topilmadi."); return
    await call.answer()
    await _clear_last_product(call.message.bot, call.message.chat.id,
                              [call.message.message_id])
    await _send_category_products(call.message, seller_id, code)


@router.callback_query(F.data.startswith("shop_"))
async def show_shop(call: CallbackQuery):
    uid = int(call.data.split("_")[1])
    if not get_seller(uid):
        await call.answer("Do'kon topilmadi."); return
    await call.answer()
    await _send_shop_menu(call, uid)


@router.callback_query(F.data == "back_shops")
async def back_to_shops(call: CallbackQuery):
    # Lentadagi barcha mahsulot xabarlarini tozalab, do'konlar ro'yxatini qaytaramiz.
    await call.answer()
    chat_id = call.message.chat.id
    await _clear_last_product(call.message.bot, chat_id, [call.message.message_id])
    u = get_user(call.from_user.id)
    city = (u.get("city") if u else None)
    if not city:
        await call.message.answer("📍 Shaharingizni tanlang:", reply_markup=_city_picker())
        return
    await call.message.answer(
        f"🛍 <b>Do'konlar</b>   📍 {city}\nBitta do'konni tanlang:",
        parse_mode="HTML", reply_markup=_shops_keyboard(city)
    )


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
    lines.append(title(product_emoji(p), name))
    lines.append(f"🏪 {shop}" + (f"  ·  📍 {city}" if city else ""))

    # Narx qatori
    price_line = f"💰 <b>{money(price)}</b>"
    if disc_pct:
        price_line += f"   <b>−{disc_pct}%</b>"
    if old_price and disc_pct:
        price_line += f"   <s>{money(old_price)}</s>"
    lines.append(price_line)

    if p.get("is_finished"):
        lines.append("❌ <b>Mahsulot tugagan</b> — hozircha buyurtma qilib bo'lmaydi")

    if desc:
        lines.append(f"{divider()}\n📝 {desc}")

    # Reyting
    if rev_cnt:
        stars = "⭐" * min(int(rating), 5)
        lines.append(f"{divider()}\n{stars} {rating}  ·  💬 {rev_cnt} ta sharh")

    lines.append(divider())
    if price >= FREE_DELIVERY_MIN:
        lines.append("🚚 <b>Shahar ichida BEPUL yetkazib berish!</b>")
    else:
        lines.append(f"🚚 {money(FREE_DELIVERY_MIN)}dan ortiq xaridga yetkazish bepul")
    lines.append("🚕 Bugun yetkazamiz  ·  🚶 O'zingiz olib ketishingiz mumkin")
    return "\n".join(lines)


def _product_kb(p: dict, user_id: int) -> InlineKeyboardMarkup:
    """Mahsulot xabari uchun tugmalar: buyurtma, istaklar (❤️) va orqaga."""
    if is_favorite(user_id, p["id"]):
        fav_text = "💔 Istaklardan olib tashlash"
    else:
        fav_text = "❤️ Istaklarimga qo'shish"
    rows = []
    if not p.get("is_finished"):
        rows.append([InlineKeyboardButton(text="🛒  Buyurtma berish", callback_data=f"order_{p['id']}")])
    rows.append([InlineKeyboardButton(text=fav_text, callback_data=f"fav_{p['id']}")])
    rows.append([InlineKeyboardButton(
        text="‹  Orqaga",
        callback_data=f"shop_{p['seller_id']}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# chat_id -> hozir ko'rsatilgan mahsulotning barcha xabar id'lari (albom rasmlari + tugmalar).
# Yangi mahsulot ochilganda hammasini o'chiramiz — chatda bir vaqtda faqat bitta
# mahsulot rasmlari turadi, shunda Telegram rasm ko'ruvchisida (surganda) boshqa
# mahsulot rasmlari aralashib ketmaydi (qaysi yo'l bilan ochilganidan qat'i nazar).
# Bu ma'lumot diskda (storage) saqlanadi — bot qayta ishga tushganda ham eski
# rasmlarni o'chira olishi uchun (set_view_msgs / pop_view_msgs).


async def _delete_msgs(bot, chat_id: int, ids: list):
    """Xabarlarni parallel o'chiradi. Har bir o'chirish alohida API chaqiruv —
    ketma-ket kutish 10 ta rasm uchun bir necha soniya olardi, parallel esa
    bitta chaqiruv vaqtida tugaydi."""
    if not ids:
        return
    await asyncio.gather(
        *(bot.delete_message(chat_id, mid) for mid in ids),
        return_exceptions=True,
    )


async def _clear_last_product(bot, chat_id: int, extra_ids: list | None = None):
    await _delete_msgs(bot, chat_id, pop_view_msgs(chat_id) + list(extra_ids or []))


@router.callback_query(F.data.startswith("prod_"))
async def product_detail(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Topilmadi."); return
    # Tugma spinnerini darhol o'chiramiz — qolgan ishlar (o'chirish, rasm
    # yuborish) foydalanuvchini kuttirmasin.
    await call.answer()

    text    = _product_caption(p)
    photos  = product_photos(p)
    kb      = _product_kb(p, call.from_user.id)
    chat_id = call.message.chat.id

    # Oldingi mahsulot xabarlarini (albom + tugmalar) va bosilgan xabarni
    # (do'kon ro'yxati / qidiruv natijasi) parallel o'chiramiz. Bu yerda
    # pop_view_msgs o'rniga get_view_msgs — yangi holat baribir pastda
    # set_view_msgs bilan yoziladi (bitta diskka yozish yetadi).
    await _delete_msgs(
        call.message.bot, chat_id,
        get_view_msgs(chat_id) + [call.message.message_id],
    )

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

    set_view_msgs(chat_id, ids)


# ─── ❤️ Istaklar (sevimli mahsulotlar) ───────────────────────────────────────
@router.callback_query(F.data.startswith("fav_"))
async def toggle_fav(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    added = toggle_favorite(call.from_user.id, pid)
    await call.answer(
        "❤️ Istaklarimga qo'shildi!" if added else "💔 Istaklardan olib tashlandi."
    )
    # Tugma yozuvini yangi holatga moslab yangilaymiz
    try:
        await call.message.edit_reply_markup(
            reply_markup=_product_kb(p, call.from_user.id)
        )
    except Exception:
        pass


@router.message(F.text == "❤️ Istaklarim")
async def favorites_handler(message: Message):
    favs = get_favorites(message.from_user.id)
    products = [p for p in (get_product_by_id(pid) for pid in favs) if p]
    if not products:
        await message.answer(
            f"{title('❤️', 'Istaklarim')}\n"
            f"{divider()}\n"
            "Hozircha bo'sh.\n"
            "Mahsulot sahifasidagi ❤️ tugmasi bilan yoqqan mahsulotlarni saqlang!",
            parse_mode="HTML",
            reply_markup=menu_for(message.from_user.id)
        )
        return
    rows = [
        [InlineKeyboardButton(
            text=f"{product_emoji(p)} {p['name']}  ·  {money(p['price'])}"
                 f"{'  ·  ❌ Tugagan' if p.get('is_finished') else ''}",
            callback_data=f"prod_{p['id']}"
        )]
        for p in products
    ]
    await message.answer(
        f"{title('❤️', 'Istaklarim')}\n"
        f"{divider()}\n"
        f"Saqlangan mahsulotlaringiz:  {len(products)} ta\n"
        "Ochish uchun mahsulotni tanlang:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


# ─── Buyurtma qilish: rang tanlash (agar ranglar bo'lsa) ───────────────────────
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


# ─── Buyurtma qilish: 0) olib ketish usuli (o'zi / yetkazib berish) ─────────────
async def _ask_fulfillment(message: Message, state: FSMContext, p: dict):
    await state.set_state(OrderState.fulfillment)
    await state.update_data(pid=p["id"])
    data = await state.get_data()
    qty   = data.get("quantity", 1)
    total = p["price"] * qty
    color_line = f"🎨 Rang: <b>{data['selected_color']}</b>\n" if data.get("selected_color") else ""
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚶 O'zim olib ketaman", callback_data="flf_pickup")],
        [InlineKeyboardButton(text="🚚 Menga yetkazib berilsin", callback_data="flf_delivery")],
    ])
    await message.answer(
        f"🛒 <b>{p['name']}</b>\n"
        f"🔢 Miqdor: {qty} dona\n"
        f"💰 Jami: <b>{total:,} so'm</b>\n"
        f"{color_line}\n"
        f"Mahsulotni qanday olmoqchisiz?",
        parse_mode="HTML", reply_markup=kb
    )


# ─── Buyurtma qilish: miqdor (nechta dona) ───────────────────────────────────
def _qty_text(p: dict, qty: int) -> str:
    total = p["price"] * qty
    return (
        f"🔢 <b>{p['name']}</b>\n"
        f"Nechta dona olmoqchisiz?\n\n"
        f"Miqdor: <b>{qty} dona</b>\n"
        f"💰 Jami: <b>{total:,} so'm</b>"
    )


def _qty_kb(qty: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖",          callback_data=f"qset_{max(1, qty - 1)}"),
            InlineKeyboardButton(text=f"{qty} dona", callback_data="noop"),
            InlineKeyboardButton(text="➕",          callback_data=f"qset_{min(99, qty + 1)}"),
        ],
        [InlineKeyboardButton(text="✅ Davom etish", callback_data=f"qok_{qty}")],
    ])


@router.callback_query(F.data.startswith("order_"))
async def start_order(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    if p.get("is_finished"):
        await call.answer("❌ Mahsulot tugagan. Hozircha buyurtma qilib bo'lmaydi.", show_alert=True)
        return
    await state.clear()
    await state.update_data(pid=pid)
    await state.set_state(OrderState.quantity)
    await call.message.answer(_qty_text(p, 1), parse_mode="HTML", reply_markup=_qty_kb(1))
    await call.answer()


@router.callback_query(OrderState.quantity, F.data.startswith("qset_"))
async def order_qty_set(call: CallbackQuery, state: FSMContext):
    qty  = max(1, min(99, int(call.data.split("_")[1])))
    data = await state.get_data()
    p = get_product_by_id(data.get("pid"))
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    try:
        await call.message.edit_text(_qty_text(p, qty), parse_mode="HTML", reply_markup=_qty_kb(qty))
    except Exception:
        pass
    await call.answer()


@router.callback_query(OrderState.quantity, F.data.startswith("qok_"))
async def order_qty_ok(call: CallbackQuery, state: FSMContext):
    qty = max(1, min(99, int(call.data.split("_")[1])))
    await state.update_data(quantity=qty)
    data = await state.get_data()
    p = get_product_by_id(data.get("pid"))
    if not p:
        await call.answer("Mahsulot topilmadi."); return
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


# ─── 0b) Yetkazib berish → pochta usulini tanlash bosqichiga o'tamiz ─────────
@router.callback_query(OrderState.fulfillment, F.data == "flf_delivery")
async def fulfillment_delivery(call: CallbackQuery, state: FSMContext):
    await state.update_data(fulfillment="delivery")
    await state.set_state(OrderState.delivery)
    data = await state.get_data()
    p = get_product_by_id(data.get("pid"))
    total = (p.get("price", 0) * data.get("quantity", 1)) if p else 0
    free = total >= FREE_DELIVERY_MIN
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚕 Taksi pochta (shu bugunoq)", callback_data="dlv_taxi")],
    ])
    if free:
        note = (
            f"✅ <b>Shahar ichida yetkazib berish BEPUL!</b>\n"
            f"<i>Xaridingiz {FREE_DELIVERY_MIN:,} so'mdan ortiq — shahar ichidagi taksi "
            f"haqini do'kon o'zi qoplaydi.</i>"
        )
    else:
        note = (
            f"ℹ️ <i>Eslatma: taksi (yetkazib berish) haqi xaridor tomonidan "
            f"to'lanadi va masofaga qarab belgilanadi. Mahsulot narxiga "
            f"kirmaydi — taksi haqini yetkazilganda haydovchiga to'laysiz.\n"
            f"({FREE_DELIVERY_MIN:,} so'mdan ortiq xaridga shahar ichida yetkazib berish bepul.)</i>"
        )
    await call.message.answer(
        "🚚 <b>Yetkazib berish usulini tanlang:</b>\n\n"
        "🚕 <b>Taksi pochta</b> — mahsulot shu bugunoq taksi orqali "
        "manzilingizga yetkaziladi.\n\n"
        f"{note}",
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
        f"{title('📍', 'Manzilni kiriting')}\n"
        f"{divider()}\n"
        "Iltimos, yetkazib berish manzilingizni kiriting\n"
        "(shahar, ko'cha, uy — to'liq yozing):",
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
    if p.get("is_finished"):
        await state.clear()
        await message.answer(
            "❌ Afsuski, bu mahsulot hozirgina tugadi. Buyurtma qabul qilinmadi.",
            reply_markup=main_menu
        )
        return

    qty   = data.get("quantity", 1)
    total = p["price"] * qty
    commission = int(total * settings.COMMISSION_RATE)
    order_id = save_order({
        "buyer_id":     message.from_user.id,
        "buyer_name":   message.from_user.full_name,
        "buyer_username": message.from_user.username,
        "seller_id":    p["seller_id"],
        "product_id":   pid,
        "product_name": p["name"],
        "quantity":     qty,
        "unit_price":   p["price"],
        "total":        total,
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
    is_free_delivery = (not is_pickup) and total >= FREE_DELIVERY_MIN
    delivery_refund  = int(total * DELIVERY_REFUND_RATE) if is_free_delivery else 0
    seller_card      = (get_seller(p["seller_id"]) or {}).get("card_number", "")
    seller_dlv_note = (
        "\n🚚 <b>Bu buyurtmada yetkazib berish XARIDOR uchun BEPUL.</b>\n"
        "⚠️ Taksi (yetkazib berish) haqini <b>SIZ haydovchiga to'laysiz</b>.\n"
        f"💸 Platforma sizga <b>5% ({delivery_refund:,} so'm)</b> kartangizga qaytaradi "
        "(taksi haqini qoplash uchun).\n"
        if is_free_delivery else ""
    )
    owner_free_note = (
        f"\n🚚 <b>BEPUL YETKAZIB BERISH buyurtmasi</b>\n"
        f"➡️ Sellerga <b>5% ({delivery_refund:,} so'm)</b> o'tkazing (taksi haqini qoplash):\n"
        f"💳 Seller kartasi: <code>{seller_card or '—'}</code>\n"
        if is_free_delivery else ""
    )

    # ── Xaridorga: oldi-to'lov PLATFORMA kartasiga ──
    if is_pickup:
        deliver_line = (
            f"🚶 Olish usuli: O'zingiz olib ketasiz\n"
            f"<b>🔵 To'lov tasdiqlangach do'kon bilan bog'lanasiz.</b>\n\n"
        )
    elif total >= FREE_DELIVERY_MIN:
        deliver_line = (
            f"🚚 Yetkazib berish: {dlv_label}\n"
            f"📍 Manzil: {data['address']}\n"
            f"📱 Tel: {phone}\n"
            f"<b>🟢 Yetkazib berish: SHU BUGUNOQ (taksi pochta)</b>\n"
            f"<b>✅ Shahar ichida yetkazib berish — BEPUL!</b>\n"
            f"<i>(Xaridingiz {FREE_DELIVERY_MIN:,} so'mdan ortiq — shahar ichidagi "
            f"taksi haqini do'kon qoplaydi.)</i>\n\n"
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
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>  (#{order_id})\n"
        f"Boshlang'ich <b>{pct}%</b> to'lovni qiling.\n"
        f"{divider()}\n"
        f"📦 Mahsulot:  {p['name']}\n"
        f"🔢 Miqdor:  {qty} dona × {money(p['price'])}\n"
        f"💰 Narxi:  <b>{money(total)}</b>\n"
        f"💳 Oldindan to'lov ({pct}%):  <b>{money(commission)}</b>\n"
        f"➡️ Karta:  <code>{platform_card}</code>\n"
        f"{card_name_line}"
        f"{divider()}\n"
        f"{deliver_line}"
        f"🧾 <b>To'lov chekining rasmini (skrinshot) shu yerga yuboring.</b>\n"
        f"Chek tasdiqlangach buyurtmangiz tayyorlanadi.\n"
        f"❓ Muammo bo'lsa — admin: @{settings.ADMIN_USERNAME}",
        parse_mode="HTML", reply_markup=cancel_keyboard
    )

    # ── Sellerga: faqat MAHSULOT haqida. Xaridor kontakti YASHIRIN! ──
    # Telefon/manzil faqat admin 10% to'lovni tasdiqlagandan keyin ochiladi.
    # Bu seller bilan xaridor to'g'ridan-to'g'ri kelishib, komissiyani
    # chetlab o'tishining oldini oladi.
    from app.bot.bot import bot
    seller_msg = (
        f"🛒 <b>Yangi buyurtma #{order_id}!</b>\n\n"
        f"📦 {p['name']}\n"
        f"🔢 Miqdor: {qty} dona × {p['price']:,} so'm\n"
        f"💰 Jami: {total:,} so'm\n"
        f"🚚 {dlv_label}\n"
        f"{seller_dlv_note}\n"
        f"🔒 <b>Xaridor ma'lumotlari (ism, tel, manzil) yashirin.</b>\n"
        f"Platforma to'lovi (oldi-to'lov) tasdiqlangach avtomatik ochiladi.\n\n"
        f"💡 <b>Eslatma:</b> Bot orqali sotilgan har bir buyurtma uchun "
        f"mahsulot narxining {pct}% qismi platforma xizmat haqi sifatida olinadi.\n"
        f"Bu summa ({commission:,} so'm) xaridorning oldi-to'lovidan to'g'ridan-to'g'ri "
        f"platformaga o'tadi — sizdan keyinchalik alohida hech narsa so'ralmaydi. "
        f"Hamkorligingiz uchun rahmat! 🙏\n\n"
        f"⏳ Holat: to'lov tasdig'i kutilmoqda.\n"
        f"Buyurtmalar: /orders"
    )
    # Do'kon egasi + yordamchilarga yuboriladi
    for nid in shop_notify_ids(p["seller_id"]):
        try:
            await bot.send_message(nid, seller_msg, parse_mode="HTML")
        except Exception:
            pass

    # ── Adminga: yangi buyurtma xabari (to'liq) ──
    try:
        from app.bot.bot import bot
        await bot.send_message(
            settings.OWNER_ID,
            f"🆕 <b>Yangi buyurtma #{order_id}</b>\n\n"
            f"📦 {p['name']}\n"
            f"🔢 {qty} dona × {p['price']:,} = <b>{total:,} so'm</b>\n"
            f"💵 Komissiya ({pct}%): {commission:,} so'm\n"
            f"👤 {message.from_user.full_name} (ID: {message.from_user.id})\n"
            f"📱 {phone}\n"
            f"📍 {data['address']}\n"
            f"🚚 {dlv_label}\n"
            f"{owner_free_note}\n"
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
        f"🧾 Chek qabul qilindi! Buyurtma #{order_id} to'lovi tekshirilmoqda.\n"
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
        f"🧾 <b>Buyurtma #{order_id} — to'lov cheki</b>\n\n"
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


# ─── Buyurtmalarim ──────────────────────────────────────────────────────────────
@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders(message: Message):
    if is_shop_member(message.from_user.id):
        await message.answer(
            "🛒 Siz sotuvchisiz. Buyurtmalarni 🛒 Sotuvchi paneli orqali ko'ring:",
            reply_markup=seller_main_menu
        )
        return
    orders = get_buyer_orders(message.from_user.id)
    if not orders:
        await message.answer("📦 Hozircha buyurtma yo'q.")
        return
    text = "📦 <b>Buyurtmalaringiz:</b>\n\n"
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
        f"🧾 Buyurtma #{oid} uchun to'lov chekining rasmini yuboring:",
        reply_markup=cancel_keyboard
    )
    await call.answer()


# ─── Qidirish ────────────────────────────────────────────────────────────────
@router.message(F.text == "🔎 Qidirish")
async def search_start(message: Message, state: FSMContext):
    if is_shop_member(message.from_user.id):
        await message.answer(
            "🛒 Siz sotuvchisiz. Quyidagi menyudan foydalaning:",
            reply_markup=seller_main_menu
        )
        return
    await state.set_state(SearchState.query)
    await message.answer("🔍 Mahsulot nomini kiriting:")


@router.message(SearchState.query)
async def do_search(message: Message, state: FSMContext):
    await state.clear()
    # Oldin ochilgan mahsulot albomini tozalaymiz (chatda rasmlar aralashmasligi uchun).
    await _clear_last_product(message.bot, message.chat.id)
    results = search_products(message.text or "")
    if not results:
        await message.answer("😔 Hech narsa topilmadi. Boshqa so'z bilan sinab ko'ring.", reply_markup=main_menu)
        return

    await message.answer(
        f"🔍 <b>{len(results)} ta natija topildi</b>",
        parse_mode="HTML"
    )

    # Qidiruvda yuborilgan rasm xabarlarini kuzatamiz — keyin mahsulot/do'kon
    # ochilganda ular ham o'chiriladi (Telegram ko'ruvchisida aralashmasligi uchun).
    photo_ids = []
    for p in results[:5]:
        caption = _product_caption(p)
        kb_rows = []
        if not p.get("is_finished"):
            kb_rows.append([InlineKeyboardButton(text="🛒 Buyurtma qilish", callback_data=f"order_{p['id']}")])
        kb_rows.append([InlineKeyboardButton(text="🔍 Batafsil", callback_data=f"prod_{p['id']}")])
        kb = InlineKeyboardMarkup(inline_keyboard=kb_rows)
        photos = product_photos(p)
        if photos:
            try:
                sent = await message.answer_photo(photos[0], caption=caption, parse_mode="HTML", reply_markup=kb)
                photo_ids.append(sent.message_id)
                continue
            except Exception:
                pass
        await message.answer(caption, parse_mode="HTML", reply_markup=kb)

    if photo_ids:
        set_view_msgs(message.chat.id, photo_ids)

    if len(results) > 5:
        rows = []
        for p in results[5:15]:
            price = p.get("price", 0)
            old   = p.get("old_price", 0)
            disc  = f" ↓{round((old-price)/old*100)}%" if old and old > price else ""
            rows.append([InlineKeyboardButton(
                text=f"{product_emoji(p)} {p['name']} — {price:,} so'm{disc}",
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
