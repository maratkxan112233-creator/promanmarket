"""Guruhlarga avtomatik reklama tarqatish.

Ishlash tartibi:
1. Bot guruhga qo'shilsa — guruh avtomatik ro'yxatga olinadi (guruhdan
   chiqarilsa — ro'yxatdan o'chadi). AUKSION guruhi ro'yxatga KIRMAYDI.
2. Rejalashtirgich (ads_scheduler) har daqiqada tekshiradi: interval vaqti
   kelgan bo'lsa, navbatdagi reklamani BARCHA guruhlarga yuboradi.
   Reklamalar navbatma-navbat (rotatsiya) yuboriladi — har safar boshqasi.
3. Reklama KECHAYU KUNDUZ (24/7) yuboriladi — tungi tanaffus yo'q.
4. Boshqarish: Admin panel → «📣 Guruhlarga reklama» yoki /reklama buyrug'i
   (faqat owner): yoqish/to'xtatish, interval, reklama qo'shish/o'chirish,
   guruhlar ro'yxati, darhol yuborish.

Rasm bilan reklama qo'shish: «➕ Reklama qo'shish» bosib, rasmni izohi
(caption) bilan yuboring — bot file_id ni saqlab, o'sha rasm+matnni yuboradi.

MUHIM: bot guruhda yozish huquqiga ega bo'lishi kerak (oddiy a'zo yetarli).
"""
import asyncio
import logging
import time
from datetime import datetime

from aiogram import Router, F
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.exceptions import (TelegramBadRequest, TelegramForbiddenError,
                                TelegramRetryAfter)
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, ChatMemberUpdated,
                           InlineKeyboardButton, InlineKeyboardMarkup, Message)

from app.app.config.settings import settings
from app.storage import (add_ad_group, add_group_ad, delete_group_ad,
                         get_ads_config, remove_ad_group, save_ads_config,
                         set_ads_field)

router = Router()
logger = logging.getLogger(__name__)

CHECK_EVERY = 60          # rejalashtirgich necha soniyada tekshiradi
SEND_PAUSE = 1.5          # guruhlar orasidagi pauza (flood-limit uchun)


def _is_owner(uid: int) -> bool:
    return uid == settings.OWNER_ID


class AdsAdd(StatesGroup):
    content = State()


class AdsInterval(StatesGroup):
    hours = State()


# ─── Guruhlarni avtomatik ro'yxatga olish ────────────────────────────────────
@router.my_chat_member()
async def on_membership_change(event: ChatMemberUpdated):
    """Bot guruhga qo'shilsa — ro'yxatga oladi, chiqarilsa — o'chiradi."""
    if event.chat.type not in ("group", "supergroup"):
        return
    # AUKSION guruhi ish guruhi — unga reklama yuborilmaydi
    if event.chat.id == settings.AUCTION_GROUP_ID:
        return

    status = event.new_chat_member.status
    title = event.chat.title or str(event.chat.id)
    from app.bot.bot import bot

    if status in ("member", "administrator"):
        add_ad_group(event.chat.id, title)
        logger.info("Reklama guruhi qo'shildi: %s (%s)", title, event.chat.id)
        try:
            await bot.send_message(
                settings.OWNER_ID,
                f"📣 Bot yangi guruhga qo'shildi:\n<b>{title}</b>\n\n"
                f"Guruh reklama ro'yxatiga olindi — endi reklamalar shu "
                f"guruhga ham boradi.", parse_mode="HTML")
        except Exception:
            pass
    elif status in ("left", "kicked"):
        if remove_ad_group(event.chat.id):
            logger.info("Reklama guruhi o'chirildi: %s (%s)", title, event.chat.id)


@router.message(F.chat.type.in_({"group", "supergroup"}))
async def register_seen_group(message: Message):
    """Bot ILGARI qo'shilgan guruhlar my_chat_member hodisasini bermaydi —
    shuning uchun guruhdan kelgan istalgan xabarda guruh ro'yxatga olinadi.
    Xabar boshqa handlerlarga ham o'tishi uchun SkipHandler tashlanadi."""
    if message.chat.id != settings.AUCTION_GROUP_ID:
        cfg = get_ads_config()
        if str(message.chat.id) not in (cfg.get("groups") or {}):
            add_ad_group(message.chat.id, message.chat.title or str(message.chat.id))
            logger.info("Reklama guruhi (xabardan) ro'yxatga olindi: %s (%s)",
                        message.chat.title, message.chat.id)
    raise SkipHandler


# ─── Reklamani yuborish ──────────────────────────────────────────────────────
async def _send_ad_to_group(bot, chat_id: int, ad: dict) -> bool:
    """Bitta guruhga bitta reklamani yuboradi. Flood-limitda kutib qayta
    urinadi. Guruh yopiq/o'chirilgan bo'lsa False qaytaradi (ro'yxatdan
    o'chirish uchun)."""
    for attempt in (1, 2):
        try:
            if ad.get("photo"):
                await bot.send_photo(chat_id, ad["photo"],
                                     caption=(ad.get("text") or None))
            else:
                await bot.send_message(chat_id, ad.get("text", ""))
            return True
        except TelegramRetryAfter as e:
            if attempt == 2:
                return True  # guruh tirik, shunchaki limit — o'chirmaymiz
            await asyncio.sleep(e.retry_after + 1)
        except (TelegramForbiddenError, TelegramBadRequest):
            return False  # bot chiqarilgan yoki guruh yo'q — ro'yxatdan o'chadi
        except Exception:
            logger.exception("Reklama yuborishda xato (chat %s)", chat_id)
            return True  # noma'lum xato — guruhni o'chirmaymiz
    return True


async def send_next_ad(bot) -> tuple[int, int]:
    """Navbatdagi reklamani barcha guruhlarga yuboradi.
    (yuborilgan guruhlar, o'chirilgan guruhlar) sonini qaytaradi."""
    cfg = get_ads_config()
    ads = cfg.get("ads") or []
    groups = dict(cfg.get("groups") or {})
    if not ads or not groups:
        return 0, 0

    idx = cfg.get("next_index", 0) % len(ads)
    ad = ads[idx]

    sent, dead = 0, []
    for cid in groups:
        ok = await _send_ad_to_group(bot, int(cid), ad)
        if ok:
            sent += 1
        else:
            dead.append(cid)
        await asyncio.sleep(SEND_PAUSE)

    # Holatni yangilaymiz (yuborish paytida sozlama o'zgargan bo'lishi mumkin,
    # shuning uchun qayta o'qiymiz)
    cfg = get_ads_config()
    for cid in dead:
        cfg["groups"].pop(cid, None)
    cfg["next_index"] = (idx + 1) % max(len(cfg.get("ads") or []), 1)
    cfg["last_sent"] = time.time()
    save_ads_config(cfg)
    return sent, len(dead)


async def ads_scheduler(bot):
    """Fon vazifasi: interval vaqti kelganda reklamani avtomatik yuboradi —
    KECHAYU KUNDUZ (24/7), tungi tanaffussiz.
    main.py da bot ishga tushganda start qilinadi."""
    await asyncio.sleep(30)  # bot to'liq ishga tushib olsin
    logger.info("Reklama rejalashtirgichi ishga tushdi (24/7 rejim)")
    while True:
        try:
            cfg = get_ads_config()
            if cfg.get("enabled") and cfg.get("groups") and cfg.get("ads"):
                due = cfg.get("last_sent", 0) + cfg.get("interval_hours", 6) * 3600
                if time.time() >= due:
                    sent, dead = await send_next_ad(bot)
                    logger.info("Avto-reklama: %s guruhga yuborildi, "
                                "%s guruh ro'yxatdan o'chdi", sent, dead)
        except Exception:
            logger.exception("Reklama rejalashtirgichida xato")
        await asyncio.sleep(CHECK_EVERY)


# ─── Admin panel: 📣 Guruhlarga reklama ──────────────────────────────────────
def _panel_text() -> str:
    cfg = get_ads_config()
    status = "🟢 Yoqilgan" if cfg.get("enabled") else "🔴 To'xtatilgan"
    last = cfg.get("last_sent", 0)
    if last:
        last_s = datetime.fromtimestamp(last).strftime("%d.%m.%Y %H:%M")
        nxt = datetime.fromtimestamp(
            last + cfg.get("interval_hours", 6) * 3600).strftime("%d.%m.%Y %H:%M")
    else:
        last_s, nxt = "hali yuborilmagan", "tez orada"
    return (
        "📣 <b>Guruhlarga reklama</b>\n"
        "──────────────\n"
        f"Holat: <b>{status}</b>\n"
        f"Interval: har <b>{cfg.get('interval_hours', 6)} soat</b>da\n"
        f"Guruhlar: <b>{len(cfg.get('groups', {}))}</b> ta\n"
        f"Reklamalar: <b>{len(cfg.get('ads', []))}</b> ta (navbatma-navbat)\n"
        f"Oxirgi yuborilgan: {last_s}\n"
        f"Keyingisi: {nxt}\n\n"
        f"🕐 Kechayu kunduz (24/7) yuboriladi — tungi tanaffus yo'q.\n"
        f"➕ Guruh qo'shish uchun botni guruhga a'zo qiling — "
        f"o'zi ro'yxatga olinadi (guruhda birorta xabar yozilishi kifoya)."
    )


def _panel_kb() -> InlineKeyboardMarkup:
    cfg = get_ads_config()
    toggle = ("⏸ To'xtatish" if cfg.get("enabled") else "▶️ Yoqish")
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=toggle, callback_data="ads_toggle"),
         InlineKeyboardButton(text="🚀 Hozir yuborish", callback_data="ads_sendnow")],
        [InlineKeyboardButton(text="🗂 Reklamalar", callback_data="ads_list"),
         InlineKeyboardButton(text="➕ Reklama qo'shish", callback_data="ads_add")],
        [InlineKeyboardButton(text="👥 Guruhlar", callback_data="ads_groups"),
         InlineKeyboardButton(text="⏱ Interval", callback_data="ads_interval")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_back")],
    ])


async def _show_panel(call: CallbackQuery):
    try:
        await call.message.edit_text(_panel_text(), parse_mode="HTML",
                                     reply_markup=_panel_kb())
    except Exception:
        try:
            await call.message.answer(_panel_text(), parse_mode="HTML",
                                      reply_markup=_panel_kb())
        except Exception:
            pass


@router.callback_query(F.data == "admin_ads")
async def ads_panel(call: CallbackQuery, state: FSMContext):
    if not _is_owner(call.from_user.id):
        await call.answer("Faqat egasi uchun", show_alert=True)
        return
    await state.clear()
    await call.answer()
    await _show_panel(call)


@router.message(Command("reklama"), F.chat.type == "private")
async def ads_cmd(message: Message):
    if not _is_owner(message.from_user.id):
        return
    await message.answer(_panel_text(), parse_mode="HTML",
                         reply_markup=_panel_kb())


@router.callback_query(F.data == "ads_toggle")
async def ads_toggle(call: CallbackQuery):
    if not _is_owner(call.from_user.id):
        return
    cfg = get_ads_config()
    set_ads_field("enabled", not cfg.get("enabled"))
    await call.answer("✅ O'zgartirildi")
    await _show_panel(call)


@router.callback_query(F.data == "ads_sendnow")
async def ads_sendnow(call: CallbackQuery):
    if not _is_owner(call.from_user.id):
        return
    cfg = get_ads_config()
    if not cfg.get("groups"):
        await call.answer("Guruhlar yo'q. Avval botni guruhga qo'shing.",
                          show_alert=True)
        return
    if not cfg.get("ads"):
        await call.answer("Reklama yo'q. Avval reklama qo'shing.",
                          show_alert=True)
        return
    await call.answer("Yuborilmoqda…")
    from app.bot.bot import bot
    sent, dead = await send_next_ad(bot)
    note = f"✅ Reklama {sent} ta guruhga yuborildi."
    if dead:
        note += f"\n🗑 {dead} ta guruh (bot chiqarilgan) ro'yxatdan o'chirildi."
    try:
        await call.message.answer(note)
    except Exception:
        pass
    await _show_panel(call)


# ─── Reklamalar ro'yxati / o'chirish / ko'rish ───────────────────────────────
async def _render_ads_list(call: CallbackQuery):
    cfg = get_ads_config()
    ads = cfg.get("ads", [])
    if not ads:
        rows = [[InlineKeyboardButton(text="➕ Reklama qo'shish",
                                      callback_data="ads_add")],
                [InlineKeyboardButton(text="🔙 Orqaga",
                                      callback_data="admin_ads")]]
        try:
            await call.message.edit_text(
                "🗂 <b>Reklamalar</b>\n\nHozircha reklama yo'q.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        except Exception:
            pass
        return

    lines = ["🗂 <b>Reklamalar</b> — navbatma-navbat yuboriladi\n"]
    rows = []
    for a in ads:
        preview = (a.get("text") or "").replace("\n", " ")[:50]
        photo_mark = "🖼 " if a.get("photo") else ""
        lines.append(f"<b>#{a['id']}</b> {photo_mark}{preview}…")
        rows.append([
            InlineKeyboardButton(text=f"👁 #{a['id']} ko'rish",
                                 callback_data=f"ads_view_{a['id']}"),
            InlineKeyboardButton(text="🗑 O'chirish",
                                 callback_data=f"ads_del_{a['id']}"),
        ])
    rows.append([InlineKeyboardButton(text="➕ Reklama qo'shish",
                                      callback_data="ads_add")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga",
                                      callback_data="admin_ads")])
    try:
        await call.message.edit_text(
            "\n".join(lines), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except Exception:
        pass


@router.callback_query(F.data == "ads_list")
async def ads_list(call: CallbackQuery):
    if not _is_owner(call.from_user.id):
        return
    await call.answer()
    await _render_ads_list(call)


@router.callback_query(F.data.startswith("ads_view_"))
async def ads_view(call: CallbackQuery):
    if not _is_owner(call.from_user.id):
        return
    ad_id = int(call.data.rsplit("_", 1)[1])
    cfg = get_ads_config()
    ad = next((a for a in cfg.get("ads", []) if a.get("id") == ad_id), None)
    if not ad:
        await call.answer("Topilmadi", show_alert=True)
        return
    await call.answer()
    # Reklama guruhga qanday chiqsa — shunday ko'rsatamiz
    try:
        if ad.get("photo"):
            await call.message.answer_photo(ad["photo"],
                                            caption=(ad.get("text") or None))
        else:
            await call.message.answer(ad.get("text", ""))
    except Exception:
        await call.answer("Ko'rsatib bo'lmadi", show_alert=True)


@router.callback_query(F.data.startswith("ads_del_"))
async def ads_del(call: CallbackQuery):
    if not _is_owner(call.from_user.id):
        return
    ad_id = int(call.data.rsplit("_", 1)[1])
    if delete_group_ad(ad_id):
        await call.answer("🗑 O'chirildi")
    else:
        await call.answer("Topilmadi", show_alert=True)
    await _render_ads_list(call)


# ─── Guruhlar ro'yxati / o'chirish ──────────────────────────────────────────
async def _render_groups(call: CallbackQuery):
    cfg = get_ads_config()
    groups = cfg.get("groups", {})
    lines = ["👥 <b>Reklama guruhlari</b>\n"]
    rows = []
    if not groups:
        lines.append("Hozircha guruh yo'q.\n\nBotni istalgan guruhga a'zo "
                     "qiling — o'zi ro'yxatga olinadi.")
    for cid, info in groups.items():
        title = info.get("title", cid)
        lines.append(f"• {title}")
        rows.append([InlineKeyboardButton(
            text=f"🗑 {title[:30]}", callback_data=f"ads_gdel_{cid}")])
    rows.append([InlineKeyboardButton(text="🔙 Orqaga",
                                      callback_data="admin_ads")])
    try:
        await call.message.edit_text(
            "\n".join(lines), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
    except Exception:
        pass


@router.callback_query(F.data == "ads_groups")
async def ads_groups(call: CallbackQuery):
    if not _is_owner(call.from_user.id):
        return
    await call.answer()
    await _render_groups(call)


@router.callback_query(F.data.startswith("ads_gdel_"))
async def ads_gdel(call: CallbackQuery):
    if not _is_owner(call.from_user.id):
        return
    cid = call.data[len("ads_gdel_"):]
    if remove_ad_group(cid):
        await call.answer("🗑 Ro'yxatdan o'chirildi")
    else:
        await call.answer("Topilmadi", show_alert=True)
    await _render_groups(call)


# ─── Reklama qo'shish (matn yoki rasm+izoh) ──────────────────────────────────
@router.callback_query(F.data == "ads_add")
async def ads_add_start(call: CallbackQuery, state: FSMContext):
    if not _is_owner(call.from_user.id):
        return
    await call.answer()
    await state.set_state(AdsAdd.content)
    await call.message.answer(
        "➕ <b>Yangi reklama</b>\n\n"
        "Reklama <b>matnini</b> yuboring — yoki <b>rasmni izohi bilan</b> "
        "yuboring (rasm + matn birga chiqadi).\n\n"
        "Bekor qilish: /cancel", parse_mode="HTML")


@router.message(AdsAdd.content, F.text == "/cancel")
@router.message(AdsInterval.hours, F.text == "/cancel")
async def ads_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi. Panel: /reklama")


@router.message(AdsAdd.content, F.photo)
async def ads_add_photo(message: Message, state: FSMContext):
    if not _is_owner(message.from_user.id):
        return
    await state.clear()
    ad_id = add_group_ad(message.caption or "", message.photo[-1].file_id)
    await message.answer(
        f"✅ Reklama #{ad_id} (rasm bilan) saqlandi.\n"
        f"Endi u navbat bilan guruhlarga yuboriladi.\n\nPanel: /reklama")


@router.message(AdsAdd.content, F.text)
async def ads_add_text(message: Message, state: FSMContext):
    if not _is_owner(message.from_user.id):
        return
    text = (message.text or "").strip()
    if len(text) < 10:
        await message.answer("Matn juda qisqa. Kamida 10 belgi yozing "
                             "yoki /cancel bosing.")
        return
    await state.clear()
    ad_id = add_group_ad(text)
    await message.answer(
        f"✅ Reklama #{ad_id} saqlandi.\n"
        f"Endi u navbat bilan guruhlarga yuboriladi.\n\nPanel: /reklama")


# ─── Interval sozlash ────────────────────────────────────────────────────────
@router.callback_query(F.data == "ads_interval")
async def ads_interval_start(call: CallbackQuery, state: FSMContext):
    if not _is_owner(call.from_user.id):
        return
    await call.answer()
    await state.set_state(AdsInterval.hours)
    cfg = get_ads_config()
    await call.message.answer(
        f"⏱ Hozirgi interval: har <b>{cfg.get('interval_hours', 6)} soat</b>da.\n\n"
        f"Yangi intervalni yozing (soatlarda, 1 dan 48 gacha).\n"
        f"Masalan: <code>4</code> — har 4 soatda bitta reklama.\n\n"
        f"Bekor qilish: /cancel", parse_mode="HTML")


@router.message(AdsInterval.hours, F.text)
async def ads_interval_set(message: Message, state: FSMContext):
    if not _is_owner(message.from_user.id):
        return
    try:
        hours = int((message.text or "").strip())
        if not 1 <= hours <= 48:
            raise ValueError
    except ValueError:
        await message.answer("1 dan 48 gacha son yozing. Masalan: 6")
        return
    await state.clear()
    set_ads_field("interval_hours", hours)
    await message.answer(f"✅ Interval saqlandi: har {hours} soatda "
                         f"bitta reklama yuboriladi.\n\nPanel: /reklama")
