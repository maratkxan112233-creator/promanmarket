from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.storage import get_applications, update_application_status, add_seller, get_sellers

router = Router()

ADMIN_IDS = []  # settings dan olinadi


def get_admin_ids():
    from app.app.config.settings import settings
    return [settings.OWNER_ID]


def admin_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Arizalar", callback_data="admin_applications")],
        [InlineKeyboardButton(text="🏪 Sellerlar", callback_data="admin_sellers")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
    ])


@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id not in get_admin_ids():
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return
    apps = get_applications()
    pending = [a for a in apps.values() if a.get("status") == "pending"]
    await message.answer(
        f"👑 <b>Admin Panel</b>\n\n"
        f"⏳ Kutilayotgan arizalar: <b>{len(pending)}</b>\n"
        f"🏪 Jami sellerlar: <b>{len(get_sellers())}</b>",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin_applications")
async def show_applications(call: CallbackQuery):
    if call.from_user.id not in get_admin_ids():
        return
    apps = get_applications()
    pending = {uid: a for uid, a in apps.items() if a.get("status") == "pending"}

    if not pending:
        await call.message.edit_text("✅ Kutilayotgan ariza yo'q.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
        ))
        return

    for uid, app in pending.items():
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{uid}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{uid}"),
            ]
        ])
        text = (
            f"📋 <b>Ariza #{uid}</b>\n\n"
            f"👤 Ism: {app.get('full_name')}\n"
            f"📱 Telefon: {app.get('phone')}\n"
            f"🏪 Do'kon: {app.get('shop_name')}\n"
            f"💳 Karta: **** {app.get('card_number', '')[-4:]}"
        )
        await call.message.answer(text, reply_markup=kb, parse_mode="HTML")

        if app.get("passport_photo"):
            await call.message.answer_photo(app["passport_photo"], caption="📄 Pasport")
        if app.get("selfie_photo"):
            await call.message.answer_photo(app["selfie_photo"], caption="🤳 Selfi")

    await call.answer()


@router.callback_query(F.data.startswith("approve_"))
async def approve_seller(call: CallbackQuery):
    if call.from_user.id not in get_admin_ids():
        return
    uid = int(call.data.split("_")[1])
    apps = get_applications()
    app = apps.get(str(uid))
    if not app:
        await call.answer("Ariza topilmadi.")
        return

    update_application_status(uid, "approved")
    add_seller(uid, {
        "user_id": uid,
        "full_name": app["full_name"],
        "shop_name": app["shop_name"],
        "phone": app["phone"],
        "card_number": app["card_number"],
    })

    await call.message.edit_text(f"✅ {app['full_name']} seller sifatida tasdiqlandi!")

    try:
        from app.bot.bot import bot
        await bot.send_message(
            uid,
            "🎉 Tabriklaymiz! Seller arizangiz tasdiqlandi!\n"
            "Endi /seller buyrug'i orqali mahsulot qo'shishingiz mumkin."
        )
    except Exception:
        pass

    await call.answer("✅ Tasdiqlandi!")


@router.callback_query(F.data.startswith("reject_"))
async def reject_seller(call: CallbackQuery):
    if call.from_user.id not in get_admin_ids():
        return
    uid = int(call.data.split("_")[1])
    apps = get_applications()
    app = apps.get(str(uid))
    if not app:
        await call.answer("Ariza topilmadi.")
        return

    update_application_status(uid, "rejected")
    await call.message.edit_text(f"❌ {app['full_name']} arizasi rad etildi.")

    try:
        from app.bot.bot import bot
        await bot.send_message(uid, "❌ Afsuski, seller arizangiz rad etildi.")
    except Exception:
        pass

    await call.answer("❌ Rad etildi!")


@router.callback_query(F.data == "admin_sellers")
async def show_sellers(call: CallbackQuery):
    if call.from_user.id not in get_admin_ids():
        return
    sellers = get_sellers()
    if not sellers:
        await call.message.edit_text("Hozircha seller yo'q.", reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
        ))
        return

    text = "🏪 <b>Sellerlar ro'yxati:</b>\n\n"
    for uid, s in sellers.items():
        text += f"• {s['shop_name']} — {s['full_name']} (ID: {uid})\n"

    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
    ))
    await call.answer()


@router.callback_query(F.data == "admin_stats")
async def show_stats(call: CallbackQuery):
    if call.from_user.id not in get_admin_ids():
        return
    from app.storage import get_all_products
    apps = get_applications()
    text = (
        f"📊 <b>Statistika</b>\n\n"
        f"📋 Jami arizalar: {len(apps)}\n"
        f"⏳ Kutilmoqda: {len([a for a in apps.values() if a.get('status') == 'pending'])}\n"
        f"✅ Tasdiqlangan: {len([a for a in apps.values() if a.get('status') == 'approved'])}\n"
        f"❌ Rad etilgan: {len([a for a in apps.values() if a.get('status') == 'rejected'])}\n"
        f"🏪 Sellerlar: {len(get_sellers())}\n"
        f"📦 Mahsulotlar: {len(get_all_products())}\n"
    )
    await call.message.edit_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")]]
    ))
    await call.answer()


@router.callback_query(F.data == "admin_back")
async def admin_back(call: CallbackQuery):
    if call.from_user.id not in get_admin_ids():
        return
    apps = get_applications()
    pending = [a for a in apps.values() if a.get("status") == "pending"]
    await call.message.edit_text(
        f"👑 <b>Admin Panel</b>\n\n"
        f"⏳ Kutilayotgan arizalar: <b>{len(pending)}</b>\n"
        f"🏪 Jami sellerlar: <b>{len(get_sellers())}</b>",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML"
    )
    await call.answer()
