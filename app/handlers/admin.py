import io
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.storage import (
    get_applications, update_application_status, add_seller, get_sellers,
    get_all_products, admin_delete_product, update_product, get_product_by_id,
    update_seller, delete_seller, delete_user, get_orders, get_seller_reviews
)

router = Router()


def get_admin_ids():
    from app.app.config.settings import settings
    return [settings.OWNER_ID]


def is_admin(uid: int) -> bool:
    return uid in get_admin_ids()


# ─── States ──────────────────────────────────────────────────────────────────
class AdminEditShop(StatesGroup):
    waiting_value = State()

class AdminEditProduct(StatesGroup):
    waiting_field = State()
    waiting_value = State()


# ─── Menus ───────────────────────────────────────────────────────────────────
def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Arizalar",        callback_data="admin_applications")],
        [InlineKeyboardButton(text="🏪 Sellerlar",        callback_data="admin_sellers")],
        [InlineKeyboardButton(text="📦 Mahsulotlar",      callback_data="admin_products")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users")],
        [InlineKeyboardButton(text="📊 Statistika",       callback_data="admin_stats")],
        [InlineKeyboardButton(text="📈 Excel hisobot",    callback_data="admin_excel_menu")],
    ])


# ─── /admin ──────────────────────────────────────────────────────────────────
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    apps = get_applications()
    pending = [a for a in apps.values() if a.get("status") == "pending"]
    await message.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"⏳ Kutilayotgan arizalar: <b>{len(pending)}</b>\n"
        f"🏪 Jami sellerlar: <b>{len(get_sellers())}</b>",
        reply_markup=admin_menu_kb(), parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    apps = get_applications()
    pending = [a for a in apps.values() if a.get("status") == "pending"]
    await call.message.edit_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"⏳ Kutilayotgan arizalar: <b>{len(pending)}</b>\n"
        f"🏪 Jami sellerlar: <b>{len(get_sellers())}</b>",
        reply_markup=admin_menu_kb(), parse_mode="HTML"
    )
    await call.answer()


# ─── Arizalar ────────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_applications")
async def show_applications(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    pending = {uid: a for uid, a in get_applications().items() if a.get("status") == "pending"}
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
        "card_number": app["card_number"],
    })
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
    await call.message.edit_text(f"❌ {app['full_name']} arizasi rad etildi.")
    try:
        from app.bot.bot import bot
        await bot.send_message(uid, "❌ Seller arizangiz rad etildi.")
    except Exception: pass
    await call.answer("❌ Rad etildi!")


# ─── Sellerlar (ko'rish + tahrirlash + o'chirish) ────────────────────────────
@router.callback_query(F.data == "admin_sellers")
async def show_sellers(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    sellers = get_sellers()
    if not sellers:
        await call.message.edit_text("Hozircha seller yo'q.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
        ))
        return
    rows = []
    for uid, s in sellers.items():
        rows.append([InlineKeyboardButton(
            text=f"🏪 {s['shop_name']} — {s['full_name']}",
            callback_data=f"aseller_{uid}"
        )])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    await call.message.edit_text("🏪 <b>Sellerlar:</b>", parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    await call.answer()


@router.callback_query(F.data.startswith("aseller_"))
async def seller_detail(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    uid = call.data.split("_")[1]
    s = get_sellers().get(uid)
    if not s:
        await call.answer("Seller topilmadi."); return
    from app.storage import get_seller_rating
    rating, cnt = get_seller_rating(int(uid))
    stars = "⭐" * int(rating) if rating else "—"
    text = (
        f"🏪 <b>{s['shop_name']}</b>\n\n"
        f"👤 {s['full_name']}\n"
        f"📱 {s['phone']}\n"
        f"💳 **** {s.get('card_number','')[-4:]}\n"
        f"⭐ Reyting: {stars} {rating} ({cnt} ta baho)"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Do'kon nomini o'zgartirish", callback_data=f"edit_shop_name_{uid}")],
        [InlineKeyboardButton(text="✏️ Karta raqamini o'zgartirish", callback_data=f"edit_shop_card_{uid}")],
        [InlineKeyboardButton(text="✏️ Telefon raqamini o'zgartirish", callback_data=f"edit_shop_phone_{uid}")],
        [InlineKeyboardButton(text="🗑 Sellerni o'chirish", callback_data=f"del_seller_{uid}")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_sellers")],
    ])
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("edit_shop_"))
async def edit_shop_start(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id): return
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
    if not is_admin(message.from_user.id):
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
    if not is_admin(call.from_user.id): return
    uid = int(call.data.split("_")[2])
    sellers = get_sellers()
    name = sellers.get(str(uid), {}).get("shop_name", "—")
    delete_seller(uid)
    await call.message.edit_text(f"🗑 {name} selleri o'chirildi.")
    await call.answer("O'chirildi")


# ─── Mahsulotlar (admin) ─────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_products")
async def admin_products(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
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
    if not is_admin(call.from_user.id): return
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
    if not is_admin(call.from_user.id): return
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
    if not is_admin(message.from_user.id):
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
    if not is_admin(call.from_user.id): return
    pid = int(call.data.split("_")[1])
    admin_delete_product(pid)
    await call.message.edit_text("🗑 Mahsulot o'chirildi.")
    await call.answer("O'chirildi")


# ─── Foydalanuvchilar ────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_users")
async def admin_users(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
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
    if not is_admin(call.from_user.id): return
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
    if not is_admin(call.from_user.id): return
    uid = int(call.data.split("_")[2])
    delete_user(uid)
    delete_seller(uid)
    await call.message.edit_text(f"🗑 Foydalanuvchi (ID:{uid}) o'chirildi.")
    await call.answer("O'chirildi")


# ─── Statistika ──────────────────────────────────────────────────────────────
@router.callback_query(F.data == "admin_stats")
async def show_stats(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
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
    if not is_admin(call.from_user.id): return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Kunlik hisobot",  callback_data="excel_daily")],
        [InlineKeyboardButton(text="📆 Oylik hisobot",   callback_data="excel_monthly")],
        [InlineKeyboardButton(text="🔙 Orqaga",          callback_data="admin_back")],
    ])
    await call.message.edit_text("📈 Qaysi hisobotni yuklab olmoqchisiz?", reply_markup=kb)
    await call.answer()


def _build_excel(orders: list, title: str) -> bytes:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = title

    headers = ["#", "Sana", "Xaridor ID", "Seller ID", "Mahsulot", "Narx", "Holat"]
    bold = Font(bold=True, color="FFFFFF")
    fill = PatternFill("solid", fgColor="2E86AB")
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = bold
        cell.fill = fill
        cell.alignment = Alignment(horizontal="center")

    total = 0
    for i, o in enumerate(orders, 1):
        ws.append([
            i,
            o.get("created_at", "")[:10],
            o.get("buyer_id"),
            o.get("seller_id"),
            o.get("product_name", "—"),
            o.get("total", 0),
            o.get("status", "—"),
        ])
        total += o.get("total", 0)

    ws.append([])
    ws.append(["", "", "", "", "JAMI:", total, ""])
    ws.cell(row=ws.max_row, column=5).font = Font(bold=True)
    ws.cell(row=ws.max_row, column=6).font = Font(bold=True)

    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 18

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@router.callback_query(F.data == "excel_daily")
async def excel_daily(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    today = datetime.now().date().isoformat()
    orders = [o for o in get_orders() if o.get("created_at", "")[:10] == today]
    data = _build_excel(orders, "Kunlik")
    file = BufferedInputFile(data, filename=f"kunlik_{today}.xlsx")
    await call.message.answer_document(file, caption=f"📅 Kunlik hisobot — {today}\nZakazlar: {len(orders)} ta")
    await call.answer()


@router.callback_query(F.data == "excel_monthly")
async def excel_monthly(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    month = datetime.now().strftime("%Y-%m")
    orders = [o for o in get_orders() if o.get("created_at", "")[:7] == month]
    data = _build_excel(orders, "Oylik")
    file = BufferedInputFile(data, filename=f"oylik_{month}.xlsx")
    await call.message.answer_document(file, caption=f"📆 Oylik hisobot — {month}\nZakazlar: {len(orders)} ta")
    await call.answer()
