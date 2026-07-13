"""⚙️ Sozlamalar — admin panelning ish vaqti sozlamalari bo'limi.

Owner shu yerdan kodga tegmasdan boshqaradi:
  • yetkazish narxi, bepul yetkazish chegarasi, oldindan to'lov foizi
  • aloqa telefoni, sovg'a matni, aksiya (banner) matni
  • popup xabar (har foydalanuvchiga bir marta ko'rsatiladi)
  • «Biz haqimizda» maydonlari (kompaniya, manzil, xarita, rekvizitlar...)
  • ⭐ Xaridorlar fikrlari (rasm/video qo'shish-o'chirish)
  • ❓ FAQ savol-javoblari

Qiymatlar data/runtime.json da (app/storage.get_runtime_config).
"""

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.storage import (
    get_runtime_config, set_runtime_field,
    get_testimonials, add_testimonial, delete_testimonial,
)
from app.handlers.admin import is_owner, _ack, _admin_nav
from app.ui import money

router = Router()


class AdminSetValue(StatesGroup):
    waiting_value = State()


class AdminPopup(StatesGroup):
    waiting_text = State()


class AdminTestimonial(StatesGroup):
    waiting_media = State()


class AdminFaq(StatesGroup):
    waiting_q = State()
    waiting_a = State()


# Maydon kaliti -> (nom, tur). Tur: "int" (musbat son), "percent" (1-99), "text".
FIELDS = {
    "delivery_fee":             ("🚛 Yetkazish narxi", "int"),
    "free_delivery_threshold":  ("🆓 Bepul yetkazish chegarasi", "int"),
    "prepay_percent":           ("💳 Oldindan to'lov foizi", "percent"),
    "contact_phone":            ("📞 Aloqa telefoni", "text"),
    "gift_text":                ("🎁 Sovg'a matni", "text"),
    "banner_extra":             ("🔥 Aksiya matni (bannerga qo'shiladi)", "text"),
    "about.company":            ("🏢 Kompaniya haqida", "text"),
    "about.phone":              ("📞 Telefon (Biz haqimizda)", "text"),
    "about.telegram":           ("✈️ Telegram", "text"),
    "about.work_hours":         ("🕘 Ish vaqti", "text"),
    "about.address":            ("📍 Manzil", "text"),
    "about.map_link":           ("🗺 Xarita havolasi", "text"),
    "about.requisites":         ("🧾 Rekvizitlar", "text"),
}


def _get_field(cfg: dict, key: str):
    if "." in key:
        parent, child = key.split(".", 1)
        return (cfg.get(parent) or {}).get(child, "")
    return cfg.get(key, "")


def _fmt_value(key: str, value) -> str:
    if key in ("delivery_fee", "free_delivery_threshold"):
        return money(value)
    if key == "prepay_percent":
        return f"{value}%"
    s = str(value or "").strip()
    if not s:
        return "—"
    return s if len(s) <= 30 else s[:30] + "…"


def _settings_menu():
    cfg = get_runtime_config()
    pop = cfg.get("popup", {})
    pop_status = "🟢 yoqilgan" if (pop.get("enabled") and pop.get("text")) else "⚪ o'chiq"
    text = (
        "⚙️ <b>Sozlamalar</b>\n────────\n"
        "Qiymatni o'zgartirish uchun ustiga bosing.\n"
        "Bu qiymatlar butun bot bo'ylab darhol qo'llanadi."
    )
    rows = []
    for key in ("delivery_fee", "free_delivery_threshold", "prepay_percent",
                "contact_phone", "gift_text", "banner_extra"):
        label, _ = FIELDS[key]
        rows.append([InlineKeyboardButton(
            text=f"{label}: {_fmt_value(key, _get_field(cfg, key))}",
            callback_data=f"aset_{key}")])
    rows.append([InlineKeyboardButton(text=f"📢 Popup xabar ({pop_status})",
                                      callback_data="asetpopup")])
    rows.append([InlineKeyboardButton(text="🏢 Biz haqimizda maydonlari",
                                      callback_data="asetabout")])
    rows.append([InlineKeyboardButton(text="⭐ Xaridorlar fikrlari",
                                      callback_data="asettst")])
    rows.append([InlineKeyboardButton(text="❓ FAQ savol-javoblar",
                                      callback_data="asetfaq")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


def _cancel_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="aset_cancel")],
    ])


async def _show_settings(call: CallbackQuery):
    text, kb = _settings_menu()
    await _admin_nav(call, text, kb)


@router.callback_query(F.data == "admin_settings")
async def admin_settings(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    await state.clear()
    await _show_settings(call)


@router.callback_query(F.data == "aset_cancel")
async def aset_cancel(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    await state.clear()
    await _show_settings(call)


# ─── Oddiy qiymatlar (son / foiz / matn) ─────────────────────────────────────
@router.callback_query(F.data.startswith("aset_"))
async def aset_field(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    key = call.data[5:]
    if key not in FIELDS:
        await _ack(call); return
    await _ack(call)
    label, ftype = FIELDS[key]
    cfg = get_runtime_config()
    hint = {
        "int":     "Yangi qiymatni son bilan yuboring (masalan: 19000).",
        "percent": "Yangi foizni yuboring (1 dan 99 gacha, masalan: 10).",
        "text":    "Yangi matnni yuboring. O'chirish uchun «-» yuboring.",
    }[ftype]
    await state.set_state(AdminSetValue.waiting_value)
    await state.update_data(field=key)
    await call.message.answer(
        f"{label}\n"
        f"Joriy qiymat: <b>{_fmt_value(key, _get_field(cfg, key))}</b>\n\n{hint}",
        parse_mode="HTML", reply_markup=_cancel_kb(),
    )


@router.message(AdminSetValue.waiting_value)
async def aset_value(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id): return
    data = await state.get_data()
    key = data.get("field", "")
    if key not in FIELDS:
        await state.clear(); return
    label, ftype = FIELDS[key]
    raw = (message.text or "").strip()

    if ftype in ("int", "percent"):
        digits = raw.replace(" ", "").replace(",", "")
        if not digits.isdigit():
            await message.answer("Faqat son yuboring.", reply_markup=_cancel_kb())
            return
        value = int(digits)
        if ftype == "percent" and not (1 <= value <= 99):
            await message.answer("Foiz 1 dan 99 gacha bo'lishi kerak.",
                                 reply_markup=_cancel_kb())
            return
        if ftype == "int" and value <= 0 and key != "delivery_fee":
            await message.answer("Musbat son yuboring.", reply_markup=_cancel_kb())
            return
    else:
        value = "" if raw == "-" else raw
        if not raw:
            await message.answer("Matn yuboring yoki «-» bilan tozalang.",
                                 reply_markup=_cancel_kb())
            return

    set_runtime_field(key, value)
    await state.clear()
    text, kb = _settings_menu()
    await message.answer(f"✅ {label} yangilandi.")
    await message.answer(text, parse_mode="HTML", reply_markup=kb)


# ─── 🏢 Biz haqimizda maydonlari ─────────────────────────────────────────────
@router.callback_query(F.data == "asetabout")
async def aset_about(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    cfg = get_runtime_config()
    rows = []
    for key in ("about.company", "about.phone", "about.telegram",
                "about.work_hours", "about.address", "about.map_link",
                "about.requisites"):
        label, _ = FIELDS[key]
        rows.append([InlineKeyboardButton(
            text=f"{label}: {_fmt_value(key, _get_field(cfg, key))}",
            callback_data=f"aset_{key}")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_settings")])
    await _admin_nav(call,
                     "🏢 <b>Biz haqimizda</b> — maydonni tanlang:",
                     InlineKeyboardMarkup(inline_keyboard=rows))


# ─── 📢 Popup xabar ──────────────────────────────────────────────────────────
@router.callback_query(F.data == "asetpopup")
async def aset_popup(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    pop = get_runtime_config().get("popup", {})
    status = "🟢 yoqilgan" if (pop.get("enabled") and pop.get("text")) else "⚪ o'chiq"
    cur = pop.get("text") or "—"
    rows = [
        [InlineKeyboardButton(text="✏️ Yangi popup yozish", callback_data="apopup_new")],
    ]
    if pop.get("enabled") and pop.get("text"):
        rows.append([InlineKeyboardButton(text="🚫 Popupni o'chirish",
                                          callback_data="apopup_off")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_settings")])
    await _admin_nav(
        call,
        "📢 <b>Popup xabar</b>\n────────\n"
        "Yangi popup saqlanganda u har bir foydalanuvchiga keyingi "
        "yozishmasida <b>bir marta</b> ko'rsatiladi.\n\n"
        f"Holat: {status}\n\nJoriy matn:\n{cur}",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "apopup_new")
async def apopup_new(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    await state.set_state(AdminPopup.waiting_text)
    await call.message.answer(
        "Popup matnini yuboring (HTML formatlash mumkin):",
        reply_markup=_cancel_kb(),
    )


@router.message(AdminPopup.waiting_text)
async def apopup_save(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id): return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Matn yuboring.", reply_markup=_cancel_kb())
        return
    pop = get_runtime_config().get("popup", {})
    set_runtime_field("popup", {
        "id": int(pop.get("id", 0)) + 1,
        "text": text,
        "enabled": True,
    })
    await state.clear()
    await message.answer("✅ Popup saqlandi va yoqildi. Ko'rinishi:")
    await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "apopup_off")
async def apopup_off(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    pop = get_runtime_config().get("popup", {})
    pop["enabled"] = False
    set_runtime_field("popup", pop)
    await call.message.answer("🚫 Popup o'chirildi.")


# ─── ⭐ Xaridorlar fikrlari ───────────────────────────────────────────────────
@router.callback_query(F.data == "asettst")
async def aset_testimonials(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    items = get_testimonials()
    rows = [[InlineKeyboardButton(text="➕ Fikr qo'shish (rasm/video)",
                                  callback_data="atst_add")]]
    for t in items:
        cap = (t.get("caption") or "").strip() or f"{t.get('media_type', '')} fikr"
        cap = cap if len(cap) <= 25 else cap[:25] + "…"
        rows.append([
            InlineKeyboardButton(text=f"👁 #{t['id']} {cap}",
                                 callback_data=f"atst_view_{t['id']}"),
            InlineKeyboardButton(text="🗑", callback_data=f"atst_del_{t['id']}"),
        ])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_settings")])
    await _admin_nav(
        call,
        f"⭐ <b>Xaridorlar fikrlari</b> ({len(items)} ta)\n────────\n"
        "Rasm yoki video ko'rinishidagi mijoz fikrlarini shu yerdan boshqarasiz.",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "atst_add")
async def atst_add(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    await state.set_state(AdminTestimonial.waiting_media)
    await call.message.answer(
        "Mijoz fikrini <b>rasm yoki video</b> ko'rinishida yuboring.\n"
        "Izoh (caption) qo'shsangiz — u ham saqlanadi.",
        parse_mode="HTML", reply_markup=_cancel_kb(),
    )


@router.message(AdminTestimonial.waiting_media, F.photo | F.video)
async def atst_save(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id): return
    if message.video:
        media_type, file_id = "video", message.video.file_id
    else:
        media_type, file_id = "photo", message.photo[-1].file_id
    tst_id = add_testimonial(media_type, file_id, (message.caption or "").strip())
    await state.clear()
    await message.answer(f"✅ Fikr #{tst_id} qo'shildi — endi u "
                         "«⭐ Xaridorlar fikrlari» bo'limida ko'rinadi.")


@router.message(AdminTestimonial.waiting_media)
async def atst_invalid(message: Message):
    await message.answer("Rasm yoki video yuboring (yoki bekor qiling).",
                         reply_markup=_cancel_kb())


@router.callback_query(F.data.startswith("atst_view_"))
async def atst_view(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    tst_id = int(call.data.split("_")[2])
    t = next((x for x in get_testimonials() if x.get("id") == tst_id), None)
    if not t:
        return
    try:
        if t.get("media_type") == "video":
            await call.message.answer_video(t["file_id"], caption=t.get("caption") or None)
        else:
            await call.message.answer_photo(t["file_id"], caption=t.get("caption") or None)
    except Exception:
        await call.message.answer("Media yuborilmadi (file_id eskirgan bo'lishi mumkin).")


@router.callback_query(F.data.startswith("atst_del_"))
async def atst_del(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    tst_id = int(call.data.split("_")[2])
    if delete_testimonial(tst_id):
        await call.answer("O'chirildi.")
    else:
        await call.answer("Topilmadi.")
    await aset_testimonials(call)


# ─── ❓ FAQ savol-javoblar ────────────────────────────────────────────────────
@router.callback_query(F.data == "asetfaq")
async def aset_faq(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    faq = get_runtime_config().get("faq", [])
    rows = [[InlineKeyboardButton(text="➕ Savol-javob qo'shish",
                                  callback_data="afaq_add")]]
    for i, item in enumerate(faq):
        q = item.get("q", "")
        q = q if len(q) <= 30 else q[:30] + "…"
        rows.append([
            InlineKeyboardButton(text=f"👁 {q}", callback_data=f"afaq_view_{i}"),
            InlineKeyboardButton(text="🗑", callback_data=f"afaq_del_{i}"),
        ])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_settings")])
    await _admin_nav(
        call,
        f"❓ <b>FAQ</b> ({len(faq)} ta savol)\n────────\n"
        "Javob matnida {prepay}, {threshold}, {fee}, {phone} o'rinbosarlarini "
        "ishlatish mumkin — ko'rsatishda joriy qiymatlar qo'yiladi.",
        InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data == "afaq_add")
async def afaq_add(call: CallbackQuery, state: FSMContext):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    await state.set_state(AdminFaq.waiting_q)
    await call.message.answer("Savol matnini yuboring:", reply_markup=_cancel_kb())


@router.message(AdminFaq.waiting_q)
async def afaq_q(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id): return
    q = (message.text or "").strip()
    if not q:
        await message.answer("Savol matnini yuboring.", reply_markup=_cancel_kb())
        return
    await state.update_data(faq_q=q)
    await state.set_state(AdminFaq.waiting_a)
    await message.answer("Endi javob matnini yuboring:", reply_markup=_cancel_kb())


@router.message(AdminFaq.waiting_a)
async def afaq_a(message: Message, state: FSMContext):
    if not is_owner(message.from_user.id): return
    a = (message.text or "").strip()
    if not a:
        await message.answer("Javob matnini yuboring.", reply_markup=_cancel_kb())
        return
    data = await state.get_data()
    faq = get_runtime_config().get("faq", [])
    faq.append({"q": data.get("faq_q", ""), "a": a})
    set_runtime_field("faq", faq)
    await state.clear()
    await message.answer("✅ Savol-javob qo'shildi.")


@router.callback_query(F.data.startswith("afaq_view_"))
async def afaq_view(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    await _ack(call)
    faq = get_runtime_config().get("faq", [])
    idx = int(call.data.split("_")[2])
    if idx >= len(faq):
        return
    item = faq[idx]
    await call.message.answer(
        f"❓ <b>{item.get('q', '')}</b>\n────────\n{item.get('a', '')}",
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("afaq_del_"))
async def afaq_del(call: CallbackQuery):
    if not is_owner(call.from_user.id): return
    faq = get_runtime_config().get("faq", [])
    idx = int(call.data.split("_")[2])
    if idx < len(faq):
        faq.pop(idx)
        set_runtime_field("faq", faq)
        await call.answer("O'chirildi.")
    else:
        await call.answer("Topilmadi.")
    await aset_faq(call)
