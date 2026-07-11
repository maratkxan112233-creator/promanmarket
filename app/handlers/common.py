import asyncio
import time

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    InputMediaPhoto,
)
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

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
    get_cart, add_to_cart, set_cart_item_qty, remove_cart_item, clear_cart,
    cart_count, get_orders_by_group,
)
from app.keyboards.seller import (
    main_menu, seller_main_menu, menu_for, phone_keyboard, cancel_keyboard,
    admin_contact_kb,
)
from app.states.seller_application import SearchState, OrderState, CartCheckoutState
from app.app.config.settings import settings
from app.ui import (
    money, divider, title, category_label, product_category,
    product_emoji, product_sort_key, product_group_label, normalize_uz_phone,
)

router = Router()

ORDER_STATUSES = {
    "pending":    "⏳ Kutilmoqda",
    "paid":       "✓ To'lov qabul qilindi",
    "processing": "📦 Tayyorlanmoqda",
    "shipped":    "🚚 Yo'lda",
    "delivered":  "✓ Yetkazib berildi",
    "cancelled":  "✕ Bekor qilindi",
}

DELIVERY_LABELS = {
    "pickup": "O'zi olib ketish",
    "taxi": "Taksi orqali — shu kunning o'zida",
    # eski buyurtmalar uchun (tarixiy) — yangi buyurtmalarda ishlatilmaydi
    "btc":  "BTC Pochta",
    "emu":  "EMU Express",
    "uzum": "Uzum Pochta",
}

# Yetkazib berish narxi — qat'iy belgilangan (har bir buyurtma uchun bir xil).
DELIVERY_FEE = 19_000
# Shu summadan yuqori (va teng) xaridlarga yetkazib berish bepul.
FREE_DELIVERY_THRESHOLD = 300_000


def delivery_fee_for(total: int) -> int:
    """Yetkazish narxi: xarid 300 000 so'mdan yuqori bo'lsa bepul (0)."""
    return 0 if total >= FREE_DELIVERY_THRESHOLD else DELIVERY_FEE


def delivery_text(fee: int) -> str:
    """Yetkazish narxini chiroyli matnga aylantiradi (bepul bo'lsa — bepul)."""
    return "<b>Bepul</b>" if fee == 0 else money(fee)


# Yetkazib berish haqida BITTA ixcham qator (har sahifani to'ldirib yubormaslik
# uchun — avval 3 qatorli "gazeta" banneri edi).
FREE_DELIVERY_BANNER = (
    f"Yetkazib berish — {money(DELIVERY_FEE)} · "
    f"{money(FREE_DELIVERY_THRESHOLD)} dan yuqori xaridga <b>bepul</b>"
)
# Sellerlarni jalb qilish (faqat /start salomida ko'rsatiladi, har market'da emas).
SELLER_INVITE_BANNER = (
    f"Do'kon ochmoqchimisiz? Murojaat: @{settings.ADMIN_USERNAME}"
)


def _extract_receipt(message: Message):
    """Chekni xabardan ajratadi → (file_id, 'photo'|'document') yoki (None, None).

    Rasm (screenshot) yoki PDF fayl qabul qilinadi."""
    if message.photo:
        return message.photo[-1].file_id, "photo"
    doc = message.document
    if doc and (doc.mime_type == "application/pdf"
                or (doc.file_name or "").lower().endswith(".pdf")):
        return doc.file_id, "document"
    return None, None


async def _send_receipt(chat_id, file_id, rtype, caption, reply_markup=None):
    """Chekni turiga qarab yuboradi: rasm bo'lsa send_photo, PDF bo'lsa send_document."""
    from app.bot.bot import bot
    if rtype == "document":
        await bot.send_document(chat_id, file_id, caption=caption,
                                parse_mode="HTML", reply_markup=reply_markup)
    else:
        await bot.send_photo(chat_id, file_id, caption=caption,
                             parse_mode="HTML", reply_markup=reply_markup)


async def _send_photo_or_text(chat_id: int, photo_id: str | None, caption: str):
    """Chatga rasm+matn (yoki rasm bo'lmasa — faqat matn) yuboradi.

    chat_id 0 bo'lsa yoki xato chiqsa — jim o'tkazib yuboriladi (asosiy buyurtma
    jarayoniga to'sqinlik qilmasin)."""
    if not chat_id:
        return
    try:
        from app.bot.bot import bot
        if photo_id:
            await bot.send_photo(chat_id, photo_id, caption=caption, parse_mode="HTML")
        else:
            await bot.send_message(chat_id, caption, parse_mode="HTML")
    except Exception:
        pass


async def _send_to_auction(photo_id: str | None, order_id, qty: int):
    """AUKSION guruhiga — barcha a'zolarga FAQAT rasm + buyurtma raqami + soni.

    Xaridor maxfiyligi uchun guruhda ism/telefon/narx/mahsulot nomi
    ko'rsatilmaydi."""
    await _send_photo_or_text(
        settings.AUCTION_GROUP_ID, photo_id,
        f"🆕 <b>Yangi buyurtma #{order_id}</b>\n🔢 Soni: <b>{qty} dona</b>"
    )


# ─── /id — joriy chatning ID sini ko'rsatadi (AUKSION guruhini sozlash uchun) ──
@router.message(F.text.regexp(r"^/id(@\w+)?\b"))
async def show_chat_id(message: Message):
    chat = message.chat
    await message.answer(
        f"🆔 <b>Chat ID:</b> <code>{chat.id}</code>\n"
        f"📛 Turi: {chat.type}\n\n"
        "Buyurtmalar shu guruhga tushishi uchun bu raqamni .env faylidagi "
        "<code>AUCTION_GROUP_ID</code> ga yozing.",
        parse_mode="HTML",
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
    await message.answer(
        "<b>Ma'lumot</b>\n"
        f"{divider()}\n"
        "Savol va takliflar:  @promanmarketbot\n"
        f"Admin:  @{settings.ADMIN_USERNAME}\n"
        "Ish vaqti:  09:00 – 18:00",
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
        products = get_seller_products(owner_id)
        rating_txt = f"★ {rating}  ({cnt} ta baho)" if cnt else "—"
        extra = (
            f"{divider()}\n"
            f"Do'kon:  {seller['shop_name']}\n"
            f"Mahsulotlar:  {len(products)} ta\n"
            f"Reyting:  {rating_txt}\n"
            f"{divider()}\n"
            "/seller — sotuvchi paneli"
        )
        role = "Sotuvchi" if is_seller(user.id) else "Sotuvchi (yordamchi)"
        profile_kb = admin_contact_kb()
    else:
        role  = "Xaridor"
        u = get_user(user.id)
        city = (u.get("city") if u else None) or "tanlanmagan"
        extra = (
            f"{divider()}\n"
            f"Shahar:  {city}\n"
            f"{divider()}\n"
            "Sotuvchi sifatida hamkorlik qilmoqchimisiz? Quyidagi tugmani bosing:"
        )
        # Xaridorga seller bo'lish taklifi — mavjud `become_seller` oqimini ochadi.
        profile_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Sotuvchi bo'lish", callback_data="become_seller")],
            [InlineKeyboardButton(text="Admin bilan bog'lanish",
                                  url=f"https://t.me/{settings.ADMIN_USERNAME}")],
        ])

    await message.answer(
        "<b>Profil</b>\n"
        f"{divider()}\n"
        f"Ism:  {user.full_name}\n"
        f"Username:  @{user.username or 'yoq'}\n"
        f"ID:  {user.id}\n"
        f"Rol:  {role}\n{extra}",
        parse_mode="HTML", reply_markup=profile_kb
    )


# ─── Market — do'konlar ro'yxati ─────────────────────────────────────────────
# Eski "🛍 Bozor" yozuvi ham qabul qilinadi (eski klaviaturasi ochiq foydalanuvchilar uchun).
@router.message(F.text.in_({"🛒 Market", "🛍 Bozor", "🛍 Katalog"}))
async def market_handler(message: Message):
    if is_shop_member(message.from_user.id):
        await message.answer(
            "Siz sotuvchisiz. Quyidagi menyudan foydalaning:",
            reply_markup=seller_main_menu
        )
        return
    u = get_user(message.from_user.id)
    city = u.get("city") if u else None
    if not city:
        await message.answer(
            "<b>Avval shahringizni tanlang</b>\n"
            "Sizga shu shahardagi do'konlar ko'rsatiladi:",
            parse_mode="HTML", reply_markup=_city_picker()
        )
        return
    await _show_market(message, city)


async def _show_market(message: Message, city: str):
    sellers = _city_sellers(city)
    if not sellers:
        await message.answer(
            f"<b>{city}</b> shahrida hozircha do'kon yo'q.\n"
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
        meta = f"★ {rating} · {len(prods)} ta mahsulot" if cnt else f"{len(prods)} ta mahsulot"
        lines.append(f"{i}. {s['shop_name']} — {meta}")
    await message.answer(
        f"<b>Do'konlar</b>   ·   📍 {city}\n"
        f"{FREE_DELIVERY_BANNER}\n\n"
        + "\n".join(lines) + "\n\n"
        "Kerakli do'konni tanlang.",
        parse_mode="HTML",
        reply_markup=_shops_keyboard(sellers)
    )


@router.callback_query(F.data == "changecity")
async def change_city(call: CallbackQuery):
    # Spinner darhol o'chsin — keyin javob yuboriladi.
    await call.answer()
    await call.message.answer("📍 Shaharingizni tanlang:", reply_markup=_city_picker())


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
    stars = f"   ·   ★ {rating} ({cnt})" if cnt else ""

    products = get_seller_products(seller_id)
    if not products:
        return (
            f"<b>{shop_name}</b>\n{divider()}\nHozircha mahsulot yo'q.",
            [InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← Orqaga", callback_data="back_shops")]
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
                text=f"— {product_emoji(p)} {product_group_label(p)} —",
                callback_data="noop"
            )])
        name = p.get("name", "—")
        if len(name) > 30:
            name = name[:30].rstrip() + "…"
        finished = "  ·  tugagan" if p.get("is_finished") else ""
        rows.append([InlineKeyboardButton(
            text=f"{name}  ·  {money(p.get('price', 0))}{finished}",
            callback_data=f"prod_{p['id']}"
        )])

    # Tugmalarni ≤_SHOP_PER_PAGE talik bo'laklarga ajratamiz.
    chunks = [rows[i:i + _SHOP_PER_PAGE] for i in range(0, len(rows), _SHOP_PER_PAGE)]
    # "← Orqaga" tugmasi faqat oxirgi bo'lakda.
    chunks[-1].append([InlineKeyboardButton(text="← Orqaga", callback_data="back_shops")])
    keyboards = [InlineKeyboardMarkup(inline_keyboard=c) for c in chunks]

    text = (f"<b>{shop_name}</b>{stars}\n{divider()}\n"
            f"Mahsulotlar: {total} ta. Kerakli mahsulotni tanlang.")
    return text, keyboards


# chat_id -> (seller_id, [ro'yxat bo'laklari xabar id'lari]). Xotirada saqlanadi:
# mahsulot ochilganda ro'yxat chatda QOLADI, "orqaga" bosilganda esa qayta
# yuborilmaydi (tekin qaytish). Restart bo'lsa oddiy qayta-yuborish yo'liga qaytadi.
_SHOP_LIST_MSGS: dict[int, tuple[int, list[int]]] = {}


async def _send_shop_menu(call: CallbackQuery, seller_id: int):
    """Do'konga kirilganda BARCHA mahsulotlarni uzluksiz (sahifa tugmasisiz)
    ketma-ket xabarlar bilan yuboradi."""
    chat_id = call.message.chat.id
    # Eski ro'yxat bo'laklari (bo'lsa) ham o'chirish partiyasiga qo'shiladi.
    _, old_list_ids = _SHOP_LIST_MSGS.pop(chat_id, (0, []))
    await _clear_last_product(call.message.bot, chat_id,
                              [call.message.message_id] + old_list_ids)
    text, keyboards = _shop_menu_chunks(seller_id)
    # Birinchi bo'lak — sarlavha bilan; qolganlari "davomi" bilan.
    first = await call.message.answer(text, parse_mode="HTML", reply_markup=keyboards[0])
    ids = [first.message_id]
    for kb in keyboards[1:]:
        m = await call.message.answer("…davomi", reply_markup=kb)
        ids.append(m.message_id)
    _SHOP_LIST_MSGS[chat_id] = (seller_id, ids)


async def _send_category_products(message: Message, seller_id: int, code: str):
    """Bo'lim mahsulotlarini AVVALGIDEK oddiy ro'yxat qilib yuboradi:
    har bir mahsulot nomi + narxi alohida tugma (prod_<id>)."""
    products  = [p for p in get_seller_products(seller_id) if product_category(p) == code]
    seller    = get_seller(seller_id)
    shop_name = seller["shop_name"] if seller else "Do'kon"
    label     = category_label(code)

    if not products:
        await message.answer(
            f"<b>{shop_name}</b>\n{divider()}\n{label}: mahsulot qolmadi.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="← Orqaga", callback_data=f"shop_{seller_id}")]
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
        finished = "  ·  tugagan" if p.get("is_finished") else ""
        rows.append([InlineKeyboardButton(
            text=f"{name}  ·  {money(p.get('price', 0))}{finished}",
            callback_data=f"prod_{p['id']}"
        )])
    rows.append([InlineKeyboardButton(text="← Orqaga", callback_data=f"shop_{seller_id}")])

    await message.answer(
        f"<b>{shop_name}</b>   ·   {label}\n{divider()}\n"
        f"Mahsulotlar: {len(products)} ta. Kerakli mahsulotni tanlang.",
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
    chat_id = call.message.chat.id
    _, list_ids = _SHOP_LIST_MSGS.pop(chat_id, (0, []))
    await _clear_last_product(call.message.bot, chat_id,
                              [call.message.message_id] + list_ids)
    await _send_category_products(call.message, seller_id, code)


@router.callback_query(F.data.startswith("shop_"))
async def show_shop(call: CallbackQuery):
    uid = int(call.data.split("_")[1])
    if not get_seller(uid):
        await call.answer("Do'kon topilmadi."); return
    await call.answer()
    chat_id = call.message.chat.id
    listed = _SHOP_LIST_MSGS.get(chat_id)
    # Mahsulot kartochkasidan "Orqaga": shu do'kon ro'yxati hali chatda turgan
    # bo'lsa — faqat kartochka (+ albom/video) o'chiriladi, ro'yxat qayta
    # yuborilmaydi. Bu qaytishni bir zumlik qiladi.
    if listed and listed[0] == uid and chat_id in _PRODUCT_CARD:
        await _clear_last_product(call.message.bot, chat_id)
        return
    await _send_shop_menu(call, uid)


@router.callback_query(F.data == "back_shops")
async def back_to_shops(call: CallbackQuery):
    # Lentadagi barcha mahsulot xabarlarini VA do'kon ro'yxati bo'laklarini
    # tozalab, do'konlar ro'yxatini qaytaramiz.
    await call.answer()
    chat_id = call.message.chat.id
    _, list_ids = _SHOP_LIST_MSGS.pop(chat_id, (0, []))
    await _clear_last_product(call.message.bot, chat_id,
                              [call.message.message_id] + list_ids)
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

    # ── Sarlavha + narx (eng muhimi yuqorida, bitta nigohda ko'rinadi) ──
    lines = [f"<b>{name}</b>", divider()]

    price_line = f"Narx: <b>{money(price)}</b>"
    if disc_pct:
        price_line += f"   −{disc_pct}%"
        if old_price:
            price_line += f"  <s>{money(old_price)}</s>"
    lines.append(price_line)

    # Do'kon · shahar · reyting — bitta ixcham qatorda
    meta = f"{shop}"
    if city:
        meta += f"  ·  📍 {city}"
    if rev_cnt:
        meta += f"  ·  ★ {rating} ({rev_cnt})"
    lines.append(meta)

    # ── Holat (faqat kerak bo'lganda) ──
    if p.get("is_finished"):
        lines.append("\n✕ <b>Mahsulot tugagan</b>")
    else:
        stock = product_stock(p)
        if stock is not None and stock <= 5:
            lines.append(f"\nOmborda: {stock} dona qoldi")

    # ── Tavsif (rasm caption limiti 1024 belgi — uzun tavsifni qisqartiramiz) ──
    if desc:
        if len(desc) > 500:
            desc = desc[:500].rstrip() + "…"
        lines.append(f"\n{desc}")

    # ── Yetkazib berish (bitta ixcham qator) ──
    fee = delivery_fee_for(price)
    if fee:
        lines.append(
            f"\nYetkazib berish: <b>{money(fee)}</b> · "
            f"{money(FREE_DELIVERY_THRESHOLD)}+ xaridga bepul · bugun"
        )
    else:
        lines.append("\nYetkazib berish: <b>bepul</b> · bugun")

    # Qisqa eslatma (bitta qator).
    lines.append("<i>Rasm namunaviy bo'lishi mumkin.</i>")
    return "\n".join(lines)


def _product_kb(p: dict, user_id: int, with_album: bool = True) -> InlineKeyboardMarkup:
    """Mahsulot xabari uchun tugmalar: buyurtma, sevimlilar, albom va orqaga."""
    if is_favorite(user_id, p["id"]):
        fav_text = "Sevimlilardan olib tashlash"
    else:
        fav_text = "Sevimlilarga qo'shish"
    rows = []
    if not p.get("is_finished"):
        rows.append([InlineKeyboardButton(text="Buyurtma berish", callback_data=f"order_{p['id']}")])
        rows.append([InlineKeyboardButton(text="Savatga qo'shish", callback_data=f"addcart_{p['id']}")])
    rows.append([InlineKeyboardButton(text=fav_text, callback_data=f"fav_{p['id']}")])
    # Qo'shimcha rasm/video bo'lsa — alohida tugma bilan so'ralganda yuboriladi
    # (kartochka bitta xabar bo'lib qoladi — tez ochiladi va tez almashadi).
    if with_album:
        n_photos = len(product_photos(p))
        has_video = bool(product_video(p))
        if n_photos > 1 and has_video:
            album_text = f"Rasmlar ({n_photos}) va video"
        elif n_photos > 1:
            album_text = f"Rasmlar ({n_photos})"
        elif has_video:
            album_text = "Videoni ko'rish"
        else:
            album_text = None
        if album_text:
            rows.append([InlineKeyboardButton(text=album_text, callback_data=f"album_{p['id']}")])
    rows.append([InlineKeyboardButton(
        text="← Orqaga",
        callback_data=f"shop_{p['seller_id']}",
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# chat_id -> hozir ko'rsatilgan mahsulotning barcha xabar id'lari (kartochka +
# albom + video). Yangi mahsulot ochilganda ortiqchalari o'chiriladi — chatda
# bir vaqtda faqat bitta mahsulot turadi. Bu ma'lumot diskda (storage)
# saqlanadi — bot qayta ishga tushganda ham eski xabarlarni o'chira olishi
# uchun (set_view_msgs / pop_view_msgs).

# chat_id -> (kartochka xabar id'si, "photo" | "text"). Xotirada saqlanadi:
# yangi mahsulot ochilganda kartochka O'CHIRILMAY, joyida TAHRIRLANADI
# (edit_message_media) — tez va "lip-lip"siz. Restart bo'lsa bo'sh qoladi va
# oddiy o'chir-yubor yo'liga qaytadi.
_PRODUCT_CARD: dict[int, tuple[int, str]] = {}


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
    _PRODUCT_CARD.pop(chat_id, None)
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
    bot     = call.message.bot

    card = _PRODUCT_CARD.get(chat_id)
    card_id = card[0] if card else None

    # Oldingi mahsulotning QO'SHIMCHA xabarlari (albom/video) o'chiriladi.
    # Kartochkaning o'zi tahrirlanadi, bosilgan ro'yxat xabari esa CHATDA
    # QOLADI — "orqaga" bosilganda ro'yxat qayta yuborilmaydi.
    extra = [mid for mid in get_view_msgs(chat_id) if mid != card_id]
    await _delete_msgs(bot, chat_id, extra)

    # ── Tahrirlash yo'li: eski kartochka joyida yangi mahsulotga almashadi ──
    edited = False
    if card_id:
        try:
            if card[1] == "photo" and photos:
                await bot.edit_message_media(
                    chat_id=chat_id, message_id=card_id,
                    media=InputMediaPhoto(media=photos[0], caption=text, parse_mode="HTML"),
                    reply_markup=kb,
                )
                edited = True
            elif card[1] == "text" and not photos:
                await bot.edit_message_text(
                    text, chat_id=chat_id, message_id=card_id,
                    parse_mode="HTML", reply_markup=kb,
                )
                edited = True
        except TelegramBadRequest as e:
            # O'sha mahsulot qayta bosilgan bo'lsa — xabar o'zgarmagan, bu xato emas.
            if "message is not modified" in str(e):
                edited = True
        except Exception:
            pass

    # ── Zaxira yo'li: tahrirlab bo'lmasa (tur almashdi / kartochka yo'q /
    # foydalanuvchi o'chirib yuborgan) — eskisini o'chirib, yangisini yuboramiz.
    kind = "photo" if photos else "text"
    if not edited:
        if card_id:
            await _delete_msgs(bot, chat_id, [card_id])
        if photos:
            try:
                sent = await call.message.answer_photo(
                    photos[0], caption=text, parse_mode="HTML", reply_markup=kb)
            except Exception:
                sent = await call.message.answer(
                    text + "\n\n<i>(rasm yuklanmadi)</i>", parse_mode="HTML", reply_markup=kb)
                kind = "text"
        else:
            sent = await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
        card_id = sent.message_id

    set_view_msgs(chat_id, [card_id])
    _PRODUCT_CARD[chat_id] = (card_id, kind)


@router.callback_query(F.data.startswith("album_"))
async def show_album(call: CallbackQuery):
    """Kartochkadagi «📸 Barcha rasmlar» tugmasi: albom + video so'ralganda
    yuboriladi (kartochka o'zi bitta xabar bo'lib tez ochilishi uchun)."""
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Topilmadi."); return
    await call.answer()

    chat_id = call.message.chat.id
    ids = []
    photos = product_photos(p)
    if len(photos) > 1:
        media = [InputMediaPhoto(media=ph) for ph in photos[:10]]
        try:
            sent = await call.message.answer_media_group(media)
            ids.extend(m.message_id for m in sent)
        except Exception:
            pass
    video = product_video(p)
    if video:
        try:
            vmsg = await call.message.answer_video(video, caption=f"🎬 {p.get('name','')}")
            ids.append(vmsg.message_id)
        except Exception:
            pass

    if ids:
        # Albom/video ham shu mahsulot xabarlariga qo'shiladi — keyingi
        # mahsulot ochilganda birga o'chiriladi.
        set_view_msgs(chat_id, get_view_msgs(chat_id) + ids)
        # Tugmani olib tashlaymiz — albom qayta-qayta yuborilmasin.
        try:
            await call.message.edit_reply_markup(
                reply_markup=_product_kb(p, call.from_user.id, with_album=False))
        except Exception:
            pass


# ─── ❤️ Istaklar (sevimli mahsulotlar) ───────────────────────────────────────
@router.callback_query(F.data.startswith("fav_"))
async def toggle_fav(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    added = toggle_favorite(call.from_user.id, pid)
    await call.answer(
        "Sevimlilarga qo'shildi." if added else "Sevimlilardan olib tashlandi."
    )
    # Tugma yozuvini yangi holatga moslab yangilaymiz. Albom allaqachon
    # yuborilgan bo'lsa (view msgs'da kartochkadan tashqari xabarlar bor),
    # albom tugmasi qayta chiqarilmaydi.
    album_pending = len(get_view_msgs(call.message.chat.id)) <= 1
    try:
        await call.message.edit_reply_markup(
            reply_markup=_product_kb(p, call.from_user.id, with_album=album_pending)
        )
    except Exception:
        pass


@router.message(F.text.in_({"❤️ Istaklarim", "❤️ Sevimlilar"}))
async def favorites_handler(message: Message):
    favs = get_favorites(message.from_user.id)
    products = [p for p in (get_product_by_id(pid) for pid in favs) if p]
    if not products:
        await message.answer(
            "<b>Sevimlilar</b>\n"
            f"{divider()}\n"
            "Hozircha bo'sh.\n"
            "Mahsulot sahifasidagi «Sevimlilarga qo'shish» tugmasi bilan "
            "yoqqan mahsulotlarni saqlab qo'yishingiz mumkin.",
            parse_mode="HTML",
            reply_markup=menu_for(message.from_user.id)
        )
        return
    rows = [
        [InlineKeyboardButton(
            text=f"{p['name']}  ·  {money(p['price'])}"
                 f"{'  ·  tugagan' if p.get('is_finished') else ''}",
            callback_data=f"prod_{p['id']}"
        )]
        for p in products
    ]
    await message.answer(
        "<b>Sevimlilar</b>\n"
        f"{divider()}\n"
        f"Saqlangan mahsulotlar:  {len(products)} ta\n"
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
        f"<b>{p['name']}</b> uchun rang tanlang:",
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
    color_line = f"Rang: <b>{data['selected_color']}</b>\n" if data.get("selected_color") else ""
    promo_line = ""
    if data.get("promo_percent"):
        full = p.get("price", 0) * qty
        promo_line = (
            f"Promo <b>{data['promo_code']}</b>: −{data['promo_percent']}%  "
            f"(<s>{full:,}</s> → <b>{total:,}</b>)\n"
        )
    await message.answer(
        f"<b>{p['name']}</b>\n"
        f"{divider()}\n"
        f"Miqdor: {qty} dona\n"
        f"{promo_line}"
        f"Jami: <b>{total:,} so'm</b>\n"
        f"{color_line}"
        f"Yetkazib berish: {delivery_text(fee)}\n\n"
        f"<b>Yetkazib berish manzilingizni kiriting</b>\n"
        f"(shahar, ko'cha, uy — to'liq yozing):",
        parse_mode="HTML", reply_markup=cancel_keyboard
    )


# ─── Buyurtma qilish: miqdor (nechta dona) ───────────────────────────────────
def _qty_text(p: dict, qty: int) -> str:
    total = p["price"] * qty
    return (
        f"<b>{p['name']}</b>\n"
        f"Nechta dona olmoqchisiz?\n\n"
        f"Miqdor: <b>{qty} dona</b>\n"
        f"Jami: <b>{total:,} so'm</b>"
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
        [InlineKeyboardButton(text="Davom etish", callback_data=f"qok_{qty}")],
    ])


@router.callback_query(F.data.startswith("order_"))
async def start_order(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    if p.get("is_finished"):
        await call.answer("Mahsulot tugagan. Hozircha buyurtma qilib bo'lmaydi.", show_alert=True)
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
        [InlineKeyboardButton(text="Promo-kodim yo'q", callback_data="promoskip")],
    ])


async def _ask_promo(message: Message, state: FSMContext, p: dict):
    await state.set_state(OrderState.promo)
    await state.update_data(pid=p["id"])
    await message.answer(
        "<b>Promo-kodingiz bo'lsa yuboring</b> — chegirma qo'llanadi.\n"
        "Bo'lmasa quyidagi tugmani bosing.",
        parse_mode="HTML", reply_markup=_promo_skip_kb()
    )


async def _after_promo(message: Message, state: FSMContext):
    data = await state.get_data()
    p = get_product_by_id(data.get("pid"))
    if not p:
        await state.clear()
        await message.answer("Mahsulot topilmadi.", reply_markup=main_menu)
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
    await message.answer("Buyurtma bekor qilindi.", reply_markup=main_menu)


@router.message(OrderState.promo)
async def order_promo_enter(message: Message, state: FSMContext):
    code = (message.text or "").strip()
    if not code:
        await message.answer("Promo-kodni yuboring yoki tugmani bosing.",
                             reply_markup=_promo_skip_kb())
        return
    promo = validate_promo(code)
    if not promo:
        await message.answer(
            "Bu promo-kod yaroqsiz yoki muddati tugagan.\n"
            "Boshqa kod yuboring yoki tugmani bosing.",
            reply_markup=_promo_skip_kb()
        )
        return
    await state.update_data(promo_code=promo["code"], promo_percent=promo["percent"])
    await message.answer(f"Promo-kod qabul qilindi: <b>−{promo['percent']}%</b> chegirma.",
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
    await message.answer("Buyurtma bekor qilindi.", reply_markup=main_menu)


# ─── 3) manzil qabul qilindi → telefon so'raymiz ────────────────────────────
@router.message(OrderState.address)
async def order_address(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Manzilni matn ko'rinishida kiriting:")
        return
    await state.update_data(address=message.text.strip())
    await state.set_state(OrderState.phone)
    await message.answer(
        "<b>Telefon raqamingizni yuboring</b>\n"
        "(pastdagi tugma orqali yoki qo'lda yozing):",
        parse_mode="HTML", reply_markup=phone_keyboard
    )


# ─── 4) telefon qabul → buyurtma saqlanadi, oldi-to'lov ko'rsatiladi ────────
@router.message(OrderState.phone)
async def order_phone(message: Message, state: FSMContext):
    if message.contact:
        # Kontakt ulashilsa — ishonchli manba: chet el raqami ham qabul qilinadi.
        raw = message.contact.phone_number
        phone = normalize_uz_phone(raw) or ("+" + str(raw).lstrip("+"))
    else:
        phone = normalize_uz_phone(message.text)
        if not phone:
            await message.answer(
                "Raqam noto'g'ri kiritildi. Namuna: <b>+998 90 123 45 67</b>\n"
                "Pastdagi tugma orqali yuborsangiz ham bo'ladi:",
                parse_mode="HTML", reply_markup=phone_keyboard,
            )
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
        await message.answer("Mahsulot topilmadi.", reply_markup=main_menu)
        return
    if p.get("is_finished"):
        await state.clear()
        await message.answer(
            "Afsuski, bu mahsulot hozirgina tugadi. Buyurtma qabul qilinmadi.",
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
    card_name = f" ({settings.PLATFORM_CARD_NAME})" if settings.PLATFORM_CARD_NAME else ""
    pct = int(settings.COMMISSION_RATE * 100)
    remain = max(total - commission, 0)

    # ── Xaridorga: oldi-to'lov PLATFORMA kartasiga (qisqa, bir ekranlik xabar) ──
    fee_note = f" + yetkazib berish {money(fee)}" if fee else ""
    promo_summary = (
        f"Promo {promo_code}: −{data.get('promo_percent',0)}%\n" if promo_code else ""
    )
    await message.answer(
        f"<b>Buyurtma #{order_id} qabul qilindi</b>\n"
        f"{divider()}\n"
        f"{p['name']} — {qty} × {money(unit)} = <b>{money(total)}</b>\n"
        f"{promo_summary}"
        f"Yetkazib berish: {delivery_text(fee)}\n"
        f"Manzil: {data['address']}\n"
        f"Telefon: {phone}\n\n"
        f"Oldindan to'lov ({pct}%): <b>{money(commission)}</b>\n"
        f"Karta: <code>{platform_card}</code>{card_name}\n"
        f"Qolgan {money(remain)}{fee_note} kurierga naqd yoki karta orqali to'lanadi.\n\n"
        f"<b>To'lov chekini (rasm yoki PDF) shu yerga yuboring</b> — "
        f"chek tasdiqlangach buyurtma tayyorlanadi.\n"
        f"Savollar uchun: @{settings.ADMIN_USERNAME}",
        parse_mode="HTML", reply_markup=cancel_keyboard
    )

    # ── Sellerga xabar HOZIR YUBORILMAYDI ──
    # Xaridor boshlang'ich (10%) to'lovni qilib, admin uni tasdiqlamaguncha
    # sellerga hech qanday xabar bormaydi. Aks holda xaridor oxirgi bosqichda
    # buyurtmani bekor qilsa ham sellerga "yangi zakaz" kelib, chalg'itadi.
    # Seller xabari admin to'lovni tasdiqlaganda yuboriladi
    # (app/handlers/admin.py → _confirm_single_order).

    # ── AUKSION guruhiga buyurtma SHU YERDA YUBORILMAYDI ──
    # Faqat admin to'lov chekini ko'rib tasdiqlaganda yuboriladi
    # (app/handlers/admin.py → _confirm_single_order). Aks holda tasdiqlanmagan
    # (chek yuborilmagan / bekor qilingan) buyurtmalar ham guruhga tushardi.


# ─── 5) chek rasmi qabul qilinadi → admin tasdig'iga yuboriladi ─────────────
@router.message(OrderState.receipt, F.photo | F.document)
async def order_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    order_id = data.get("order_id")
    o = get_order_by_id(order_id) if order_id else None
    if not o:
        await state.clear()
        await message.answer("❌ Buyurtma topilmadi.", reply_markup=main_menu)
        return

    receipt_id, rtype = _extract_receipt(message)
    if receipt_id is None:
        await message.answer(
            "Iltimos, to'lov chekining <b>rasmini yoki PDF faylini</b> yuboring "
            "(yoki ❌ Bekor qilish).",
            parse_mode="HTML"
        )
        return
    update_order_fields(order_id, {"receipt": receipt_id, "receipt_type": rtype})
    await state.clear()

    # Chek rasmini xaridor chatidan o'chiramiz — aks holda Telegram rasm
    # ko'ruvchisida (surganda) mahsulot rasmlariga aralashib ko'rinadi. Rasm
    # admin tomonida saqlanib qoladi (file_id allaqachon olingan).
    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(
        f"Chek qabul qilindi. Buyurtma #{order_id} to'lovi tekshirilmoqda — "
        f"tasdiqlangach xabar beramiz.",
        reply_markup=main_menu
    )

    # Adminga chek + tasdiqlash tugmalari
    pct = int(settings.COMMISSION_RATE * 100)
    # To'lovni tasdiqlash + yetkazib berish vaqtini tanlash (mahsulot turiga qarab):
    #   🟢 Bugun  —  juda tez (kichik/yengil mahsulotlar)
    #   🟡 24 soat — ertaga (katta/og'ir maishiy texnika)
    # Tanlangan vaqt xaridorga yuboriladigan xabarда ko'rsatiladi.
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiq + 🟢 Bugun",   callback_data=f"paycfm_{order_id}_today"),
            InlineKeyboardButton(text="✅ Tasdiq + 🟡 24 soat", callback_data=f"paycfm_{order_id}_24h"),
        ],
        [
            InlineKeyboardButton(text="❌ Rad etish",            callback_data=f"payrej_{order_id}"),
        ],
    ])
    caption = (
        f"<b>Buyurtma #{order_id} — to'lov cheki</b>\n\n"
        f"Mahsulot: {o.get('product_name','—')}\n"
        f"Oldindan to'lov ({pct}%): {o.get('prepay',0):,} so'm\n"
        f"Xaridor: {o.get('buyer_name','—')}\n"
        f"Telefon: {o.get('phone','—')}\n"
        f"Manzil: {o.get('address','—')}"
    )
    try:
        await _send_receipt(settings.OWNER_ID, receipt_id, rtype, caption, kb)
    except Exception:
        pass


@router.message(OrderState.receipt)
async def order_receipt_invalid(message: Message):
    await message.answer(
        "Iltimos, to'lov chekining <b>rasmini yoki PDF faylini</b> yuboring "
        "(yoki ❌ Bekor qilish).",
        parse_mode="HTML"
    )


# ═══════════════════════════════════════════════════════════════════════════
#  🛍 SAVAT (korzina) — bir nechta mahsulotni bitta zakazda
# ═══════════════════════════════════════════════════════════════════════════

# ─── Savatga qo'shish ────────────────────────────────────────────────────────
@router.callback_query(F.data.startswith("addcart_"))
async def add_to_cart_cb(call: CallbackQuery):
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    if p.get("is_finished"):
        await call.answer("Mahsulot tugagan.", show_alert=True); return
    colors = p.get("colors") or []
    if colors:
        # Rang bor — avval rang tanlaymiz (savatga rang bilan qo'shiladi).
        rows = [[InlineKeyboardButton(text=c, callback_data=f"cartcolor_{pid}_{i}")]
                for i, c in enumerate(colors)]
        await call.message.answer(
            f"<b>{p['name']}</b> — savatga qaysi rangda qo'shamiz?",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
        )
        await call.answer()
        return
    add_to_cart(call.from_user.id, pid)
    await call.answer(f"Savatga qo'shildi (jami {cart_count(call.from_user.id)} ta).",
                      show_alert=False)


@router.callback_query(F.data.startswith("cartcolor_"))
async def add_to_cart_color_cb(call: CallbackQuery):
    parts = call.data.split("_")
    pid = int(parts[1])
    idx = int(parts[2])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Mahsulot topilmadi."); return
    colors = p.get("colors") or []
    color = colors[idx] if 0 <= idx < len(colors) else ""
    add_to_cart(call.from_user.id, pid, color=color)
    try:
        await call.message.edit_text(
            f"Savatga qo'shildi: <b>{p['name']}</b>"
            + (f" · {color}" if color else ""),
            parse_mode="HTML",
        )
    except Exception:
        pass
    await call.answer(f"Savatga qo'shildi (jami {cart_count(call.from_user.id)} ta).")


# ─── Savatni ko'rsatish ──────────────────────────────────────────────────────
def _cart_lines(user_id: int):
    """Savat qatorlarini (idx, item, product) ro'yxati va umumiy summани qaytaradi.
    Mahsulot o'chirilgan/tugagan bo'lsa product=None bo'ladi."""
    rows = []
    combined = 0
    for idx, it in enumerate(get_cart(user_id)):
        p = get_product_by_id(it.get("product_id"))
        qty = max(1, int(it.get("quantity", 1)))
        if p and not p.get("is_finished"):
            combined += p.get("price", 0) * qty
        rows.append((idx, it, p))
    return rows, combined


def _cart_view(user_id: int):
    """Savat matni va inline tugmalarini qaytaradi."""
    rows, combined = _cart_lines(user_id)
    if not rows:
        return None, None

    lines = ["<b>Savat</b>", divider()]
    has_orderable = False
    for n, (idx, it, p) in enumerate(rows, start=1):
        qty = max(1, int(it.get("quantity", 1)))
        color = it.get("color") or ""
        if not p:
            lines.append(f"{n}. <i>Mahsulot o'chirilgan</i>")
            continue
        if p.get("is_finished"):
            lines.append(f"{n}. {p['name']} — <b>tugagan</b>")
            continue
        has_orderable = True
        line_total = p.get("price", 0) * qty
        color_txt = f"  ·  {color}" if color else ""
        lines.append(
            f"{n}. <b>{p['name']}</b>{color_txt}\n"
            f"   {qty} dona × {money(p.get('price', 0))} = <b>{money(line_total)}</b>"
        )

    fee = delivery_fee_for(combined)
    lines.append(divider())
    lines.append(f"Jami: <b>{money(combined)}</b>")
    lines.append(f"Yetkazib berish: {delivery_text(fee)}")
    if has_orderable:
        pct = int(settings.COMMISSION_RATE * 100)
        prepay = int(combined * settings.COMMISSION_RATE)
        lines.append(f"Oldindan to'lov ({pct}%): <b>{money(prepay)}</b>")

    kb_rows = []
    for idx, it, p in rows:
        qty = max(1, int(it.get("quantity", 1)))
        if p and not p.get("is_finished"):
            name_short = (p['name'][:18] + "…") if len(p['name']) > 19 else p['name']
            kb_rows.append([
                InlineKeyboardButton(text="➖", callback_data=f"cqset_{idx}_{qty-1}"),
                InlineKeyboardButton(text=f"{name_short}: {qty}", callback_data="noop"),
                InlineKeyboardButton(text="➕", callback_data=f"cqset_{idx}_{qty+1}"),
                InlineKeyboardButton(text="❌", callback_data=f"cdel_{idx}"),
            ])
        else:
            kb_rows.append([
                InlineKeyboardButton(text="Olib tashlash", callback_data=f"cdel_{idx}"),
            ])
    if has_orderable:
        kb_rows.append([InlineKeyboardButton(text="Buyurtma berish", callback_data="cocheckout")])
    kb_rows.append([InlineKeyboardButton(text="Savatni tozalash", callback_data="cclear")])

    return "\n".join(lines), InlineKeyboardMarkup(inline_keyboard=kb_rows)


@router.message(F.text.in_({"🛍 Savatim", "🧺 Savat"}))
async def cart_handler(message: Message):
    if is_shop_member(message.from_user.id):
        await message.answer(
            "Siz sotuvchisiz. Savat faqat xaridorlar uchun.",
            reply_markup=seller_main_menu,
        )
        return
    text, kb = _cart_view(message.from_user.id)
    if not text:
        await message.answer(
            f"<b>Savat</b>\n{divider()}\n"
            "Hozircha bo'sh.\n"
            "Mahsulot sahifasidagi «Savatga qo'shish» tugmasi bilan mahsulot qo'shing.",
            parse_mode="HTML", reply_markup=menu_for(message.from_user.id),
        )
        return
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


async def _refresh_cart(call: CallbackQuery):
    text, kb = _cart_view(call.from_user.id)
    if not text:
        try:
            await call.message.edit_text("Savat bo'sh.")
        except Exception:
            pass
        return
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        pass


@router.callback_query(F.data.startswith("cqset_"))
async def cart_qty_set(call: CallbackQuery):
    parts = call.data.split("_")
    idx = int(parts[1]); newq = int(parts[2])
    items = get_cart(call.from_user.id)
    if 0 <= idx < len(items):
        p = get_product_by_id(items[idx].get("product_id"))
        mx = _max_qty(p) if p else 99
        set_cart_item_qty(call.from_user.id, idx, max(1, min(mx, newq)))
    await call.answer()
    await _refresh_cart(call)


@router.callback_query(F.data.startswith("cdel_"))
async def cart_del(call: CallbackQuery):
    idx = int(call.data.split("_")[1])
    remove_cart_item(call.from_user.id, idx)
    await call.answer("Olib tashlandi.")
    await _refresh_cart(call)


@router.callback_query(F.data == "cclear")
async def cart_clear(call: CallbackQuery):
    clear_cart(call.from_user.id)
    await call.answer("Savat tozalandi.")
    try:
        await call.message.edit_text("Savat bo'sh.")
    except Exception:
        pass


# ─── Savatdan buyurtma: promo → manzil → telefon ─────────────────────────────
@router.callback_query(F.data == "cocheckout")
async def cart_checkout(call: CallbackQuery, state: FSMContext):
    rows, combined = _cart_lines(call.from_user.id)
    orderable = [(it, p) for _, it, p in rows if p and not p.get("is_finished")]
    if not orderable:
        await call.answer("Savatda buyurtma qilish mumkin mahsulot yo'q.", show_alert=True)
        return
    await call.answer()
    await state.clear()
    await state.set_state(CartCheckoutState.promo)
    await call.message.answer(
        "<b>Promo-kodingiz bo'lsa yuboring</b> — chegirma savatdagi barcha "
        "mahsulotlarga qo'llanadi.\nBo'lmasa quyidagi tugmani bosing.",
        parse_mode="HTML", reply_markup=_promo_skip_kb(),
    )


@router.callback_query(CartCheckoutState.promo, F.data == "promoskip")
async def cart_promo_skip(call: CallbackQuery, state: FSMContext):
    await call.answer()
    try:
        await call.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await _cart_ask_address(call.message, state)


@router.message(CartCheckoutState.promo, F.text == "❌ Bekor qilish")
async def cart_promo_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Buyurtma bekor qilindi.", reply_markup=menu_for(message.from_user.id))


@router.message(CartCheckoutState.promo)
async def cart_promo_enter(message: Message, state: FSMContext):
    code = (message.text or "").strip()
    if not code:
        await message.answer("Promo-kodni yuboring yoki tugmani bosing.",
                             reply_markup=_promo_skip_kb())
        return
    promo = validate_promo(code)
    if not promo:
        await message.answer(
            "Bu promo-kod yaroqsiz yoki muddati tugagan.\n"
            "Boshqa kod yuboring yoki tugmani bosing.",
            reply_markup=_promo_skip_kb(),
        )
        return
    await state.update_data(promo_code=promo["code"], promo_percent=promo["percent"])
    await message.answer(f"Promo-kod qabul qilindi: <b>−{promo['percent']}%</b> chegirma.",
                         parse_mode="HTML")
    await _cart_ask_address(message, state)


async def _cart_ask_address(message: Message, state: FSMContext):
    await state.set_state(CartCheckoutState.address)
    await message.answer(
        "<b>Yetkazib berish manzilingizni kiriting</b>\n"
        "(shahar, ko'cha, uy — to'liq yozing):",
        parse_mode="HTML", reply_markup=cancel_keyboard,
    )


@router.message(CartCheckoutState.address, F.text == "❌ Bekor qilish")
async def cart_address_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Buyurtma bekor qilindi.", reply_markup=menu_for(message.from_user.id))


@router.message(CartCheckoutState.address)
async def cart_address(message: Message, state: FSMContext):
    if not message.text or not message.text.strip():
        await message.answer("Manzilni matn ko'rinishida kiriting:")
        return
    await state.update_data(address=message.text.strip())
    await state.set_state(CartCheckoutState.phone)
    await message.answer(
        "<b>Telefon raqamingizni yuboring</b>\n"
        "(pastdagi tugma orqali yoki qo'lda yozing):",
        parse_mode="HTML", reply_markup=phone_keyboard,
    )


@router.message(CartCheckoutState.phone, F.text == "❌ Bekor qilish")
async def cart_phone_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Buyurtma bekor qilindi.", reply_markup=menu_for(message.from_user.id))


@router.message(CartCheckoutState.phone)
async def cart_phone(message: Message, state: FSMContext):
    if message.contact:
        # Kontakt ulashilsa — ishonchli manba: chet el raqami ham qabul qilinadi.
        raw = message.contact.phone_number
        phone = normalize_uz_phone(raw) or ("+" + str(raw).lstrip("+"))
    else:
        phone = normalize_uz_phone(message.text)
        if not phone:
            await message.answer(
                "Raqam noto'g'ri kiritildi. Namuna: <b>+998 90 123 45 67</b>\n"
                "Pastdagi tugma orqali yuborsangiz ham bo'ladi:",
                parse_mode="HTML", reply_markup=phone_keyboard,
            )
            return
    set_user_field(message.from_user.id, "phone", phone)

    data = await state.get_data()
    uid = message.from_user.id
    address = data.get("address", "—")

    # Savatdagi har bir (buyurtma qilish mumkin) qatorni hisoblaymiz.
    lines = []  # (p, qty, unit, total, commission, color)
    combined_total = 0
    skipped = []
    for it in get_cart(uid):
        p = get_product_by_id(it.get("product_id"))
        if not p or p.get("is_finished"):
            if p:
                skipped.append(p.get("name", "—"))
            continue
        qty = max(1, min(_max_qty(p), int(it.get("quantity", 1))))
        unit = _unit_price(p, data)
        total = unit * qty
        commission = int(total * settings.COMMISSION_RATE)
        lines.append((p, qty, unit, total, commission, it.get("color") or ""))
        combined_total += total

    if not lines:
        await state.clear()
        await message.answer(
            "Afsuski, savatdagi mahsulotlar tugab qoldi. Buyurtma qabul qilinmadi.",
            reply_markup=menu_for(uid),
        )
        return

    fee = delivery_fee_for(combined_total)  # umumiy summага qarab BIR MARTA
    group_id = f"g{int(time.time())}_{uid}"
    promo_code = data.get("promo_code")
    promo_percent = data.get("promo_percent", 0) or 0

    created = []   # (order_id, p, qty, unit, total, commission)
    combined_prepay = 0
    for i, (p, qty, unit, total, commission, color) in enumerate(lines):
        oid = save_order({
            "buyer_id":      uid,
            "buyer_name":    message.from_user.full_name,
            "buyer_username": message.from_user.username,
            "seller_id":     p["seller_id"],
            "product_id":    p["id"],
            "product_name":  p["name"],
            "quantity":      qty,
            "unit_price":    unit,
            "total":         total,
            "prepay":        commission,
            "commission":    commission,
            "delivery_fee":  fee if i == 0 else 0,   # yetkazish bir marta
            "fulfillment":   "delivery",
            "delivery":      "taxi",
            "address":       address,
            "phone":         phone,
            "color":         color,
            "promo_code":    promo_code or "",
            "promo_percent": promo_percent,
            "status":        "pending",
            "receipt":       None,
            "group_id":      group_id,
        })
        created.append((oid, p, qty, unit, total, commission))
        combined_prepay += commission

    if promo_code:
        try:
            use_promo(promo_code)
        except Exception:
            pass

    clear_cart(uid)
    await state.set_state(CartCheckoutState.receipt)
    await state.update_data(group_id=group_id)

    # ── Sellerlarga xabar HOZIR YUBORILMAYDI ──
    # Xaridor boshlang'ich to'lovni qilib, admin tasdiqlamaguncha kutiladi.
    # Har bir buyurtma uchun seller xabari admin to'lovni tasdiqlaganda
    # yuboriladi (app/handlers/admin.py → _confirm_single_order).

    # ── Xaridorga: BITTA umumiy oldi-to'lov xabari (qisqa, bir ekranlik) ──
    platform_card = settings.PLATFORM_CARD or "⚠️ admin kartani sozlamagan"
    card_name = f" ({settings.PLATFORM_CARD_NAME})" if settings.PLATFORM_CARD_NAME else ""
    pct = int(settings.COMMISSION_RATE * 100)
    remain = max(combined_total - combined_prepay, 0)
    fee_note = f" + yetkazib berish {money(fee)}" if fee else ""
    promo_summary = f"Promo {promo_code}: −{promo_percent}%\n" if promo_code else ""

    items_txt = ""
    for oid, p, qty, unit, total, commission in created:
        items_txt += f"• {p['name']} — {qty} × {money(unit)} = <b>{money(total)}</b>\n"

    skipped_txt = ""
    if skipped:
        skipped_txt = "Tugagani uchun qo'shilmadi: " + ", ".join(skipped) + "\n"

    await message.answer(
        f"<b>Buyurtma qabul qilindi</b> ({len(created)} ta mahsulot)\n"
        f"{divider()}\n"
        f"{items_txt}"
        f"{skipped_txt}"
        f"{promo_summary}"
        f"Jami: <b>{money(combined_total)}</b>\n"
        f"Yetkazib berish: {delivery_text(fee)}\n"
        f"Manzil: {address}\n"
        f"Telefon: {phone}\n\n"
        f"Oldindan to'lov ({pct}%): <b>{money(combined_prepay)}</b>\n"
        f"Karta: <code>{platform_card}</code>{card_name}\n"
        f"Qolgan {money(remain)}{fee_note} kurierga naqd yoki karta orqali to'lanadi.\n\n"
        f"<b>To'lov chekini (rasm yoki PDF) shu yerga yuboring</b> — "
        f"chek tasdiqlangach buyurtma tayyorlanadi.\n"
        f"Savollar uchun: @{settings.ADMIN_USERNAME}",
        parse_mode="HTML", reply_markup=cancel_keyboard,
    )

    # ── AUKSION guruhiga buyurtmalar SHU YERDA YUBORILMAYDI ──
    # Har bir buyurtma admin to'lovni tasdiqlaganda guruhga tushadi
    # (app/handlers/admin.py → _confirm_single_order).


# ─── Savat cheki qabul qilinadi → admin tasdig'iga (guruh) ───────────────────
@router.message(CartCheckoutState.receipt, F.text == "❌ Bekor qilish")
async def cart_receipt_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Chek yuborish bekor qilindi. Buyurtmalaringizni «📦 Buyurtmalarim» "
        "bo'limidan ko'rishingiz mumkin.",
        reply_markup=menu_for(message.from_user.id),
    )


@router.message(CartCheckoutState.receipt, F.photo | F.document)
async def cart_receipt(message: Message, state: FSMContext):
    data = await state.get_data()
    group_id = data.get("group_id")
    orders = get_orders_by_group(group_id) if group_id else []
    if not orders:
        await state.clear()
        await message.answer("❌ Buyurtma topilmadi.", reply_markup=menu_for(message.from_user.id))
        return

    receipt_id, rtype = _extract_receipt(message)
    if receipt_id is None:
        await message.answer(
            "Iltimos, to'lov chekining <b>rasmini yoki PDF faylini</b> yuboring "
            "(yoki ❌ Bekor qilish).",
            parse_mode="HTML",
        )
        return
    for o in orders:
        update_order_fields(o["id"], {"receipt": receipt_id, "receipt_type": rtype})
    await state.clear()

    # Chek rasmini xaridor chatidan o'chiramiz — aks holda Telegram rasm
    # ko'ruvchisida (surganda) mahsulot rasmlariga aralashib ko'rinadi. Rasm
    # admin tomonida saqlanib qoladi (file_id allaqachon olingan).
    try:
        await message.delete()
    except Exception:
        pass

    await message.answer(
        f"Chek qabul qilindi. Buyurtmalaringiz ({len(orders)} ta) to'lovi "
        f"tekshirilmoqda — tasdiqlangach xabar beramiz.",
        reply_markup=menu_for(message.from_user.id),
    )

    # Adminga: BITTA xabar — barcha buyurtmalar + tasdiqlash tugmalari
    pct = int(settings.COMMISSION_RATE * 100)
    total_prepay = sum(int(o.get("prepay", 0)) for o in orders)
    o0 = orders[0]
    items_txt = "".join(
        f"• #{o['id']}  {o.get('product_name','—')} — {o.get('quantity',1)} dona\n"
        for o in orders
    )
    caption = (
        f"<b>Savat buyurtmasi — to'lov cheki</b>\n"
        f"({len(orders)} ta mahsulot)\n\n"
        f"{items_txt}\n"
        f"Umumiy oldindan to'lov ({pct}%): <b>{total_prepay:,} so'm</b>\n"
        f"Xaridor: {o0.get('buyer_name','—')}\n"
        f"Telefon: {o0.get('phone','—')}\n"
        f"Manzil: {o0.get('address','—')}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiq + 🟢 Bugun",   callback_data=f"paycfmg_{group_id}_today"),
            InlineKeyboardButton(text="✅ Tasdiq + 🟡 24 soat", callback_data=f"paycfmg_{group_id}_24h"),
        ],
        [
            InlineKeyboardButton(text="❌ Rad etish",            callback_data=f"payrejg_{group_id}"),
        ],
    ])
    try:
        await _send_receipt(settings.OWNER_ID, receipt_id, rtype, caption, kb)
    except Exception:
        pass


@router.message(CartCheckoutState.receipt)
async def cart_receipt_invalid(message: Message):
    await message.answer(
        "Iltimos, to'lov chekining <b>rasmini yoki PDF faylini</b> yuboring "
        "(yoki ❌ Bekor qilish).",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("gsendrcpt_"))
async def cart_resend_receipt(call: CallbackQuery, state: FSMContext):
    group_id = call.data.split("_", 1)[1]
    orders = get_orders_by_group(group_id)
    if not orders or orders[0].get("buyer_id") != call.from_user.id:
        await call.answer("Topilmadi."); return
    await call.answer()
    await state.set_state(CartCheckoutState.receipt)
    await state.update_data(group_id=group_id)
    await call.message.answer(
        "Savat buyurtmangiz uchun to'lov chekining rasmini yoki PDF faylini qayta yuboring:",
        reply_markup=cancel_keyboard,
    )


# ─── Buyurtmalarim ──────────────────────────────────────────────────────────────
@router.message(F.text == "📦 Buyurtmalarim")
async def my_orders(message: Message):
    if is_shop_member(message.from_user.id):
        await message.answer(
            "Siz sotuvchisiz. Buyurtmalarni Sotuvchi paneli orqali ko'ring:",
            reply_markup=seller_main_menu
        )
        return
    orders = get_buyer_orders(message.from_user.id)
    if not orders:
        await message.answer("Hozircha buyurtma yo'q.")
        return
    text = f"<b>Buyurtmalarim</b>\n{divider()}\n\n"
    rows = []
    for o in orders[-10:]:
        dlv = DELIVERY_LABELS.get(o.get("delivery",""), o.get("delivery",""))
        status = ORDER_STATUSES.get(o.get("status",""), o.get("status",""))
        text += (
            f"<b>#{o['id']}</b> — {o.get('product_name','—')}\n"
            f"   Summa: {o.get('total',0):,} so'm\n"
            f"   Yetkazib berish: {dlv}\n"
            f"   Holat: {status}\n"
        )
        if o.get("status") not in ("delivered","cancelled"):
            if o.get("delivery") == "pickup":
                text += "   To'lov tasdiqlangach do'kon bilan bog'lanasiz.\n"
            else:
                text += "   Yetkazib berish — shu kunning o'zida.\n"
        # Chek hali yuborilmagan pending buyurtmaga — chek yuborish tugmasi
        if o.get("status") == "pending" and not o.get("receipt"):
            rows.append([InlineKeyboardButton(
                text=f"#{o['id']} uchun chek yuborish",
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
        f"Buyurtma #{oid} uchun to'lov chekining rasmini yoki PDF faylini yuboring:",
        reply_markup=cancel_keyboard
    )
    await call.answer()


# ─── Qidirish ────────────────────────────────────────────────────────────────
@router.message(F.text.in_({"🔎 Qidirish", "🔍 Qidiruv"}))
async def search_start(message: Message, state: FSMContext):
    if is_shop_member(message.from_user.id):
        await message.answer(
            "Siz sotuvchisiz. Quyidagi menyudan foydalaning:",
            reply_markup=seller_main_menu
        )
        return
    await state.set_state(SearchState.query)
    await message.answer("Mahsulot nomini kiriting:")


# Foydalanuvchining oxirgi qidiruv so'zi — narx bo'yicha qayta saralash uchun
# (sort tugmasi bosilganda qidiruvni qaytadan ishlatamiz). Faqat xotirada.
_LAST_SEARCH: dict[int, str] = {}


def _sorted_search_kb(results: list, order: str) -> InlineKeyboardMarkup:
    """Natijalarni narx bo'yicha saralab, tugmalar ro'yxati + saralash tugmalari."""
    items = sorted(results, key=lambda p: p.get("price", 0), reverse=(order == "exp"))
    rows = []
    for p in items[:30]:
        price = p.get("price", 0)
        fin = "  ·  tugagan" if p.get("is_finished") else ""
        rows.append([InlineKeyboardButton(
            text=f"{p['name']} — {price:,} so'm{fin}",
            callback_data=f"prod_{p['id']}"
        )])
    cheap_lbl = ("✓ " if order == "cheap" else "") + "Arzondan"
    exp_lbl   = ("✓ " if order == "exp" else "") + "Qimmatdan"
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
    await call.answer("Arzondan" if order == "cheap" else "Qimmatdan")
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
        await message.answer("Hech narsa topilmadi. Boshqa so'z bilan sinab ko'ring.", reply_markup=main_menu)
        return
    _LAST_SEARCH[message.from_user.id] = query

    await message.answer(
        f"<b>{len(results)} ta natija topildi</b>",
        parse_mode="HTML"
    )

    # Qidiruvda yuborilgan rasm xabarlarini kuzatamiz — keyin mahsulot/do'kon
    # ochilganda ular ham o'chiriladi (Telegram ko'ruvchisida aralashmasligi uchun).
    photo_ids = []
    for p in results[:5]:
        caption = _product_caption(p)
        kb_rows = []
        if not p.get("is_finished"):
            kb_rows.append([InlineKeyboardButton(text="Buyurtma berish", callback_data=f"order_{p['id']}")])
        kb_rows.append([InlineKeyboardButton(text="Batafsil", callback_data=f"prod_{p['id']}")])
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
            "<b>Barcha natijalar</b> — narx bo'yicha saralang:",
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
    star_str = "★" * stars
    try:
        await call.message.edit_text(f"Bahoyingiz qabul qilindi: {star_str} ({stars}/5)")
    except Exception:
        await call.message.answer(f"Bahoyingiz qabul qilindi: {star_str} ({stars}/5)")
    await call.answer("Rahmat!")
