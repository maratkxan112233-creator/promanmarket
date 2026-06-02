from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from data.db import get_all_categories, get_products_by_category, get_product, format_price, get_category
from data.cart import add_to_cart

router = Router()

_qty: dict[int, dict[str, int]] = {}


def _get_qty(uid: int, pid: str) -> int:
    return _qty.get(uid, {}).get(pid, 1)


def _set_qty(uid: int, pid: str, q: int):
    _qty.setdefault(uid, {})[pid] = max(1, min(q, 99))


# ─── KLAVIATURALAR ────────────────────────────────────────────────

def categories_kb() -> InlineKeyboardMarkup:
    cats = get_all_categories()
    if not cats:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home")]
        ])
    buttons = [
        [InlineKeyboardButton(
            text=f"{c['emoji']} {c['name']}",
            callback_data=f"cat_{cid}"
        )]
        for cid, c in cats.items()
    ]
    buttons.append([InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def products_kb(cid: str) -> InlineKeyboardMarkup:
    products = get_products_by_category(cid)
    buttons = []
    for p in products:
        status = "" if p["in_stock"] else " ❌"
        buttons.append([InlineKeyboardButton(
            text=f"{p['name']} — {format_price(p['price'])}{status}",
            callback_data=f"prod_{p['id']}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅ Kategoriyalar", callback_data="catalog")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def product_detail_kb(pid: str, cid: str, qty: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➖", callback_data=f"qm_{pid}"),
            InlineKeyboardButton(text=f"  {qty} dona  ", callback_data=f"qs_{pid}"),
            InlineKeyboardButton(text="➕", callback_data=f"qp_{pid}"),
        ],
        [InlineKeyboardButton(
            text=f"🛒 Savatga qo'shish ({qty} dona)",
            callback_data=f"addcart_{pid}_{qty}"
        )],
        [InlineKeyboardButton(text="⬅ Orqaga", callback_data=f"cat_{cid}")],
    ])


# ─── YORDAMCHI: xabarni xavfsiz o'chirib yangi yuborish ──────────

async def _safe_send_text(callback: CallbackQuery, text: str, reply_markup):
    """Rasm yoki oddiy xabar bo'lishidan qat'i nazar xavfsiz ishlaydi."""
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


# ─── HANDLERLAR ───────────────────────────────────────────────────

@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery):
    cats = get_all_categories()
    if not cats:
        await _safe_send_text(
            callback,
            "📂 Hozircha kategoriyalar yo'q.\nAdmin tez orada qo'shadi! 🔧",
            InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🏠 Bosh menyu", callback_data="home")]
            ])
        )
        return
    await _safe_send_text(
        callback,
        "📂 <b>Kategoriyani tanlang:</b>",
        categories_kb()
    )


@router.callback_query(F.data.startswith("cat_"))
async def show_category(callback: CallbackQuery):
    cid = callback.data[4:]
    cat = get_category(cid)
    if not cat:
        await callback.answer("Kategoriya topilmadi", show_alert=True)
        return
    products = get_products_by_category(cid)
    if not products:
        await callback.answer("Bu kategoriyada mahsulot yo'q", show_alert=True)
        return
    await _safe_send_text(
        callback,
        f"{cat['emoji']} <b>{cat['name']}</b>\n\nMahsulotni tanlang:",
        products_kb(cid)
    )


@router.callback_query(F.data.startswith("prod_"))
async def show_product(callback: CallbackQuery):
    pid = callback.data[5:]
    p = get_product(pid)
    if not p:
        await callback.answer("Mahsulot topilmadi", show_alert=True)
        return

    qty = _get_qty(callback.from_user.id, pid)
    stock_text = "✅ Mavjud" if p["in_stock"] else "❌ Tugagan"
    text = (
        f"<b>{p['name']}</b>\n\n"
        f"📝 {p['description']}\n"
        f"💰 Narx: <b>{format_price(p['price'])}</b>\n"
        f"📦 Holat: {stock_text}"
    )

    kb = product_detail_kb(pid, p["category_id"], qty) if p["in_stock"] else \
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Orqaga", callback_data=f"cat_{p['category_id']}")]
        ])

    if p.get("photo_id"):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_photo(
            photo=p["photo_id"], caption=text,
            reply_markup=kb, parse_mode="HTML"
        )
    else:
        await _safe_send_text(callback, text, kb)

    await callback.answer()


@router.callback_query(F.data.startswith("qm_"))
async def qty_minus(callback: CallbackQuery):
    pid = callback.data[3:]
    p = get_product(pid)
    if not p:
        return
    cur = _get_qty(callback.from_user.id, pid)
    if cur <= 1:
        await callback.answer("Minimum 1 dona!")
        return
    _set_qty(callback.from_user.id, pid, cur - 1)
    new_qty = _get_qty(callback.from_user.id, pid)
    await callback.message.edit_reply_markup(
        reply_markup=product_detail_kb(pid, p["category_id"], new_qty)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qp_"))
async def qty_plus(callback: CallbackQuery):
    pid = callback.data[3:]
    p = get_product(pid)
    if not p:
        return
    cur = _get_qty(callback.from_user.id, pid)
    if cur >= 99:
        await callback.answer("Maksimum 99 dona!")
        return
    _set_qty(callback.from_user.id, pid, cur + 1)
    new_qty = _get_qty(callback.from_user.id, pid)
    await callback.message.edit_reply_markup(
        reply_markup=product_detail_kb(pid, p["category_id"], new_qty)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qs_"))
async def qty_show(callback: CallbackQuery):
    pid = callback.data[3:]
    qty = _get_qty(callback.from_user.id, pid)
    await callback.answer(f"Tanlangan: {qty} dona")


@router.callback_query(F.data.startswith("addcart_"))
async def add_to_cart_handler(callback: CallbackQuery):
    parts = callback.data.split("_")
    pid = parts[1]
    qty = int(parts[2]) if len(parts) > 2 else 1
    p = get_product(pid)
    if not p or not p["in_stock"]:
        await callback.answer("❌ Mahsulot mavjud emas", show_alert=True)
        return
    add_to_cart(callback.from_user.id, pid, qty)
    _set_qty(callback.from_user.id, pid, 1)
    await callback.answer(f"✅ {p['name']} — {qty} dona savatga qo'shildi!", show_alert=True)
