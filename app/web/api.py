"""Mini App JSON API — do'kon ma'lumotlari va zakaz qabul qilish.

Hamma funksiya botdagi bilan bir xil `app.storage` funksiyalarini ishlatadi
(bir xil jarayon, bir xil kesh) — ma'lumot to'liq mos keladi.
"""

import json
import logging
import os
import time
import uuid

from aiohttp import web
from aiogram.types import (FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup)

from app.app.config.settings import settings
from app.services import runtime_settings as rs
from app.storage import (DATA_DIR, get_all_products, get_product_by_id,
                         product_photos, product_stock, save_order,
                         search_products, set_user_field, track_event,
                         use_promo, validate_promo)
from app.ui import normalize_uz_phone
from app.web.auth import InitDataError, validate_init_data

logger = logging.getLogger(__name__)

RECEIPTS_DIR = os.path.join(DATA_DIR, "receipts")
os.makedirs(RECEIPTS_DIR, exist_ok=True)

MAX_RECEIPT_BYTES = 10 * 1024 * 1024   # 10 MB
_ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/heic",
                  "image/heif"}


def _card(p: dict) -> dict:
    """Ro'yxat (grid) uchun qisqartirilgan mahsulot ma'lumoti."""
    photos = product_photos(p)
    return {
        "id": p.get("id"),
        "name": p.get("name", ""),
        "price": p.get("price", 0),
        "old_price": p.get("old_price"),
        "shop_name": p.get("shop_name", ""),
        "city": p.get("city", ""),
        "photo": photos[0] if photos else None,
    }


def _is_available(p: dict) -> bool:
    if p.get("is_finished"):
        return False
    st = product_stock(p)
    return st is None or st > 0


async def list_products(request: web.Request) -> web.Response:
    """GET /api/products?q=&limit= — do'kon ro'yxati."""
    q = (request.query.get("q") or "").strip()
    items = search_products(q) if q else get_all_products()
    items = [_card(p) for p in items if _is_available(p)]
    return web.json_response(items)


async def get_product(request: web.Request) -> web.Response:
    """GET /api/product/{id} — mahsulot detali."""
    try:
        pid = int(request.match_info["id"])
    except (KeyError, ValueError):
        return web.json_response({"error": "bad id"}, status=400)
    p = get_product_by_id(pid)
    if not p:
        return web.json_response({"error": "not found"}, status=404)
    photos = product_photos(p)
    return web.json_response({
        "id": p.get("id"),
        "name": p.get("name", ""),
        "description": p.get("description", ""),
        "price": p.get("price", 0),
        "old_price": p.get("old_price"),
        "shop_name": p.get("shop_name", ""),
        "city": p.get("city", ""),
        "warranty": p.get("warranty"),
        "photos": photos,
        "stock": product_stock(p),
        "available": _is_available(p),
    })


async def get_config(request: web.Request) -> web.Response:
    """GET /api/config — frontda narx/matn bot bilan bir xil bo'lishi uchun."""
    return web.json_response({
        "prepay_percent": rs.prepay_percent(),
        "delivery_fee": rs.delivery_fee(),
        "free_threshold": rs.free_threshold(),
        "contact_phone": rs.contact_phone(),
        "gift_text": rs.gift_text(),
        "card": settings.PLATFORM_CARD,
        "card_name": settings.PLATFORM_CARD_NAME,
    })


def _receipt_ext(content_type: str, filename: str) -> str:
    fn = (filename or "").lower()
    if content_type == "application/pdf" or fn.endswith(".pdf"):
        return ".pdf"
    if fn.endswith(".png"):
        return ".png"
    if fn.endswith(".webp"):
        return ".webp"
    return ".jpg"


async def _read_receipt(field) -> tuple[bytes, str]:
    """Multipart chek maydonini hajm chegarasi bilan o'qiydi. (bytes, ext)."""
    content_type = (field.headers or {}).get("Content-Type", "") or ""
    is_pdf = content_type == "application/pdf"
    if not is_pdf and content_type and content_type not in _ALLOWED_IMAGE:
        # ba'zi klientlar octet-stream yuboradi — fayl nomiga qarab yon beramiz
        pass
    chunks = []
    size = 0
    while True:
        chunk = await field.read_chunk()
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_RECEIPT_BYTES:
            raise ValueError("chek fayli juda katta")
        chunks.append(chunk)
    ext = _receipt_ext(content_type, getattr(field, "filename", ""))
    return b"".join(chunks), ext


async def create_order(request: web.Request) -> web.Response:
    """POST /api/order (multipart) — ilova ichidan to'liq zakaz.

    Maydonlar: initData (str), payload (JSON str), receipt (rasm/PDF fayl).
    Zakaz botdagi bilan bir xil dict shaklida saqlanadi; chek OWNER'ga admin
    tasdiq tugmalari bilan yuboriladi (paycfm_... oqimi o'zgarmasdan ishlaydi).
    """
    if not (request.content_type or "").startswith("multipart/"):
        return web.json_response({"error": "multipart kutilgan"}, status=400)
    try:
        reader = await request.multipart()
    except (AssertionError, ValueError):
        return web.json_response({"error": "bad multipart"}, status=400)

    init_data = None
    payload_raw = None
    receipt_bytes = None
    receipt_ext = ".jpg"

    async for field in reader:
        if field.name == "initData":
            init_data = (await field.text()).strip()
        elif field.name == "payload":
            payload_raw = await field.text()
        elif field.name == "receipt":
            try:
                receipt_bytes, receipt_ext = await _read_receipt(field)
            except ValueError as e:
                return web.json_response({"error": str(e)}, status=413)

    # 1) initData tekshiruvi — buyer_id faqat shundan olinadi
    try:
        user = validate_init_data(init_data or "")
    except InitDataError as e:
        logger.warning("initData rad etildi: %s", e)
        return web.json_response({"error": "auth"}, status=401)
    buyer_id = int(user["id"])
    buyer_name = " ".join(x for x in (user.get("first_name"),
                                      user.get("last_name")) if x) or "—"
    buyer_username = user.get("username")

    # 2) payload
    try:
        payload = json.loads(payload_raw or "{}")
    except json.JSONDecodeError:
        return web.json_response({"error": "bad payload"}, status=400)

    try:
        pid = int(payload.get("product_id"))
        qty = max(int(payload.get("quantity", 1)), 1)
    except (TypeError, ValueError):
        return web.json_response({"error": "bad product/qty"}, status=400)

    address = (payload.get("address") or "").strip()
    phone = normalize_uz_phone(payload.get("phone") or "")
    color = (payload.get("color") or "").strip()
    promo_code = (payload.get("promo_code") or "").strip()

    if not address:
        return web.json_response({"error": "no address"}, status=400)
    if not phone:
        return web.json_response({"error": "bad phone"}, status=400)
    if receipt_bytes is None:
        return web.json_response({"error": "no receipt"}, status=400)

    # 3) mahsulot va narx — SERVERDA hisoblanadi (mijoz narxiga ishonilmaydi)
    p = get_product_by_id(pid)
    if not p or not _is_available(p):
        return web.json_response({"error": "unavailable"}, status=409)

    promo_percent = 0
    if promo_code:
        promo = validate_promo(promo_code)
        promo_percent = int(promo.get("percent", 0)) if promo else 0
        if not promo:
            promo_code = ""   # yaroqsiz kod — e'tiborga olinmaydi

    base = int(p.get("price", 0))
    unit = int(base * (100 - promo_percent) / 100) if promo_percent else base
    total = unit * qty
    fee = 0 if total >= rs.free_threshold() else rs.delivery_fee()
    commission = int(total * rs.prepay_rate())

    # 4) chek faylini saqlash
    receipt_name = f"web_{int(time.time())}_{uuid.uuid4().hex[:8]}{receipt_ext}"
    receipt_path = os.path.join(RECEIPTS_DIR, receipt_name)
    with open(receipt_path, "wb") as f:
        f.write(receipt_bytes)

    # 5) zakazni saqlash — common.py:order_phone bilan bir xil dict
    order_id = save_order({
        "buyer_id":       buyer_id,
        "buyer_name":     buyer_name,
        "buyer_username": buyer_username,
        "seller_id":      p["seller_id"],
        "product_id":     pid,
        "product_name":   p["name"],
        "quantity":       qty,
        "unit_price":     unit,
        "total":          total,
        "prepay":         commission,
        "commission":     commission,
        "delivery_fee":   fee,
        "fulfillment":    "delivery",
        "delivery":       "taxi",
        "address":        address,
        "phone":          phone,
        "color":          color,
        "promo_code":     promo_code or "",
        "promo_percent":  promo_percent,
        "status":         "pending",
        "receipt":        receipt_name,
        "source":         "webapp",
    })
    set_user_field(buyer_id, "phone", phone)
    if promo_code:
        try:
            use_promo(promo_code)
        except Exception:
            pass
    track_event("payment_receipt", buyer_id)

    # 6) chekni admin (OWNER)ga — order_receipt bilan bir xil tugmalar
    is_pdf = receipt_ext == ".pdf"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiq + 🟢 Bugun",   callback_data=f"paycfm_{order_id}_today"),
         InlineKeyboardButton(text="✅ Tasdiq + 🟡 24 soat", callback_data=f"paycfm_{order_id}_24h")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"payrej_{order_id}")],
    ])
    caption = (
        f"<b>Buyurtma #{order_id} — to'lov cheki</b>  <i>(ilova)</i>\n\n"
        f"Mahsulot: {p['name']}\n"
        f"Miqdor: {qty} × {unit:,} = {total:,} so'm\n"
        f"Oldindan to'lov ({rs.prepay_percent()}%): {commission:,} so'm\n"
        f"Xaridor: {buyer_name}"
        + (f" (@{buyer_username})" if buyer_username else "") + "\n"
        f"Telefon: {phone}\n"
        f"Manzil: {address}"
    )
    try:
        from app.bot.bot import bot
        if is_pdf:
            await bot.send_document(settings.OWNER_ID, FSInputFile(receipt_path),
                                    caption=caption, parse_mode="HTML",
                                    reply_markup=kb)
        else:
            await bot.send_photo(settings.OWNER_ID, FSInputFile(receipt_path),
                                 caption=caption, parse_mode="HTML",
                                 reply_markup=kb)
    except Exception:
        logger.exception("Chekni adminga yuborib bo'lmadi (#%s)", order_id)

    return web.json_response({"ok": True, "order_id": order_id})
