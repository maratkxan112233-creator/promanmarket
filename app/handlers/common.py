from aiogram import Router, F
from aiogram.types import Message

from app.storage import is_seller, get_seller, get_all_products, get_seller_products
from app.keyboards.seller import main_menu

router = Router()


@router.message(F.text == "📞 Aloqa")
async def contact_handler(message: Message):
    await message.answer(
        "📞 <b>Aloqa</b>\n\n"
        "Savol va takliflar uchun:\n"
        "👤 Admin: @promanmarketbot\n\n"
        "Ish vaqti: 09:00 — 18:00",
        parse_mode="HTML"
    )


@router.message(F.text == "👤 Profilim")
async def profile_handler(message: Message):
    user = message.from_user
    seller = get_seller(user.id)

    if seller:
        role = "🏪 Seller"
        products = get_seller_products(user.id)
        extra = f"\n🏪 Do'kon: {seller['shop_name']}\n📦 Mahsulotlar: {len(products)} ta\n\n/seller — seller panel"
    else:
        role = "🛍 Xaridor"
        extra = "\n\nSeller bo'lish uchun: 🏪 Seller bo'lish"

    await message.answer(
        f"👤 <b>Profilingiz</b>\n\n"
        f"Ism: {user.full_name}\n"
        f"Username: @{user.username or 'yo\'q'}\n"
        f"ID: {user.id}\n"
        f"Rol: {role}"
        f"{extra}",
        parse_mode="HTML",
        reply_markup=main_menu
    )


@router.message(F.text == "🛍 Bozor")
async def market_handler(message: Message):
    products = get_all_products()
    if not products:
        await message.answer("🛒 Hozircha mahsulot yo'q.")
        return

    await message.answer(f"🛍 <b>Bozor</b> — {len(products)} ta mahsulot\n", parse_mode="HTML")

    for p in products[:10]:
        text = (
            f"📦 <b>{p['name']}</b>\n"
            f"🏪 {p.get('shop_name', 'Do\'kon')}\n"
            f"📝 {p.get('description', '')}\n"
            f"💰 {p['price']:,} so'm"
        )
        if p.get("photo"):
            await message.answer_photo(p["photo"], caption=text, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")
