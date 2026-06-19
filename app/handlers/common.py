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
    get_user, set_user_field, get_cities, product_photos, product_video,
    set_view_msgs, pop_view_msgs, get_view_msgs,
    get_favorites, is_favorite, toggle_favorite,
    is_shop_member, get_shop_seller, get_owner_id, shop_notify_ids,
    product_stock, validate_promo, use_promo,
)
from app.keyboards.seller import (
    main_menu, seller_main_menu, menu_for, phone_keyboard, cancel_keyboard,
    admin_contact_kb,
)
from app.states.seller_application import SearchState, OrderState
from app.app.config.settings import settings
from app.ui import (
    money, divider, title, category_label, product_category,
    product_emoji, product_sort_key, product_group_label,
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

# Yetkazib berish narxi — qat'iy belgilangan (har bir buyurtma uchun bir xil).
DELIVERY_FEE = 19_000
# Shu summadan yuqori (va teng) xaridlarga yetkazib berish bepul.
FREE_DELIVERY_THRESHOLD = 300_000


def delivery_fee_for(total: int) -> int:
    """Yetkazish narxi: xarid 300 000 so'mdan yuqori bo'lsa bepul (0)."""
    return 0 if total >= FREE_DELIVERY_THRESHOLD else DELIVERY_FEE


def delivery_text(fee: int) -> str:
    """Yetkazish narxini chiroyli matnga aylantiradi (bepul bo'lsa — BEPUL)."""
    return "BEPUL 🎉" if fee == 0 else money(fee)


# Xaridorni qiziqtirish uchun har joyda chiqadigan doimiy reklama yozuvi.
FREE_DELIVERY_BANNER = (
    f"🚚 <b>Yetkazib berish — atigi {money(DELIVERY_FEE)}!</b>\n"
    f"🎉 <b>{money(FREE_DELIVERY_THRESHOLD)} dan yuqori xaridga — BEPUL!</b>\n"
    f"Bugun buyurtma bering — bugun yetkazamiz."
)
# Sellerlarni jalb qilish uchun doimiy ko'rinib turadigan taklif yozuvi.
SELLER_INVITE_BANNER = (
    "🤝 <b>Sellerlarni hamkorlikka taklif qilamiz!</b>\n"
    f"Murojaat: @{settings.ADMIN_USERNAME}"
)


def _city_sellers(city: str) -> list[tuple[str, dict]]:
    """Shu shahardagi sellerlar ro'yxati (uid, yozuv) — tartibi saqlangan holda.
    Matn ro'yxati va tugmalar BIR XIL ketma-ketlikda bo'lishi uchun ishlatiladi."""
    return [(uid, s) for uid, s in get_sellers().items() if s.get("city") == city]


def _shops_keyboard(sellers: list[tuple[str, dict]]) -> InlineKeyboardMarkup:
    # Admin panelidagidek (admin_menu_kb) — bir ustunli, toza kartochkalar.
    # Har bir do'kon tugmasi faqat nomdan iborat; reyting/mahsulot soni
    # yuqoridagi matn ro'yxatida ko'rsatiladi (_show_market).
    rows = [
        [InlineKeyboardButton(text=f"🏪 {s['shop_name']}", callback_data=f"shop_{uid}")]
        for uid, s in sellers
    ]
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
    sellers = _city_sellers(city)
    if not sellers:
        await message.answer(
            f"🛒 <b>{city}</b> shahrida hozircha do'kon yo'q.\n"
            "Boshqa shaharni tanlashingiz mumkin:",
            parse_mode="HTML", reply_markup=_city_picker()
        )
        return
    # Reyting va mahsulot soni endi tugmada emas — bu yerda raqamlangan
    # ro'yxatda. Tartib tugmalar bilan bir xil (ikkalasi ham `sellers` dan).
    lines = []
    for i, (uid, s) in enumerate(sellers, 1):
        rating, cnt = get_seller_rating(int(uid))
        prods = get_seller_products(int(uid))
        meta = f"⭐{rating} · {len(prods)} ta mahsulot" if cnt else f"{len(prods)} ta mahsulot"
        lines.append(f"{i}. 🏪 {s['shop_name']} — {meta}")
    await message.answer(
        f"{FREE_DELIVERY_BANNER}\n"
        f"{SELLER_INVITE_BANNER}\n"
        f"{divider()}\n"
        f"🛍 <b>Do'konlar</b>   📍 {city}\n"
        + "\n".join(lines) + "\n"
        f"{divider()}\n"
        "Bitta do'konni tanlang:",
        parse_mode="HTML",
        reply_markup=_shops_keyboard(sellers)
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


# Bitta xabardagi (inline-klaviaturadagi) mahsulotlar soni. Telegram bitta
# klaviaturaga juda ko'p tugmani qabul qilmaydi (mahsulot 100 dan oshsa menyu
# ochilmay qoladi). Shuning uchun "▶️ keyingi sahifa" tugmasi O'RNIGA mahsulotlar
# ketma-ket bir nechta xabarga bo'lib yuboriladi — foydalanuvchi shunchaki pastga
# aylantirib, BITTA UZUN RO'YXATdek ko'radi (hech qanday sahifa tugmasini bosmaydi).
_SHOP_PER_PAGE = 40


def _shop_menu_chunks(seller_id: int):
    """(sarlavha_matni, [klaviatura, ...]) — do'kon mahsulotlarining BUTUN ro'yxati,
    har biri ≤_SHOP_PER_PAGE tugmali bo'laklarga bo'lingan holda.

    Bo'laklar ketma-ket alohida xabar bo'lib yuboriladi, shu sababli sahifalash
    (◀️/▶️) tugmalari KERAK EMAS — ro'yxat uzluksiz ko'rinadi."""
    seller    = get_seller(seller_id)
    shop_name = seller["shop_name"] if seller else "Do'kon"
    rating, cnt = get_seller_rating(seller_id)
    stars = f"   ⭐ {rating} ({cnt})" if cnt else ""

    products = get_seller_products(seller_id)
    if not products:
        return (
            f"{title('🏪', shop_name)}\n{divider()}\n📦 Hozircha mahsulot yo'q.",
            [InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="‹  Do'konlarga qaytish", callback_data="back_shops")]
            ])]
        )

    # Mahsulotlarni KATEGORIYA bo'yicha guruhlaymiz — aralash chiqmasligi uchun
    # (konditsionerlar ketma-ket, kir yuvishlar ketma-ket). Har kategoriya ichida
    # ARZONIDAN QIMMATIGA (narx bo'yicha) tartiblanadi. Har guruh boshida
    # chiroyli sarlavha (bosilmaydigan) ko'rsatiladi.
    products = sorted(products, key=lambda p: (product_sort_key(p), p.get("price", 0)))

    total = len(products)
    rows = []
    cur_group = object()
    for p in products:
        grp = product_sort_key(p)
        if grp != cur_group:
            cur_group = grp
            rows.append([InlineKeyboardButton(
                text=f"➖➖  {product_emoji(p)} {product_group_label(p)}  ➖➖",
                callback_data="noop"
            )])
        name = p.get("name", "—")
        if len(name) > 30:
            name = name[:30].rstrip() + "…"
        finished = "  ·  ❌ Tugagan" if p.get("is_finished") else ""
        rows.append([InlineKeyboardButton(
            text=f"{product_emoji(p)} {name}  ·  {money(p.get('price', 0))}{finished}",
            callback_data=f"prod_{p['id']}"
        )])

    # Tugmalarni ≤_SHOP_PER_PAGE talik bo'laklarga ajratamiz.
    chunks = [rows[i:i + _SHOP_PER_PAGE] for i in range(0, len(rows), _SHOP_PER_PAGE)]
    # "‹ Orqaga" tugmasi faqat oxirgi bo'lakda.
    chunks[-1].append([InlineKeyboardButton(text="‹  Orqaga", callback_data="back_shops")])
    keyboards = [InlineKeyboardMarkup(inline_keyboard=c) for c in chunks]

    text = (f"{title('🏪', shop_name)}{stars}\n{divider()}\n"
            f"📦 {total} ta mahsulot — birini tanlang 👇")
    return text, keyboards


async def _send_shop_menu(call: CallbackQuery, seller_id: int):
    """Do'konga kirilganda BARCHA mahsulotlarni uzluksiz (sahifa tugmasisiz)
    ketma-ket xabarlar bilan yuboradi."""
    chat_id = call.message.chat.id
    await _clear_last_product(call.message.bot, chat_id, [call.message.message_id])
    text, keyboards = _shop_menu_chunks(seller_id)
    # Birinchi bo'lak — sarlavha bilan; qolganlari "davomi" bilan.
    await call.message.answer(text, parse_mode="HTML", reply_markup=keyboards[0])
    for kb in keyboards[1:]:
        await call.message.answer("📦 …davomi", reply_markup=kb)


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

    # Bo'lim ichida arzonidan qimmatiga tartiblaymiz.
    products = sorted(products, key=lambda p: p.get("price", 0))
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
    await _show_market(call.message, city)


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
    else:
        stock = product_stock(p)
        # Kam qolganda xaridorni shoshirtirish uchun ogohlantiramiz.
        if stock is not None and stock <= 5:
            lines.append(f"🔥 <b>Shoshiling — atigi {stock} dona qoldi!</b>")

    if desc:
        lines.append(f"{divider()}\n📝 {desc}")

    # Rasm haqida ogohlantirish — ba'zi rasmlar mahsulotga o'xshash, lekin aynan
    # shu rasmdagi mahsulot bo'lmasligi mumkin (xaridor noto'g'ri kutmasligi uchun).
    lines.append(
        "ℹ️ <i>Eslatma: rasm namunaviy bo'lishi mumkin — mahsulot rasmga "
        "o'xshash, lekin aynan shu rasmdagi bo'lmasligi mumkin.</i>"
    )

    # Reyting
    if rev_cnt:
        stars = "⭐" * min(int(rating), 5)
        lines.append(f"{divider()}\n{stars} {rating}  ·  💬 {rev_cnt} ta sharh")

    lines.append(divider())
    # Yetkazib berish narxi mahsulot narxiga qarab: 300 000 dan yuqori — BEPUL,
    # aks holda 19 000 so'm.
    fee = delivery_fee_for(price)
    lines.append(f"🚚 Yetkazib berish: <b>{delivery_text(fee)}</b>  ·  🚕 Bugun yetkazamiz")
    if fee:
        # Hali bepulga yetmagan — xaridorni rag'batlantirish uchun eslatma.
        lines.append(f"🎉 <b>{money(FREE_DELIVERY_THRESHOLD)} dan yuqori xaridga — BEPUL</b>")
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

    # Qisqa video (bo'lsa) — rasmlardan keyin alohida yuboriladi.
    video = product_video(p)
    if video:
        try:
            vmsg = await call.message.answer_video(video, caption=f"🎬 {p.get('name','')}")
            ids.append(vmsg.message_id)
        except Exception:
            pass

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
        await _start_delivery(message, state, p)
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
    await _start_delivery(call.message, state, p)
    await call.answer()


# ─── Buyurtma qilish: yetkazib berish (yagona usul) → manzil so'raymiz ─────────
def _unit_price(p: dict, data: dict) -> int:
    """Mahsulotning chegirmali birlik narxi (promo-kod qo'llangan bo'lsa)."""
    price = p.get("price", 0)
    pct = int(data.get("promo_percent", 0) or 0)
    return int(price * (100 - pct) / 100) if pct else price


async def _start_delivery(message: Message, state: FSMContext, p: dict):
    """Endi yagona usul — yetkazib berish (19 000 so'm). Pickup olib tashlangan."""
    await state.update_data(pid=p["id"], fulfillment="delivery", delivery="taxi")
    await state.set_state(OrderState.address)
    data = await state.get_data()
    qty   = data.get("quantity", 1)
    unit  = _unit_price(p, data)
    total = unit * qty
    fee   = delivery_fee_for(total)
    color_line = f"🎨 Rang: <b>{data['selected_color']}</b>\n" if data.get("selected_color") else ""
    promo_line = ""
    if data.get("promo_percent"):
        full = p.get("price", 0) * qty
        promo_line = (
            f"🎁 Promo <b>{data['promo_code']}</b>: −{data['promo_percent']}%  "
            f"(<s>{full:,}</s> → <b>{total:,}</b>)\n"
        )
    await message.answer(
        f"🛒 <b>{p['name']}</b>\n"
        f"🔢 Miqdor: {qty} dona\n"
        f"{promo_line}"
        f"💰 Jami: <b>{total:,} so'm</b>\n"
        f"{color_line}"
        f"🚚 Yetkazib berish: <b>{delivery_text(fee)}</b>\n\n"
        f"📍 <b>Yetkazib berish manzilingizni kiriting</b>\n"
        f"(shahar, ko'cha, uy — to'liq yozing):",
        parse_mode="HTML", reply_markup=cancel_keyboard
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


def _max_qty(p: dict) -> int:
    """Buyurtma uchun ruxsat etilgan eng ko'p miqdor (zaxiraga qarab, ≤99)."""
    s = product_stock(p)
    return min(99, s) if (s is not None and s > 0) else 99


def _qty_kb(qty: int, max_qty: int = 99) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖",          callback_data=f"qset_{max(1, qty - 1)}"),
            InlineKeyboardButton(text=f"{qty} dona", callback_data="noop"),
            InlineKeyboardButton(text="➕",          callback_data=f"qset_{min(max_qty, qty + 1)}"),
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
    mx = _max_qty(p)
    await call.message.answer(_qty_text(p, 1), parse_mode="HTML", reply_markup=_qty_kb(1, mx))
    await call.answer()


@router.callback_query(OrderState.quantity, F.data.startswith("qset_"))
async def order_qty_set(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    p = get_product_by_id(data.get("pid"))
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    mx = _max_qty(p)
    qty  = max(1, min(mx, int(call.data.split("_")[1])))
    try:
        await call.message.edit_text(_qty_text(p, qty), parse_mode="HTML", reply_markup=_qty_kb(qty, mx))
    except Exception:
        pass
    await call.answer()


@router.callback_query(OrderState.quantity, F.data.startswith("qok_"))
async def order_qty_ok(call: CallbackQuery, state: FSMContext):
    data0 = await state.get_data()
    p0 = get_product_by_id(data0.get("pid"))
    mx = _max_qty(p0) if p0 else 99
    qty = max(1, min(mx, int(call.data.split("_")[1])))
    await state.update_data(quantity=qty)
    data = await state.get_data()
    p = get_product_by_id(data.get("pid"))
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    await _ask_promo(call.message, state, p)
    await call.answer()


# ─── Buyurtma qilish: promo-kod (ixtiyoriy) ──────────────────────────────────
def _promo_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Promo-kodim yo'q", callback_data="promoskip")],
    ])


async def _ask_promo(message: Message, state: FSMContext, p: dict):
    await state.set_state(OrderState.promo)
    await state.update_data(pid=p["id"])
    await message.answer(
        "🎁 <b>Promo-kodingiz bo'lsa yuboring</b> — chegirma qo'llanadi.\n"
        "Bo'lmasa pastdagi tugmani bosing.",
        parse_mode="HTML", reply_markup=_promo_skip_kb()
    )


async def _after_promo(message: Message, state: FSMContext):
    data = await state.get_data()
    p = get_product_by_id(data.get("pid"))
    if not p:
        await state.clear()
        await message.answer("❌ Mahsulot topilmadi.", reply_markup=main_menu)
        return
    await _ask_color(message, state, p)


@router.callback_query(OrderState.promo, F.data == "promoskip")
async def order_promo_skip(call: CallbackQuery, state: FSMContext):
    await call.answer()
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _after_promo(call.message, state)


@router.message(OrderState.promo, F.text == "❌ Bekor qilish")
async def order_promo_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Buyurtma bekor qilindi.", reply_markup=main_menu)


@router.message(OrderState.promo)
async def order_promo_enter(message: Message, state: FSMContext):
    code = (message.text or "").strip()
    if not code:
        await message.answer("🎁 Promo-kodni yuboring yoki tugmani bosing.",
                             reply_markup=_promo_skip_kb())
        return
    promo = validate_promo(code)
    if not promo:
        await message.answer(
            "❌ Bu promo-kod yaroqsiz yoki muddati tugagan.\n"
            "Boshqa kod yuboring yoki tugmani bosing.",
            reply_markup=_promo_skip_kb()
        )
        return
    await state.update_data(promo_code=promo["code"], promo_percent=promo["percent"])
    await message.answer(f"✅ Promo-kod qabul qilindi: <b>−{promo['percent']}%</b> chegirma!",
                         parse_mode="HTML")
    await _after_promo(message, state)


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

    # Raqamni profilga ham yozamiz — keyin telefon orqali topish mumkin bo'ladi
    # (masalan, seller yordamchini raqami bilan qo'shganda)
    set_user_field(message.from_user.id, "phone", phone)

    data = await state.get_data()
    pid  = data["pid"]
    dlv  = data.get("delivery", "taxi")
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
    unit  = _unit_price(p, data)
    total = unit * qty
    fee   = delivery_fee_for(total)   # 300 000 dan yuqori xaridga — bepul
    commission = int(total * settings.COMMISSION_RATE)
    promo_code = data.get("promo_code")
    order_id = save_order({
        "buyer_id":     message.from_user.id,
        "buyer_name":   message.from_user.full_name,
        "buyer_username": message.from_user.username,
        "seller_id":    p["seller_id"],
        "product_id":   pid,
        "product_name": p["name"],
        "quantity":     qty,
        "unit_price":   unit,
        "total":        total,
        "prepay":       commission,       # 10% = platforma komissiyasi
        "commission":   commission,
        "delivery_fee": fee,              # 300 000 dan yuqori xaridga 0 (bepul)
        "fulfillment":  "delivery",
        "delivery":     dlv,
        "address":      data.get("address", "—"),
        "phone":        phone,
        "color":        data.get("selected_color", ""),
        "promo_code":   promo_code or "",
        "promo_percent": data.get("promo_percent", 0) or 0,
        "status":       "pending",
        "receipt":      None,
    })
    # Promo-kod ishlatildi deb belgilaymiz (limit hisobi uchun).
    if promo_code:
        try:
            use_promo(promo_code)
        except Exception:
            pass
    await state.update_data(order_id=order_id)
    await state.set_state(OrderState.receipt)

    platform_card = settings.PLATFORM_CARD or "⚠️ admin kartani sozlamagan"
    card_name_line = f"   → Karta egasi: <b>{settings.PLATFORM_CARD_NAME}</b>\n" if settings.PLATFORM_CARD_NAME else ""
    pct = int(settings.COMMISSION_RATE * 100)
    remain = max(total - commission, 0)

    # ── Xaridorga: oldi-to'lov PLATFORMA kartasiga ──
    fee_note = (
        f" + yetkazib berish <b>{money(fee)}</b>" if fee
        else " (yetkazib berish <b>BEPUL 🎉</b>)"
    )
    deliver_line = (
        f"🚚 Yetkazib berish: <b>{delivery_text(fee)}</b>\n"
        f"📍 Manzil: {data['address']}\n"
        f"📱 Tel: {phone}\n"
        f"<b>🟢 Yetkazib berish: SHU BUGUNOQ</b>\n\n"
        f"💵 Yetkazilganda <b>kurierga naqd</b> to'laysiz: qolgan mahsulot puli "
        f"<b>{money(remain)}</b>{fee_note}.\n"
        f"💳 Karta orqali to'lamoqchi bo'lsangiz — kurierdan so'raysiz.\n\n"
    )
    promo_summary = (
        f"🎁 Promo {promo_code}: −{data.get('promo_percent',0)}%\n" if promo_code else ""
    )
    await message.answer(
        f"✅ <b>Buyurtmangiz qabul qilindi!</b>  (#{order_id})\n"
        f"Boshlang'ich <b>{pct}%</b> to'lovni qiling.\n"
        f"{divider()}\n"
        f"📦 Mahsulot:  {p['name']}\n"
        f"🔢 Miqdor:  {qty} dona × {money(unit)}\n"
        f"{promo_summary}"
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
        f"🔢 Miqdor: {qty} dona × {unit:,} so'm\n"
        f"💰 Jami: {total:,} so'm\n"
        f"🚚 Yetkazib berish: {delivery_text(fee)}\n\n"
        f"🔒 <b>Xaridor ma'lumotlari kurierда.</b>\n"
        f"Mahsulotni kurier do'koningizdan olib, xaridorga yetkazadi.\n\n"
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
            f"🔢 {qty} dona × {unit:,} = <b>{total:,} so'm</b>\n"
            f"{promo_summary}"
            f"💵 Komissiya ({pct}%): {commission:,} so'm\n"
            f"👤 {message.from_user.full_name} (ID: {message.from_user.id})\n"
            f"📱 {phone}\n"
            f"📍 {data['address']}\n"
            f"🚚 Yetkazib berish: {delivery_text(fee)}\n"
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


# Foydalanuvchining oxirgi qidiruv so'zi — narx bo'yicha qayta saralash uchun
# (sort tugmasi bosilganda qidiruvni qaytadan ishlatamiz). Faqat xotirada.
_LAST_SEARCH: dict[int, str] = {}


def _sorted_search_kb(results: list, order: str) -> InlineKeyboardMarkup:
    """Natijalarni narx bo'yicha saralab, tugmalar ro'yxati + saralash tugmalari."""
    items = sorted(results, key=lambda p: p.get("price", 0), reverse=(order == "exp"))
    rows = []
    for p in items[:30]:
        price = p.get("price", 0)
        fin = "  ·  ❌" if p.get("is_finished") else ""
        rows.append([InlineKeyboardButton(
            text=f"{product_emoji(p)} {p['name']} — {price:,} so'm{fin}",
            callback_data=f"prod_{p['id']}"
        )])
    cheap_lbl = ("✅ " if order == "cheap" else "") + "💰 Arzondan"
    exp_lbl   = ("✅ " if order == "exp" else "") + "💸 Qimmatdan"
    rows.append([
        InlineKeyboardButton(text=cheap_lbl, callback_data="srtcheap"),
        InlineKeyboardButton(text=exp_lbl,   callback_data="srtexp"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.in_({"srtcheap", "srtexp"}))
async def search_sort(call: CallbackQuery):
    query = _LAST_SEARCH.get(call.from_user.id)
    if not query:
        await call.answer("Avval qaytadan qidiring.", show_alert=True); return
    results = search_products(query)
    if not results:
        await call.answer("Natija qolmadi."); return
    order = "cheap" if call.data == "srtcheap" else "exp"
    await call.answer("💰 Arzondan" if order == "cheap" else "💸 Qimmatdan")
    try:
        await call.message.edit_reply_markup(reply_markup=_sorted_search_kb(results, order))
    except Exception:
        pass


@router.message(SearchState.query)
async def do_search(message: Message, state: FSMContext):
    await state.clear()
    # Oldin ochilgan mahsulot albomini tozalaymiz (chatda rasmlar aralashmasligi uchun).
    await _clear_last_product(message.bot, message.chat.id)
    query = (message.text or "").strip()
    results = search_products(query)
    if not results:
        await message.answer("😔 Hech narsa topilmadi. Boshqa so'z bilan sinab ko'ring.", reply_markup=main_menu)
        return
    _LAST_SEARCH[message.from_user.id] = query

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

    # Narx bo'yicha saralab ko'rsatish — barcha natijalar bitta ro'yxatda
    # (saralash tugmalari bilan). Bittadan ortiq natija bo'lsa ma'noli.
    if len(results) > 1:
        await message.answer(
            "📋 <b>Barcha natijalar</b> — narx bo'yicha saralang:",
            parse_mode="HTML",
            reply_markup=_sorted_search_kb(results, "cheap")
        )


# ─── Baholash ────────────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("rev_"))
async def save_review(call: CallbackQuery):
    parts = call.data.split("_")
    seller_id = int(parts[1])
    order_id  = int(parts[2])
    stars     = int(parts[3])
    from app.storage import add_review, has_order_review
    # Bir buyurtma faqat bir marta baholanadi — takror bosishlar reytingni
    # buzmasligi uchun.
    if has_order_review(order_id):
        await call.answer("Bu buyurtmaga allaqachon baho bergansiz. Rahmat!",
                          show_alert=True)
        try:
            await call.message.edit_reply_markup(reply_markup=None)
        except Exception:
            pass
        return
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
