"""ℹ️ Ma'lumot bo'limi — ishonch va konversiya sahifalari.

Asosiy menyudagi bitta «ℹ️ Ma'lumot» tugmasi ichida:
  ⭐ Nega aynan biz?   — ustunliklar (24 soat, 10%, kafolat, sovg'a...)
  🏢 Biz haqimizda     — kompaniya, telefon, ish vaqti, manzil, rekvizitlar
  ⭐ Xaridorlar fikrlari — admin qo'shgan rasm/video guvohliklar
  ❓ Savol-javob        — FAQ (admin paneldan tahrirlanadi)

Barcha matnlar runtime sozlamalardan olinadi (app/services/runtime_settings).
Bu router dispatcher'da common'dan OLDIN ulanadi.
"""

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)

from app.storage import get_testimonials
from app.services import runtime_settings as rs
from app.ui import divider

router = Router()


def _info_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Nega aynan biz?", callback_data="info_why")],
        [InlineKeyboardButton(text="🏢 Biz haqimizda", callback_data="info_about")],
        [InlineKeyboardButton(text="⭐ Xaridorlar fikrlari", callback_data="info_tst_0")],
        [InlineKeyboardButton(text="❓ Savol-javob", callback_data="info_faq")],
    ])


def _back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Orqaga", callback_data="info_menu")],
    ])


@router.message(F.text == "ℹ️ Ma'lumot")
async def info_menu(message: Message):
    await message.answer(
        f"ℹ️ <b>Ma'lumot</b>\n{divider()}\n"
        "Kerakli bo'limni tanlang:",
        parse_mode="HTML", reply_markup=_info_menu_kb(),
    )


@router.callback_query(F.data == "info_menu")
async def info_menu_cb(call: CallbackQuery):
    await call.answer()
    try:
        await call.message.edit_text(
            f"ℹ️ <b>Ma'lumot</b>\n{divider()}\n"
            "Kerakli bo'limni tanlang:",
            parse_mode="HTML", reply_markup=_info_menu_kb(),
        )
    except Exception:
        await call.message.answer(
            f"ℹ️ <b>Ma'lumot</b>\n{divider()}\n"
            "Kerakli bo'limni tanlang:",
            parse_mode="HTML", reply_markup=_info_menu_kb(),
        )


# ─── ⭐ Nega aynan biz? ───────────────────────────────────────────────────────
@router.callback_query(F.data == "info_why")
async def info_why(call: CallbackQuery):
    await call.answer()
    try:
        await call.message.edit_text(rs.why_us_text(), parse_mode="HTML",
                                     reply_markup=_back_kb())
    except Exception:
        await call.message.answer(rs.why_us_text(), parse_mode="HTML",
                                  reply_markup=_back_kb())


# ─── 🏢 Biz haqimizda ────────────────────────────────────────────────────────
@router.callback_query(F.data == "info_about")
async def info_about(call: CallbackQuery):
    await call.answer()
    rows = []
    map_link = rs.about().get("map_link", "").strip()
    if map_link.startswith("http"):
        rows.append([InlineKeyboardButton(text="🗺 Xaritada ko'rish", url=map_link)])
    rows.append([InlineKeyboardButton(text="← Orqaga", callback_data="info_menu")])
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    try:
        await call.message.edit_text(rs.about_text(), parse_mode="HTML",
                                     reply_markup=kb)
    except Exception:
        await call.message.answer(rs.about_text(), parse_mode="HTML",
                                  reply_markup=kb)


# ─── ⭐ Xaridorlar fikrlari ───────────────────────────────────────────────────
def _tst_nav_kb(idx: int, total: int) -> InlineKeyboardMarkup:
    rows = []
    if total > 1:
        rows.append([
            InlineKeyboardButton(text="◀️", callback_data=f"info_tst_{(idx - 1) % total}"),
            InlineKeyboardButton(text=f"{idx + 1}/{total}", callback_data="noop"),
            InlineKeyboardButton(text="▶️", callback_data=f"info_tst_{(idx + 1) % total}"),
        ])
    rows.append([InlineKeyboardButton(text="← Orqaga", callback_data="info_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data.startswith("info_tst_"))
async def info_testimonials(call: CallbackQuery):
    await call.answer()
    items = get_testimonials()
    if not items:
        try:
            await call.message.edit_text(
                "⭐ <b>Xaridorlar fikrlari</b>\n────────\n"
                "Hozircha fikrlar qo'shilmagan.",
                parse_mode="HTML", reply_markup=_back_kb())
        except Exception:
            pass
        return
    idx = int(call.data.split("_")[2]) % len(items)
    t = items[idx]
    caption = f"⭐ <b>Xaridorlar fikrlari</b>\n\n{t.get('caption', '')}".strip()
    kb = _tst_nav_kb(idx, len(items))
    # Media xabarini tahrirlab bo'lmaydi (matn xabaridan keladi) — eski
    # xabarni o'chirib, yangisini yuboramiz.
    try:
        await call.message.delete()
    except Exception:
        pass
    try:
        if t.get("media_type") == "video":
            await call.message.answer_video(t["file_id"], caption=caption,
                                            parse_mode="HTML", reply_markup=kb)
        else:
            await call.message.answer_photo(t["file_id"], caption=caption,
                                            parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(caption or "⭐ Xaridorlar fikrlari",
                                  parse_mode="HTML", reply_markup=kb)


# ─── ❓ Savol-javob (FAQ) ─────────────────────────────────────────────────────
def _faq_kb() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=item["q"], callback_data=f"info_faq_{i}")]
        for i, item in enumerate(rs.faq_list())
    ]
    rows.append([InlineKeyboardButton(text="← Orqaga", callback_data="info_menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "info_faq")
async def info_faq(call: CallbackQuery):
    await call.answer()
    text = (f"❓ <b>Savol-javob</b>\n{divider()}\n"
            "Savolni tanlang:")
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=_faq_kb())
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=_faq_kb())


@router.callback_query(F.data.startswith("info_faq_"))
async def info_faq_answer(call: CallbackQuery):
    await call.answer()
    faq = rs.faq_list()
    idx = int(call.data.split("_")[2])
    if idx >= len(faq):
        return
    item = faq[idx]
    text = (f"❓ <b>{item['q']}</b>\n{divider()}\n"
            f"{item['a']}")
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Savollarga qaytish", callback_data="info_faq")],
        [InlineKeyboardButton(text="🏠 Ma'lumot menyusi", callback_data="info_menu")],
    ])
    try:
        await call.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    except Exception:
        await call.message.answer(text, parse_mode="HTML", reply_markup=kb)
