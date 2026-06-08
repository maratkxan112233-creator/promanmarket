import io
import os
import zipfile
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.storage import (
    get_applications, update_application_status, add_seller, get_sellers,
    get_all_products, admin_delete_product, update_product, get_product_by_id,
    update_seller, delete_seller, delete_user, get_orders, get_seller_reviews,
    get_order_by_id, update_order_status, get_seller_orders, get_seller,
    get_seller_products, add_product, delete_all_products,
    get_admins, add_admin, remove_admin, is_sub_admin,
    add_audit, get_audit,
    get_cities, add_city, remove_city, get_user,
)
from app.album import collect
from app.app.config.settings import settings

router = Router()

# ─── Robust navigatsiya: eski (48soat+) yoki rasm xabarda edit_text ishlamaydi ──
async def _admin_nav(call, text, kb):
    try:
        if call.message.photo or call.message.video or call.message.document:
            try: await call.message.delete()
            except Exception: pass
            await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
        else:
            await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        try:
            await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
        except Exception:
            pass


class AdminSellerSearch(StatesGroup):
    query = State()


def _sellers_keyboard(items):
    rows = []
    for uid, s in items:
        rows.append([InlineKeyboardButton(
            text=f"✏️ {s['shop_name']}",
            callback_data=f"aseller_{uid}"
        )])
    rows.append([InlineKeyboardButton(text="🔍 Seller qidirish", callback_data="seller_search")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _sellers_text(items):
    from app.storage import get_seller_rating, get_seller_orders
    lines = ["🏪 <b>Sellerlar</b> — jami " + str(len(items)) + " ta\n"]
    for i, (uid, s) in enumerate(items, 1):
        rating, cnt = get_seller_rating(int(uid))
        ordc = len(get_seller_orders(int(uid)))
        card = s.get("card_number", "")
        last4 = card[-4:] if card else "—"
        lines.append(
            f"<b>{i}. {s['shop_name']}</b>\n"
            f"   👤 {s['full_name']}\n"
            f"   🏙 {s.get('city','—')}\n"
            f"   📱 {s.get('phone','—')}\n"
            f"   💳 **** {last4}   ⭐ {rating} ({cnt})   🛒 {ordc} zakaz"
        )
    return "\n".join(lines)


def is_owner(uid: int) -> bool:
    return uid == settings.OWNER_ID


def is_admin(uid: int) -> bool:
    # Owner yoki sub-admin
    return is_owner(uid) or is_sub_admin(uid)


def _actor_name(u) -> str:
    return u.full_name + (f" (@{u.username})" if u.username else "")


def _admin_city(uid: int):
    a = get_admins().get(str(uid))
    return a.get("city") if a else None


def _log(actor, action: str, target: str = ""):
    role = "Owner" if is_owner(actor.id) else "Admin"
    add_audit({
        "admin_id":   actor.id,
        "admin_name": _actor_name(actor),
        "role":       role,
        "action":     action,
        "target":     target,
    })


class AdminAddProduct(StatesGroup):
    seller = State()
    name        = State()
    description = State()
    price       = State()
    photo       = State()


# ─── States ──────────────────────────────────────────────────────────────────
class AdminEditShop(StatesGroup):
    waiting_value = State()

class AdminEditProduct(StatesGroup):
    waiting_field = State()
    waiting_value = State()


# ─── Menus ───────────────────────────────────────────────────────────────────
def admin_menu_kb(uid: int):
    if is_owner(uid):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Arizalar",        callback_data="admin_applications")],
            [InlineKeyboardButton(text="🏪 Sellerlar",        callback_data="admin_sellers")],
            [InlineKeyboardButton(text="➕ Mahsulot qo'shish", callback_data="admin_addprod")],
            [InlineKeyboardButton(text="📦 Mahsulotlar",      callback_data="admin_products")],
            [InlineKeyboardButton(text="🧹 Mahsulotlarni tozalash", callback_data="admin_clearprods")],
            [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")],
            [InlineKeyboardButton(text="🏙 Shaharlar",        callback_data="admin_cities")],
            [InlineKeyboardButton(text="📊 Statistika",       callback_data="admin_stats")],
            [InlineKeyboardButton(text="📈 Excel hisobot",    callback_data="admin_excel_menu")],
            [InlineKeyboardButton(text="👮 Adminlar",         callback_data="admin_admins")],
            [InlineKeyboardButton(text="💾 Zaxira (backup)",  callback_data="admin_backup")],
            [InlineKeyboardButton(text="📜 Jurnal (Word)",    callback_data="admin_log")],
        ])
    # Sub-admin: faqat seller qo'shish (arizalar) + mahsulot qo'shish
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Arizalar (seller qo'shish)", callback_data="admin_applications")],
        [InlineKeyboardButton(text="➕ Mahsulot qo'shish",          callback_data="admin_addprod")],
    ])


# ─── /admin ──────────────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    if is_owner(message.from_user.id):
        apps = get_applications()
        pending = [a for a in apps.values() if a.get("status") == "pending"]
        text = (
            f"👑 <b>Admin Panel</b>\n\n"
            f"⏳ Kutilayotgan arizalar: <b>{len(pending)}</b>\n"
            f"🏪 Jami sellerlar: <b>{len(get_sellers())}</b>\n"
            f"👮 Sub-adminlar: <b>{len(get_admins())}</b>"
        )
    else:
        text = (
            "🛡 <b>Admin Panel</b> (yordamchi)\n\n"
            "Sizda quyidagi huquqlar bor:\n"
            "• Arizalarni tasdiqlab seller qo'shish\n"
            "• Mahsulot qo'shish"
        )
    await message.answer(text, reply_markup=admin_menu_kb(message.from_user.id), parse_mode="HTML")


@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    if is_owner(call.from_user.id):
        apps = get_applications()
        pending = [a for a in apps.values() if a.get("status") == "pending"]
        text = (
            f"👑 <b>Admin Panel</b>\n\n"
            f"⏳ Kutilayotgan arizalar: <b>{len(pending)}</b>\n"
            f"🏪 Jami sellerlar: <b>{len(get_sellers())}</b>\n"
            f"👮 Sub-adminlar: <b>{len(get_admins())}</b>"
        )
    else:
        text = (
            "🛡 <b>Admin Panel</b> (yordamchi)\n\n"
            "• Arizalarni tasdiqlab seller qo'shish\n"
            "• Mahsulot qo'shish"
        )
    await _admin_nav(call, text, admin_menu_kb(call.from_user.id))
    await call.answer()


# ─── Arizalar ────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_applications")
async def show_applications(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    pending = {uid: a for uid, a in get_applications().items() if a.get("status") == "pending"}
    if not is_owner(call.from_user.id):
        mycity = _admin_city(call.from_user.id)
        pending = {uid: a for uid, a in pending.items() if a.get("city") == mycity}
    if not pending:
        await call.message.edit_text("✅ Kutilayotgan ariza yo'q.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
        ))
        return
    for uid, app in pending.items():
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{uid}"),
            InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"reject_{uid}"),
        ]])
        text = (
            f"📋 <b>Ariza #{uid}</b>\n\n"
            f"👤 {app.get('full_name')}\n"
            f"📱 {app.get('phone')}\n"
            f"🏙 Shahar: {app.get('city','—')}\n"
            f"🏪 {app.get('shop_name')}\n"
            f"💳 **** {app.get('card_number','')[-4:]}"
        )
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")
        if app.get("passport_photo"):
            await call.message.answer_photo(app["passport_photo"], caption="📄 Pasport")
        if app.get("selfie_photo"):
            await call.message.answer_photo(app["selfie_photo"], caption="🤳 Selfi")
    await call.answer()


@router.callback_query(F.data.startswith("approve_"))
async def approve_seller(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    uid = int(call.data.split("_")[1])
    app = get_applications().get(str(uid))
    if not app:
        await call.answer("Ariza topilmadi."); return
    update_application_status(uid, "approved")
    add_seller(uid, {
        "user_id": uid, "full_name": app["full_name"],
        "shop_name": app["shop_name"], "phone": app["phone"],
        "card_number": app["card_number"], "city": app.get("city", ""),
    })
    _log(call.from_user, "Seller qo'shildi",
         f"{app['full_name']} — do'kon: {app['shop_name']} (ID:{uid}, {app.get('city','—')})")
    await call.message.edit_text(f"✅ {app['full_name']} seller sifatida tasdiqlandi!")
    try:
        from app.bot.bot import bot
        await bot.send_message(uid, "🎉 Seller arizangiz tasdiqlandi!\n/seller buyrug'i orqali panel oching.")
    except Exception: pass
    await call.answer("✅ Tasdiqlandi!")


@router.callback_query(F.data.startswith("reject_"))
async def reject_seller_cb(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    uid = int(call.data.split("_")[1])
    app = get_applications().get(str(uid))
    if not app:
        await call.answer("Ariza topilmadi."); return
    update_application_status(uid, "rejected")
    _log(call.from_user, "Ariza rad etildi", f"{app['full_name']} (ID:{uid})")
    await call.message.edit_text(f"❌ {app['full_name']} arizasi rad etildi.")
    try:
        from app.bot.bot import bot
        await bot.send_message(uid, "❌ Seller arizangiz rad etildi.")
    except Exception: pass
    await call.answer("❌ Rad etildi!")


# ─── To'lov chekini tasdiqlash / rad etish ───────────────────────────────────
@router.callback_query(F.data.startswith("paycfm_"))
async def confirm_payment(call: CallbackQuery):
    if not is_owner(call.from_user.id):
        await call.answer("Ruxsat yo'q.", show_alert=True); return
    # Tugma spinnerini DARHOL to'xtatamiz — "qotib qolish" oldini oladi
    await call.answer("✅ To'lov tasdiqlandi!")

    oid = int(call.data.split("_")[1])
    o = get_order_by_id(oid)
    if not o:
        try: await call.message.answer("❌ Zakaz topilmadi.")
        except Exception: pass
        return

    update_order_status(oid, "paid")
    try:
        _log(call.from_user, "To'lov tasdiqlandi", f"Zakaz #{oid}")
    except Exception:
        pass

    try:
        await call.message.edit_caption(
            caption=(call.message.caption or "") + "\n\n✅ TO'LOV TASDIQLANDI",
        )
    except Exception:
        pass

    from app.bot.bot import bot
    is_pickup = o.get("delivery") == "pickup"
    dlv_map = {
        "pickup": "🚶 O'zi olib ketadi",
        "taxi": "🚕 Taksi pochta (shu bugunoq)",
        "btc": "📦 BTC Pochta", "emu": "🚀 EMU Express", "uzum": "🍊 Uzum Pochta",
    }
    dlv_label = dlv_map.get(o.get("delivery", ""), o.get("delivery", "—"))

    if is_pickup:
        # ── PICKUP: xaridor o'zi olib ketadi ──
        # Sellerga xaridor danniylari KO'RSATILMAYDI.
        # Xaridorga esa do'kon kontaktini beramiz — borib olib ketishi uchun.
        shop = get_seller(o["seller_id"]) or {}
        shop_name = shop.get("shop_name", "—")
        shop_phone = shop.get("phone", "—")
        shop_city = shop.get("city", "—")

        # Xaridorga — do'kon kontakti ochiladi
        try:
            await bot.send_message(
                o["buyer_id"],
                f"✅ <b>Zakaz #{oid} to'lovi tasdiqlandi!</b>\n"
                f"📦 {o.get('product_name','—')}\n\n"
                f"🚶 <b>Mahsulotni o'zingiz olib ketasiz.</b>\n"
                f"🏪 Do'kon: {shop_name}\n"
                f"🏙 Shahar: {shop_city}\n"
                f"📱 Do'kon tel: {shop_phone}\n\n"
                f"Do'kon bilan bog'lanib, mahsulotni olib keting.",
                parse_mode="HTML"
            )
        except Exception:
            pass

        # Sellerga — XARIDOR DANNIYLARI KO'RSATILMAYDI
        try:
            await bot.send_message(
                o["seller_id"],
                f"💳 <b>Zakaz #{oid} — to'lov tasdiqlandi!</b>\n\n"
                f"📦 {o.get('product_name','—')}\n"
                f"🚚 {dlv_label}\n\n"
                f"🔒 <b>Xaridor o'zi olib ketadi — ma'lumotlari ko'rsatilmaydi.</b>\n"
                f"Xaridor do'kon raqamiga bog'lanib, mahsulotni olib ketadi.\n"
                f"💡 <i>Eslatma: bu zakaz uchun platforma xizmat haqi "
                f"({o.get('commission', int(o.get('total',0)*0.1)):,} so'm — 10%) "
                f"xaridorning oldi-to'lovidan olingan.</i>\n"
                f"Mahsulotni tayyorlab qo'ying. /orders",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        # ── TAKSI/DOSTAVKA: xaridor danniylari ENDI ochiladi (to'lov tasdiqlangani uchun) ──
        # Xaridorga
        try:
            await bot.send_message(
                o["buyer_id"],
                f"✅ <b>Zakaz #{oid} to'lovi tasdiqlandi!</b>\n"
                f"📦 {o.get('product_name','—')}\n"
                f"🚕 Yetkazib berish: SHU BUGUNOQ (taksi pochta)\n"
                f"Buyurtmangiz tayyorlanmoqda. 🔄",
                parse_mode="HTML"
            )
        except Exception:
            pass

        # Sellerga — to'liq xaridor ma'lumotlari
        try:
            await bot.send_message(
                o["seller_id"],
                f"💳 <b>Zakaz #{oid} — to'lov tasdiqlandi!</b>\n"
                f"🔓 <b>Xaridor ma'lumotlari ochildi:</b>\n\n"
                f"📦 {o.get('product_name','—')}\n"
                f"👤 {o.get('buyer_name','—')}\n"
                f"📱 {o.get('phone','—')}\n"
                f"📍 {o.get('address','—')}\n"
                f"🚚 {dlv_label}\n\n"
                f"💡 <i>Eslatma: bu zakaz uchun platforma xizmat haqi "
                f"({o.get('commission', int(o.get('total',0)*0.1)):,} so'm — 10%) "
                f"xaridorning oldi-to'lovidan olingan.</i>\n"
                f"Endi buyurtmani tayyorlab, taksi orqali manzilga jo'nating. /orders",
                parse_mode="HTML"
            )
        except Exception:
            pass


@router.callback_query(F.data.startswith("payrej_"))
async def reject_payment(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    oid = int(call.data.split("_")[1])
    o = get_order_by_id(oid)
    if not o:
        await call.answer("Zakaz topilmadi.", show_alert=True); return
    try:
        await call.message.edit_caption(
            caption=(call.message.caption or "") + "\n\n❌ CHEK RAD ETILDI",
        )
    except Exception:
        pass
    try:
        from app.bot.bot import bot
        await bot.send_message(
            o["buyer_id"],
            f"❌ <b>Zakaz #{oid} cheki rad etildi.</b>\n"
            f"Iltimos, to'g'ri to'lov chekini qayta yuboring:\n"
            f"📦 Zakazlarim → 🧾 chek yuborish",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await call.answer("❌ Rad etildi.")


# ─── Sellerlar (ko'rish + tahrirlash + o'chirish) ────────────────────────────
@router.callback_query(F.data == "admin_sellers")
async def show_sellers(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    sellers = get_sellers()
    if not sellers:
        await _admin_nav(call, "Hozircha seller yo'q.", InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
        ))
        await call.answer()
        return
    items = list(sellers.items())
    await _admin_nav(call, _sellers_text(items), _sellers_keyboard(items))
    await call.answer()


# ─── Seller qidirish ─────────────────────────────────────────────────────────
@router.callback_query(F.data == "seller_search")
async def seller_search_start(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    await state.set_state(AdminSellerSearch.query)
    await call.message.answer("🔍 Do'kon nomi yoki seller ismini kiriting:")
    await call.answer()


@router.message(AdminSellerSearch.query)
async def seller_search_do(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        await state.clear(); return
    await state.clear()
    q = (message.text or "").strip().lower()
    items = [
        (uid, s) for uid, s in get_sellers().items()
        if q in s.get("shop_name", "").lower() or q in s.get("full_name", "").lower()
    ]
    if not items:
        await message.answer(
            f"😔 '{message.text}' bo'yicha seller topilmadi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏪 Barcha sellerlar", callback_data="admin_sellers")]
            ])
        )
        return
    await message.answer(_sellers_text(items), parse_mode="HTML",
                         reply_markup=_sellers_keyboard(items))


@router.callback_query(F.data.startswith("aseller_"))
async def seller_detail(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    uid = call.data.split("_")[1]
    s = get_sellers().get(uid)
    if not s:
        await call.answer("Seller topilmadi."); return
    from app.storage import get_seller_rating, get_seller_products
    rating, cnt = get_seller_rating(int(uid))
    stars = "⭐" * int(rating) if rating else "—"
    prods = get_seller_products(int(uid))
    text = (
        f"🏪 <b>{s['shop_name']}</b>\n\n"
        f"👤 {s['full_name']}\n"
        f"🏙 Shahar: {s.get('city','—')}\n"
        f"📱 {s['phone']}\n"
        f"💳 {s.get('card_number','—')}\n"
        f"🆔 ID: {uid}\n"
        f"📦 Mahsulotlar: {len(prods)} ta\n"
        f"⭐ Reyting: {stars} {rating} ({cnt} ta baho)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Do'kon nomini o'zgartirish", callback_data=f"edit_shop_name_{uid}")],
        [InlineKeyboardButton(text="✏️ Karta raqamini o'zgartirish", callback_data=f"edit_shop_card_{uid}")],
        [InlineKeyboardButton(text="✏️ Telefon raqamini o'zgartirish", callback_data=f"edit_shop_phone_{uid}")],
        [InlineKeyboardButton(text="🗑 Sellerni o'chirish", callback_data=f"del_seller_{uid}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_sellers")],
    ])
    await _admin_nav(call, text, kb)
    await call.answer()


@router.callback_query(F.data.startswith("edit_shop_"))
async def edit_shop_start(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    parts = call.data.split("_")          # edit_shop_name_123  → ['edit','shop','name','123']
    field = parts[2]                       # name | card | phone
    uid   = parts[3]
    field_labels = {"name": "Do'kon nomi", "card": "Karta raqami", "phone": "Telefon"}
    await state.set_state(AdminEditShop.waiting_value)
    await state.update_data(field=field, uid=uid)
    await call.message.answer(f"✏️ Yangi <b>{field_labels.get(field,'qiymat')}</b>ni kiriting:", parse_mode="HTML")
    await call.answer()


@router.message(AdminEditShop.waiting_value)
async def edit_shop_save(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        await state.clear(); return
    data = await state.get_data()
    field = data["field"]
    uid   = int(data["uid"])
    mapping = {"name": "shop_name", "card": "card_number", "phone": "phone"}
    update_seller(uid, {mapping[field]: message.text})
    await state.clear()
    await message.answer(f"✅ Seller ma'lumoti yangilandi!")


@router.callback_query(F.data.startswith("del_seller_"))
async def del_seller_cb(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    uid = int(call.data.split("_")[2])
    sellers = get_sellers()
    name = sellers.get(str(uid), {}).get("shop_name", "—")
    delete_seller(uid)
    _log(call.from_user, "Seller o'chirildi", f"{name} (ID:{uid})")
    await call.message.edit_text(f"🗑 {name} selleri o'chirildi.")
    await call.answer("O'chirildi")


# ─── Mahsulotlar (admin) ─────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_products")
async def admin_products(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    products = get_all_products()
    if not products:
        await call.message.edit_text("Mahsulot yo'q.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
        ))
        return
    rows = []
    for p in products:
        rows.append([InlineKeyboardButton(
            text=f"📦 {p['name']} — {p['price']:,} so'm",
            callback_data=f"aprod_{p['id']}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    await call.message.edit_text("📦 <b>Barcha mahsulotlar:</b>", parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data.startswith("aprod_"))
async def admin_product_detail(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    pid = int(call.data.split("_")[1])
    p = get_product_by_id(pid)
    if not p:
        await call.answer("Topilmadi."); return
    text = (
        f"📦 <b>{p['name']}</b>\n"
        f"🏪 {p.get('shop_name','—')}\n"
        f"📝 {p.get('description','—')}\n"
        f"💰 {p['price']:,} so'm"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish",  callback_data=f"eprod_name_{pid}")],
        [InlineKeyboardButton(text="✏️ Narxini o'zgartirish", callback_data=f"eprod_price_{pid}")],
        [InlineKeyboardButton(text="✏️ Tavsifini o'zgartirish", callback_data=f"eprod_desc_{pid}")],
        [InlineKeyboardButton(text="🗑 O'chirish",            callback_data=f"dprod_{pid}")],
        [InlineKeyboardButton(text="🔙 Orqaga",               callback_data="admin_products")],
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("eprod_"))
async def edit_product_start(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    parts = call.data.split("_")   # eprod_name_5
    field = parts[1]
    pid   = int(parts[2])
    labels = {"name": "Nom", "price": "Narx (faqat raqam)", "desc": "Tavsif"}
    await state.set_state(AdminEditProduct.waiting_value)
    await state.update_data(field=field, pid=pid)
    await call.message.answer(f"✏️ Yangi <b>{labels.get(field,'qiymat')}</b>ni kiriting:", parse_mode="HTML")
    await call.answer()


@router.message(AdminEditProduct.waiting_value)
async def edit_product_save(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        await state.clear(); return
    data  = await state.get_data()
    field = data["field"]
    pid   = data["pid"]
    mapping = {"name": "name", "price": "price", "desc": "description"}
    value = int(message.text) if field == "price" and message.text.isdigit() else message.text
    update_product(pid, {mapping[field]: value})
    await state.clear()
    await message.answer("✅ Mahsulot yangilandi!")


@router.callback_query(F.data.startswith("dprod_"))
async def admin_del_product(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    pid = int(call.data.split("_")[1])
    _p = get_product_by_id(pid)
    admin_delete_product(pid)
    _log(call.from_user, "Mahsulot o'chirildi",
         f"{_p['name']} (ID:{pid})" if _p else f"ID:{pid}")
    await call.message.edit_text("🗑 Mahsulot o'chirildi.")
    await call.answer("O'chirildi")


# ─── Hamma mahsulotni tozalash (faqat owner) ─────────────────────────────────
@router.callback_query(F.data == "admin_clearprods")
async def admin_clear_prods(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    n = len(get_all_products())
    if n == 0:
        await call.answer("Mahsulot yo'q.", show_alert=True); return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"⚠️ Ha, {n} ta mahsulotni o'chir",
                              callback_data="admin_clearprods_yes")],
        [InlineKeyboardButton(text="🔙 Bekor qilish", callback_data="admin_back")],
    ])
    await _admin_nav(
        call,
        f"🧹 <b>Hamma mahsulotni tozalash</b>\n\n"
        f"Hozir <b>{n} ta</b> mahsulot bor.\n"
        f"Hammasini o'chirsangiz, do'konlardagi barcha mahsulotlar "
        f"(rasmlari bilan) yo'qoladi. Buni qaytarib bo'lmaydi.\n\n"
        f"Davom etasizmi?",
        kb,
    )
    await call.answer()


@router.callback_query(F.data == "admin_clearprods_yes")
async def admin_clear_prods_yes(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    n = delete_all_products()
    _log(call.from_user, "Hamma mahsulot tozalandi", f"{n} ta")
    await _admin_nav(
        call,
        f"✅ <b>{n} ta</b> mahsulot o'chirildi.\n"
        f"Endi mahsulotlarni qaytadan qo'shishingiz mumkin.",
        admin_menu_kb(call.from_user.id),
    )
    await call.answer("Tozalandi")


# ─── Foydalanuvchilar ────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    from app.storage import get_users
    users = get_users()
    sellers = get_sellers()
    text = f"👥 <b>Foydalanuvchilar:</b> {len(users)} ta\n🏪 Sellerlar: {len(sellers)} ta\n\n"
    rows = []
    for uid, u in list(users.items())[:20]:
        role = "🏪" if uid in sellers else "🛍"
        rows.append([InlineKeyboardButton(
            text=f"{role} {u.get('full_name','ID:'+uid)}",
            callback_data=f"auser_{uid}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    await call.message.edit_text(text, parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data.startswith("auser_"))
async def admin_user_detail(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    uid = call.data.split("_")[1]
    from app.storage import get_users
    u = get_users().get(uid, {})
    sellers = get_sellers()
    role = "🏪 Seller" if uid in sellers else "🛍 Xaridor"
    text = f"👤 <b>{u.get('full_name','Noma lum')}</b>\nID: {uid}\nRol: {role}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_user_{uid}")],
        [InlineKeyboardButton(text="🔙 Orqaga",    callback_data="admin_users")],
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("del_user_"))
async def del_user_cb(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    uid = int(call.data.split("_")[2])
    delete_user(uid)
    delete_seller(uid)
    _log(call.from_user, "Foydalanuvchi o'chirildi", f"ID:{uid}")
    await call.message.edit_text(f"🗑 Foydalanuvchi (ID:{uid}) o'chirildi.")
    await call.answer("O'chirildi")


# ─── Statistika ──────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def show_stats(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    apps = get_applications()
    orders = get_orders()
    revenue = sum(o.get("total", 0) for o in orders)
    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"📋 Arizalar: {len(apps)} ta\n"
        f"✅ Tasdiqlangan: {len([a for a in apps.values() if a.get('status')=='approved'])}\n"
        f"🏪 Sellerlar: {len(get_sellers())}\n"
        f"📦 Mahsulotlar: {len(get_all_products())}\n"
        f"🛒 Zakazlar: {len(orders)} ta\n"
        f"💰 Jami savdo: {revenue:,} so'm"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
    ))
    await call.answer()


# ─── Excel hisobot ───────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_excel_menu")
async def excel_menu(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Kunlik hisobot",  callback_data="excel_daily")],
        [InlineKeyboardButton(text="📆 Oylik hisobot",   callback_data="excel_monthly")],
        [InlineKeyboardButton(text="🏪 Seller bo'yicha", callback_data="excel_sellers")],
        [InlineKeyboardButton(text="🔙 Orqaga",          callback_data="admin_back")],
    ])
    await call.message.edit_text("📈 Qaysi hisobotni yuklab olmoqchisiz?", reply_markup=kb)
    await call.answer()


def _build_excel(orders: list, title: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title[:30]

    headers = ["#", "Sana", "Mahsulot", "Xaridor", "Telefon", "Manzil",
               "Yetkazish", "Narx", "Komissiya 10%", "Holat"]
    bold = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="2E86AB")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = bold
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center")

    dlv_map = {"pickup": "O'zi olib ketadi", "taxi": "Taksi pochta (shu bugunoq)", "btc": "BTC Pochta", "emu": "EMU Express", "uzum": "Uzum Pochta"}
    total = 0
    total_comm = 0
    for i, o in enumerate(orders, 1):
        comm = o.get("commission", int(o.get("total", 0) * 0.1))
        ws.append([
            o.get("id", i),
            o.get("created_at", "")[:10],
            o.get("product_name", "—"),
            o.get("buyer_name", o.get("buyer_id", "—")),
            o.get("phone", "—"),
            o.get("address", "—"),
            dlv_map.get(o.get("delivery", ""), o.get("delivery", "—")),
            o.get("total", 0),
            comm,
            o.get("status", "—"),
        ])
        total += o.get("total", 0)
        total_comm += comm

    ws.append([])
    ws.append(["", "", "", "", "", "", "JAMI:", total, total_comm, ""])
    for c in (7, 8, 9):
        ws.cell(row=ws.max_row, column=c).font = Font(bold=True)

    widths = [6, 12, 22, 20, 16, 30, 14, 14, 14, 14]
    for idx, w in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(row=1, column=idx).column_letter].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.callback_query(F.data == "excel_daily")
async def excel_daily(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    today = datetime.now().date().isoformat()
    orders = [o for o in get_orders() if o.get("created_at", "")[:10] == today]
    data = _build_excel(orders, "Kunlik")
    file = BufferedInputFile(data, filename=f"kunlik_{today}.xlsx")
    await call.message.answer_document(file, caption=f"📅 Kunlik hisobot — {today}\nZakazlar: {len(orders)} ta")
    await call.answer()


@router.callback_query(F.data == "excel_monthly")
async def excel_monthly(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    month = datetime.now().strftime("%Y-%m")
    orders = [o for o in get_orders() if o.get("created_at", "")[:7] == month]
    data = _build_excel(orders, "Oylik")
    file = BufferedInputFile(data, filename=f"oylik_{month}.xlsx")
    await call.message.answer_document(file, caption=f"📆 Oylik hisobot — {month}\nZakazlar: {len(orders)} ta")
    await call.answer()


# ─── Seller bo'yicha hisobot ─────────────────────────────────────────────────
@router.callback_query(F.data == "excel_sellers")
async def excel_sellers_list(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    sellers = get_sellers()
    if not sellers:
        await call.answer("Seller yo'q.", show_alert=True); return
    rows = []
    for uid, s in sellers.items():
        cnt = len(get_seller_orders(int(uid)))
        rows.append([InlineKeyboardButton(
            text=f"🏪 {s['shop_name']} ({cnt} zakaz)",
            callback_data=f"excel_seller_{uid}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_excel_menu")])
    await call.message.edit_text(
        "🏪 <b>Qaysi seller hisoboti?</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )
    await call.answer()


@router.callback_query(F.data.startswith("excel_seller_"))
async def excel_seller_report(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    uid = int(call.data.split("_")[-1])
    seller = get_seller(uid)
    orders = get_seller_orders(uid)
    if not orders:
        await call.answer("Bu sellerda zakaz yo'q.", show_alert=True); return
    shop = seller["shop_name"] if seller else str(uid)
    data = _build_excel(orders, f"{shop}")
    total = sum(o.get("total", 0) for o in orders)
    comm  = sum(o.get("commission", int(o.get("total", 0) * 0.1)) for o in orders)
    file = BufferedInputFile(data, filename=f"seller_{uid}.xlsx")
    await call.message.answer_document(
        file,
        caption=(
            f"🏪 <b>{shop}</b> — hisobot\n"
            f"🛒 Zakazlar: {len(orders)} ta\n"
            f"💰 Jami savdo: {total:,} so'm\n"
            f"💵 Sizning komissiyangiz (10%): {comm:,} so'm"
        ),
        parse_mode="HTML"
    )
    await call.answer()


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN: MAHSULOT QO'SHISH (owner + sub-admin)
# ═══════════════════════════════════════════════════════════════════════════
class AdminAddState(StatesGroup):
    user_id = State()
    city    = State()


@router.callback_query(F.data == "admin_addprod")
async def admin_addprod_pick(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    sellers = list(get_sellers().items())
    if not is_owner(call.from_user.id):
        mycity = _admin_city(call.from_user.id)
        sellers = [(u, s) for u, s in sellers if s.get("city") == mycity]
    if not sellers:
        await call.answer("Sizning shahringizda do'kon yo'q.", show_alert=True); return
    rows = [[InlineKeyboardButton(text=f"🏪 {s['shop_name']} ({s.get('city','—')})",
                                  callback_data=f"aap_{uid}")]
            for uid, s in sellers]
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    await _admin_nav(call, "➕ <b>Mahsulot qaysi do'konga qo'shilsin?</b>",
                     InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data.startswith("aap_"))
async def admin_addprod_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
    sid = int(call.data.split("_")[1])
    seller = get_seller(sid)
    if not seller:
        await call.answer("Do'kon topilmadi.", show_alert=True); return
    await state.set_state(AdminAddProduct.name)
    await state.update_data(seller_id=sid, shop_name=seller["shop_name"], city=seller.get("city", ""))
    await call.message.answer(f"🏪 {seller['shop_name']}\n📦 Mahsulot nomini kiriting:")
    await call.answer()


@router.message(AdminAddProduct.name)
async def admin_ap_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(AdminAddProduct.description)
    await message.answer("📝 Tavsif kiriting:")


@router.message(AdminAddProduct.description)
async def admin_ap_desc(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(AdminAddProduct.price)
    await message.answer("💰 Narxini kiriting (faqat raqam):")


@router.message(AdminAddProduct.price)
async def admin_ap_price(message: Message, state: FSMContext):
    if not (message.text or "").isdigit():
        await message.answer("❌ Faqat raqam kiriting:"); return
    await state.update_data(price=int(message.text))
    await state.set_state(AdminAddProduct.photo)
    await message.answer(
        "📸 Rasm(lar)ni yuboring — bittasini yoki bir nechtasini birga "
        "(albom) jo'nating.\nRasmsiz qo'shish uchun /skip yozing."
    )


def _admin_build_product(data: dict, photos: list) -> dict:
    return {
        "seller_id":   data["seller_id"],
        "shop_name":   data["shop_name"],
        "city":        data.get("city", ""),
        "name":        data["name"],
        "description": data["description"],
        "price":       data["price"],
        "photos":      photos,
    }


async def _admin_finish_product(message: Message, state: FSMContext, data: dict, photos: list):
    add_product(_admin_build_product(data, photos))
    _log(message.from_user, "Mahsulot qo'shildi",
         f"{data['name']} — do'kon: {data['shop_name']} ({data['price']:,} so'm)")
    await state.clear()
    await message.answer(
        f"✅ <b>{data['name']}</b> «{data['shop_name']}» do'koniga qo'shildi!"
        + (f"\n🖼 {len(photos)} ta rasm" if photos else ""),
        parse_mode="HTML", reply_markup=admin_menu_kb(message.from_user.id)
    )
    try:
        from app.bot.bot import bot
        await bot.send_message(
            data["seller_id"],
            f"➕ Admin do'koningizga yangi mahsulot qo'shdi:\n"
            f"📦 {data['name']} — {data['price']:,} so'm",
        )
    except Exception:
        pass


@router.message(AdminAddProduct.photo, F.media_group_id)
async def admin_ap_photo_album(message: Message, state: FSMContext):
    data = await state.get_data()
    key  = (message.from_user.id, message.media_group_id)

    async def done(photos):
        await _admin_finish_product(message, state, data, photos)

    collect(key, message.photo[-1].file_id, 1.5, done)


@router.message(AdminAddProduct.photo, F.photo)
async def admin_ap_photo_single(message: Message, state: FSMContext):
    data = await state.get_data()
    await _admin_finish_product(message, state, data, [message.photo[-1].file_id])


@router.message(AdminAddProduct.photo, F.text == "/skip")
async def admin_ap_photo_skip(message: Message, state: FSMContext):
    data = await state.get_data()
    await _admin_finish_product(message, state, data, [])


@router.message(AdminAddProduct.photo)
async def admin_ap_photo_wrong(message: Message, state: FSMContext):
    await message.answer("❌ Rasm yuboring yoki /skip yozing:")


# ═══════════════════════════════════════════════════════════════════════════
#  OWNER: SUB-ADMINLARNI BOSHQARISH
# ═══════════════════════════════════════════════════════════════════════════
@router.callback_query(F.data == "admin_admins")
async def admins_list(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    admins = get_admins()
    text = f"👮 <b>Sub-adminlar</b> — {len(admins)} ta\n\n"
    rows = []
    if not admins:
        text += "Hozircha sub-admin yo'q.\n"
    for uid, a in admins.items():
        text += f"• {a.get('name','—')} — 🏙 {a.get('city','—')} (ID: {uid})\n"
        rows.append([InlineKeyboardButton(text=f"🗑 {a.get('name', uid)} ni olib tashlash",
                                          callback_data=f"deladmin_{uid}")])
    rows.append([InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="addadmin")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    text += ("\n<i>Sub-admin faqat seller va mahsulot qo'sha oladi. "
             "Uning har bir amali jurnalga yoziladi.</i>")
    await _admin_nav(call, text, InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data == "addadmin")
async def add_admin_start(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    await state.set_state(AdminAddState.user_id)
    await call.message.answer(
        "➕ Yangi adminning <b>Telegram ID</b> raqamini yuboring.\n"
        "(Foydalanuvchi avval botga /start bosgan bo'lishi kerak. "
        "ID'ni u 👤 Profilim bo'limida ko'radi.)",
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminAddState.user_id)
async def add_admin_save(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        await state.clear(); return
    txt = (message.text or "").strip()
    if not txt.isdigit():
        await message.answer("❌ Faqat raqamli ID yuboring:"); return
    uid = int(txt)
    if uid == settings.OWNER_ID:
        await state.clear()
        await message.answer("Bu siz — asosiy egasiz."); return
    u = get_user(uid)
    name = u.get("full_name") if u else f"ID {uid}"
    await state.update_data(new_admin_id=uid, new_admin_name=name)
    await state.set_state(AdminAddState.city)
    rows, row = [], []
    for c in get_cities():
        row.append(InlineKeyboardButton(text=c, callback_data=f"admincity_{c}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row:
        rows.append(row)
    await message.answer(
        f"👤 {name}\n🏙 Bu admin qaysi shaharni boshqaradi? Tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows)
    )


@router.callback_query(AdminAddState.city, F.data.startswith("admincity_"))
async def add_admin_city(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    city = call.data.split("_", 1)[1]
    if city not in get_cities():
        await call.answer("Shahar topilmadi.", show_alert=True); return
    data = await state.get_data()
    uid = data["new_admin_id"]; name = data["new_admin_name"]
    await state.clear()
    add_admin(uid, {"name": name, "added_by": call.from_user.id, "city": city})
    _log(call.from_user, "Sub-admin qo'shildi", f"{name} (ID:{uid}, shahar: {city})")
    await call.message.answer(
        f"✅ {name} — <b>{city}</b> shahri admini qilib tayinlandi.\n"
        f"U /admin orqali faqat shu shahar seller/mahsulotlarini boshqaradi.",
        parse_mode="HTML", reply_markup=admin_menu_kb(call.from_user.id)
    )
    try:
        from app.bot.bot import bot
        await bot.send_message(uid, f"🛡 Sizga <b>{city}</b> shahri admini huquqi berildi!\n/admin buyrug'ini bosing.",
                               parse_mode="HTML")
    except Exception:
        pass
    await call.answer("Qo'shildi!")


@router.callback_query(F.data.startswith("deladmin_"))
async def del_admin_cb(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    uid = int(call.data.split("_")[1])
    a = get_admins().get(str(uid), {})
    if remove_admin(uid):
        _log(call.from_user, "Sub-admin olib tashlandi", f"{a.get('name','—')} (ID:{uid})")
        await call.answer("Olib tashlandi.")
    else:
        await call.answer("Topilmadi.")
    await admins_list(call)


# ═══════════════════════════════════════════════════════════════════════════
#  OWNER: AUDIT JURNALI + WORD
# ═══════════════════════════════════════════════════════════════════════════
def _fmt_dt(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return iso[:16]


@router.callback_query(F.data == "admin_log")
async def admin_log(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    log = get_audit()
    text = f"📜 <b>Amallar jurnali</b> — jami {len(log)} ta\n\n"
    if not log:
        text += "Hozircha yozuv yo'q."
    else:
        for e in log[-15:][::-1]:
            text += (
                f"🕒 {_fmt_dt(e.get('created_at',''))}\n"
                f"   👤 {e.get('admin_name','—')} [{e.get('role','')}]\n"
                f"   ▫️ {e.get('action','—')}: {e.get('target','')}\n\n"
            )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📄 Word (.docx) yuklab olish", callback_data="admin_log_word")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")],
    ])
    await _admin_nav(call, text, kb)
    await call.answer()


def _build_log_docx(log: list) -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    doc = Document()
    h = doc.add_heading("ProMan Market — Amallar jurnali", level=1)
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p = doc.add_paragraph(f"Yuklab olingan sana: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    table = doc.add_table(rows=1, cols=5)
    table.style = "Light Grid Accent 1"
    hdr = table.rows[0].cells
    for i, t in enumerate(["#", "Sana / vaqt", "Admin", "Amal", "Tafsilot"]):
        hdr[i].text = t
        for r in hdr[i].paragraphs[0].runs:
            r.font.bold = True

    for idx, e in enumerate(log, 1):
        c = table.add_row().cells
        c[0].text = str(idx)
        c[1].text = _fmt_dt(e.get("created_at", ""))
        c[2].text = f"{e.get('admin_name','—')} [{e.get('role','')}]"
        c[3].text = e.get("action", "—")
        c[4].text = e.get("target", "")

    doc.add_paragraph()
    doc.add_paragraph(f"Jami amallar: {len(log)} ta")
    import io as _io
    buf = _io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


@router.callback_query(F.data == "admin_log_word")
async def admin_log_word(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    log = get_audit()
    if not log:
        await call.answer("Jurnal bo'sh.", show_alert=True); return
    data = _build_log_docx(log)
    fname = f"jurnal_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"
    file = BufferedInputFile(data, filename=fname)
    await call.message.answer_document(file, caption=f"📜 Amallar jurnali — {len(log)} ta yozuv")
    await call.answer("Tayyor!")


# ═══════════════════════════════════════════════════════════════════════════
#  OWNER: SHAHARLAR (tuman/shahar) BOSHQARUVI
# ═══════════════════════════════════════════════════════════════════════════
class AdminCityState(StatesGroup):
    name = State()


def _cities_kb():
    rows = []
    for c in get_cities():
        rows.append([
            InlineKeyboardButton(text=f"🏙 {c}", callback_data="noop"),
            InlineKeyboardButton(text="🗑", callback_data=f"delcity_{c}"),
        ])
    rows.append([InlineKeyboardButton(text="➕ Shahar qo'shish", callback_data="addcity")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "admin_cities")
async def admin_cities(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    cities = get_cities()
    text = (f"🏙 <b>Shaharlar / Tumanlar</b> — {len(cities)} ta\n\n"
            "Sellerlar va xaridorlar shu ro'yxatdan tanlaydi.\n"
            "Har bir shaharga alohida admin tayinlashingiz mumkin.")
    await _admin_nav(call, text, _cities_kb())
    await call.answer()


@router.callback_query(F.data == "noop")
async def _noop(call: CallbackQuery):
    await call.answer()


@router.callback_query(F.data == "addcity")
async def add_city_start(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    await state.set_state(AdminCityState.name)
    await call.message.answer("🏙 Yangi shahar/tuman nomini yozing:")
    await call.answer()


@router.message(AdminCityState.name)
async def add_city_save(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        await state.clear(); return
    name = (message.text or "").strip()
    await state.clear()
    if not name:
        await message.answer("❌ Nomi bo'sh bo'lmasin."); return
    if add_city(name):
        _log(message.from_user, "Shahar qo'shildi", name)
        await message.answer(f"✅ «{name}» qo'shildi.", reply_markup=admin_menu_kb(message.from_user.id))
    else:
        await message.answer("Bu shahar allaqachon bor.", reply_markup=admin_menu_kb(message.from_user.id))


@router.callback_query(F.data.startswith("delcity_"))
async def del_city_cb(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    name = call.data.split("_", 1)[1]
    if remove_city(name):
        _log(call.from_user, "Shahar o'chirildi", name)
        await call.answer(f"{name} o'chirildi.")
    else:
        await call.answer("Topilmadi.")
    await admin_cities(call)


# ═══════════════════════════════════════════════════════════════════════════
#  OWNER: ZAXIRA (BACKUP) VA TIKLASH (RESTORE)
# ═══════════════════════════════════════════════════════════════════════════
from app.storage import DATA_DIR


class AdminRestore(StatesGroup):
    waiting_file = State()


def _make_backup_zip() -> tuple[bytes, int]:
    import glob
    files = glob.glob(os.path.join(DATA_DIR, "*.json"))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, arcname=os.path.basename(f))
    return buf.getvalue(), len(files)


async def _send_backup(message: Message):
    data, n = _make_backup_zip()
    if n == 0:
        await message.answer("Hozircha saqlangan ma'lumot yo'q.")
        return
    fname = f"backup_{datetime.now().strftime('%Y%m%d_%H%M')}.zip"
    await message.answer_document(
        BufferedInputFile(data, filename=fname),
        caption=(
            f"💾 <b>Zaxira nusxa</b> — {n} ta fayl\n"
            f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            "Bu faylni xavfsiz joyda saqlang. Yangi serverga ko'chsangiz, "
            "shu faylni botga /restore bilan yuborib hamma narsani tiklaysiz."
        ),
        parse_mode="HTML"
    )


@router.message(Command("backup"))
async def backup_cmd(message: Message):
    if not is_owner(message.from_user.id): return
    await _send_backup(message)


@router.callback_query(F.data == "admin_backup")
async def backup_btn(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    await _send_backup(call.message)
    await call.answer("Zaxira tayyor ✅")


@router.message(Command("restore"))
async def restore_cmd(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id): return
    await state.set_state(AdminRestore.waiting_file)
    await message.answer(
        "♻️ <b>Ma'lumotlarni tiklash</b>\n\n"
        "Avval olingan <b>backup .zip</b> faylini shu yerga (hujjat sifatida) yuboring.\n"
        "⚠️ Diqqat: hozirgi ma'lumotlar yangisi bilan almashtiriladi.\n\n"
        "Bekor qilish: /cancel",
        parse_mode="HTML"
    )


@router.message(AdminRestore.waiting_file, F.text == "/cancel")
async def restore_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=admin_menu_kb(message.from_user.id))


@router.message(AdminRestore.waiting_file, F.document)
async def restore_file(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id):
        await state.clear(); return
    doc = message.document
    if not (doc.file_name or "").endswith(".zip"):
        await message.answer("❌ Iltimos, backup .zip faylini yuboring.")
        return
    await state.clear()
    try:
        from app.bot.bot import bot
        bio = io.BytesIO()
        await bot.download(doc, destination=bio)
        bio.seek(0)
        os.makedirs(DATA_DIR, exist_ok=True)
        count = 0
        with zipfile.ZipFile(bio) as z:
            for n in z.namelist():
                if not n.endswith(".json"):
                    continue
                base = os.path.basename(n)        # xavfsizlik: papka yo'llarini tashlaymiz
                if not base:
                    continue
                with z.open(n) as src, open(os.path.join(DATA_DIR, base), "wb") as dst:
                    dst.write(src.read())
                count += 1
        if count == 0:
            await message.answer("❌ Zip ichida .json fayl topilmadi. To'g'ri backup faylini yuboring.")
            return
        _log(message.from_user, "Ma'lumotlar tiklandi", f"{count} ta fayl")
        await message.answer(
            f"✅ <b>{count} ta fayl tiklandi!</b>\nMa'lumotlar muvaffaqiyatli yangilandi.",
            parse_mode="HTML", reply_markup=admin_menu_kb(message.from_user.id)
        )
    except Exception as e:
        await message.answer(f"❌ Faylni o'qishda xato: {e}")


@router.message(AdminRestore.waiting_file)
async def restore_wrong(message: Message):
    await message.answer("❌ Backup .zip faylini hujjat sifatida yuboring (yoki /cancel).")
