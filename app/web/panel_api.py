"""Mini App ichidagi ADMIN va SELLER panellari uchun JSON API.

Rollar botdagi bilan bir xil aniqlanadi (fayldagi a'zolik orqali):
  - owner  — settings.OWNER_ID
  - seller — sellers.json (yoki do'kon yordamchisi)
Har bir endpoint `initData` imzosini tekshiradi va rolni serverda qayta
aniqlaydi — mijoz yuborgan id/rolga hech qachon ishonilmaydi.

Barcha ma'lumot o'zgarishlari `app.storage` funksiyalari orqali (bot bilan
bir xil atomik yozuv) bajariladi — bot va ilova bir xil holatni ko'radi.
"""

import json
import logging
import os
import time
import uuid

from aiohttp import web

from app.app.config.settings import settings
from app.storage import (DATA_DIR, add_product, admin_delete_product,
                         delete_product, get_all_products, get_order_by_id,
                         get_owner_id, get_product_by_id, get_seller,
                         get_seller_orders, get_seller_products, get_sellers,
                         is_sub_admin, product_photos, product_stock, to_int,
                         update_order_status, update_product, update_seller)
from app.web.api import _init_data_from, _is_available
from app.web.auth import InitDataError, validate_init_data

logger = logging.getLogger(__name__)

# Yuklangan mahsulot rasmlari shu yerda saqlanadi va /media/ orqali beriladi.
MEDIA_DIR = os.path.join(DATA_DIR, "product_images")
os.makedirs(MEDIA_DIR, exist_ok=True)

MAX_IMAGE_BYTES = 6 * 1024 * 1024   # bitta rasm uchun 6 MB
_ALLOWED_IMAGE = {"image/jpeg", "image/png", "image/webp", "image/heic",
                  "image/heif"}

# Seller o'zgartira oladigan buyurtma holatlari (whitelist).
ALLOWED_ORDER_STATUS = {"pending", "paid", "processing", "shipped",
                        "delivered", "cancelled"}


# ─── Autentifikatsiya / rol ──────────────────────────────────────────────────
def _user(init_data: str):
    """initData'ni tekshiradi. To'g'ri bo'lsa user dict, aks holda None."""
    try:
        return validate_init_data(init_data or "")
    except InitDataError:
        return None


def _is_owner(uid: int) -> bool:
    return uid == settings.OWNER_ID


def _is_admin(uid: int) -> bool:
    return _is_owner(uid) or is_sub_admin(uid)


async def _body(request: web.Request) -> dict:
    try:
        return await request.json()
    except (json.JSONDecodeError, Exception):
        return {}


def _err(msg: str, status: int = 400) -> web.Response:
    return web.json_response({"error": msg}, status=status)


# ─── /api/me — foydalanuvchi rollari (frontda tugmalarni ko'rsatish uchun) ─────
async def get_me(request: web.Request) -> web.Response:
    user = _user(_init_data_from(request))
    if not user:
        return web.json_response({"is_owner": False, "is_admin": False,
                                  "is_seller": False, "shop": None})
    uid = int(user["id"])
    owner_id = get_owner_id(uid)
    shop = None
    if owner_id is not None:
        s = get_seller(owner_id) or {}
        shop = {"shop_name": s.get("shop_name", ""),
                "is_assistant": owner_id != uid}
    return web.json_response({
        "is_owner": _is_owner(uid),
        "is_admin": _is_admin(uid),
        "is_seller": owner_id is not None,
        "shop": shop,
    })


# ─── Rasm yuklash yordamchilari ──────────────────────────────────────────────
def _img_ext(content_type: str, filename: str) -> str:
    fn = (filename or "").lower()
    if content_type == "image/png" or fn.endswith(".png"):
        return ".png"
    if content_type == "image/webp" or fn.endswith(".webp"):
        return ".webp"
    return ".jpg"


async def _save_image(field) -> str | None:
    """Multipart rasm maydonini saqlaydi. Muvaffaqiyatda "/media/<nom>" URL,
    aks holda None qaytaradi. Fayl nomi serverda generatsiya qilinadi (mijoz
    nomiga yo'l uchun ishonilmaydi)."""
    content_type = (field.headers or {}).get("Content-Type", "") or ""
    if content_type and content_type not in _ALLOWED_IMAGE:
        # ba'zi klientlar octet-stream yuboradi — nomga qarab yon beramiz
        if not (getattr(field, "filename", "") or "").lower().endswith(
                (".jpg", ".jpeg", ".png", ".webp")):
            return None
    chunks, size = [], 0
    while True:
        chunk = await field.read_chunk()
        if not chunk:
            break
        size += len(chunk)
        if size > MAX_IMAGE_BYTES:
            return None
        chunks.append(chunk)
    if not chunks:
        return None
    ext = _img_ext(content_type, getattr(field, "filename", ""))
    name = f"p_{int(time.time())}_{uuid.uuid4().hex[:8]}{ext}"
    with open(os.path.join(MEDIA_DIR, name), "wb") as f:
        f.write(b"".join(chunks))
    return f"/media/{name}"


async def _parse_product_form(request: web.Request):
    """Mahsulot formasini (multipart) o'qiydi.
    Qaytaradi: (init_data, payload_dict, yangi_rasm_urllar). multipart bo'lmasa
    init_data="" qaytaradi (handler 401/400 bilan javob beradi)."""
    if not (request.content_type or "").startswith("multipart/"):
        return "", {}, []
    try:
        reader = await request.multipart()
    except (AssertionError, ValueError):
        return "", {}, []
    init_data, payload, new_urls = "", {}, []
    async for field in reader:
        if field.name == "initData":
            init_data = (await field.text()).strip()
        elif field.name == "payload":
            try:
                payload = json.loads(await field.text() or "{}")
            except json.JSONDecodeError:
                payload = {}
        elif field.name == "image":
            url = await _save_image(field)
            if url:
                new_urls.append(url)
    return init_data, (payload if isinstance(payload, dict) else {}), new_urls


def _product_fields(payload: dict, photos: list) -> dict:
    """payload'dan faqat ruxsat etilgan mahsulot maydonlarini yig'adi."""
    f = {"photos": photos}
    if "name" in payload:
        f["name"] = str(payload.get("name") or "").strip()
    if "description" in payload:
        f["description"] = str(payload.get("description") or "")
    if "price" in payload:
        f["price"] = max(to_int(payload.get("price"), 0), 0)
    if "old_price" in payload:
        op = to_int(payload.get("old_price"), 0)
        f["old_price"] = op if op > 0 else None
    if "colors" in payload:
        raw = payload.get("colors")
        if isinstance(raw, list):
            f["colors"] = [str(c).strip() for c in raw if str(c).strip()]
        else:
            f["colors"] = [c.strip() for c in str(raw or "").split(",")
                           if c.strip()]
    if "stock" in payload:
        s = payload.get("stock")
        if s in (None, ""):
            f["stock"] = None
            f["is_finished"] = False
        else:
            st = max(to_int(s, 0), 0)
            f["stock"] = st
            f["is_finished"] = (st == 0)
    if "is_finished" in payload:
        f["is_finished"] = bool(payload.get("is_finished"))
    return f


def _final_photos(p: dict, payload: dict, new_urls: list) -> list:
    """Tahrirda saqlanadigan rasmlar: mavjudlardan qoldirilganlari + yangilar."""
    existing = product_photos(p)
    keep = payload.get("keep_photos")
    if isinstance(keep, list):
        base = [u for u in keep if u in existing]   # faqat haqiqiy mavjudlar
    else:
        base = existing
    return base + [u for u in new_urls if u not in base]


def _admin_card(p: dict) -> dict:
    """Panel ro'yxati uchun to'liq (tahrir qilinadigan) mahsulot ma'lumoti."""
    photos = product_photos(p)
    return {
        "id": p.get("id"),
        "name": p.get("name", ""),
        "description": p.get("description", ""),
        "price": p.get("price", 0),
        "old_price": p.get("old_price"),
        "stock": product_stock(p),
        "colors": p.get("colors") or [],
        "photos": photos,
        "shop_name": p.get("shop_name", ""),
        "seller_id": p.get("seller_id"),
        "is_finished": bool(p.get("is_finished")),
        "available": _is_available(p),
    }


# ─── SELLER: mahsulotlar ─────────────────────────────────────────────────────
async def seller_products(request: web.Request) -> web.Response:
    user = _user(_init_data_from(request))
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    items = [_admin_card(p) for p in get_seller_products(owner)]
    items.sort(key=lambda c: c["id"] or 0, reverse=True)
    return web.json_response(items)


async def seller_create_product(request: web.Request) -> web.Response:
    init_data, payload, new_urls = await _parse_product_form(request)
    user = _user(init_data)
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    seller = get_seller(owner) or {}
    fields = _product_fields(payload, new_urls)
    if not fields.get("name"):
        return _err("no name", 400)
    product = {
        "seller_id": owner,
        "shop_name": seller.get("shop_name", ""),
        "city": seller.get("city", ""),
        "category": payload.get("category", "other"),
        **fields,
    }
    add_product(product)
    return web.json_response({"ok": True})


async def seller_update_product(request: web.Request) -> web.Response:
    try:
        pid = int(request.match_info["id"])
    except (KeyError, ValueError):
        return _err("bad id", 400)
    init_data, payload, new_urls = await _parse_product_form(request)
    user = _user(init_data)
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    p = get_product_by_id(pid)
    if not p:
        return _err("not found", 404)
    if p.get("seller_id") != owner:
        return _err("forbidden", 403)
    fields = _product_fields(payload, _final_photos(p, payload, new_urls))
    update_product(pid, fields)
    return web.json_response({"ok": True})


async def seller_delete_product(request: web.Request) -> web.Response:
    try:
        pid = int(request.match_info["id"])
    except (KeyError, ValueError):
        return _err("bad id", 400)
    user = _user((await _body(request)).get("initData")
                 or _init_data_from(request))
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    ok = delete_product(pid, owner)
    return web.json_response({"ok": ok})


# ─── SELLER: buyurtmalar ─────────────────────────────────────────────────────
def _order_view(o: dict) -> dict:
    return {
        "id": o.get("id"),
        "product_name": o.get("product_name", ""),
        "quantity": o.get("quantity", 1),
        "total": o.get("total", 0),
        "status": o.get("status", "pending"),
        "buyer_name": o.get("buyer_name", ""),
        "phone": o.get("phone", ""),
        "address": o.get("address", ""),
        "color": o.get("color", ""),
        "created_at": o.get("created_at", ""),
    }


async def seller_orders(request: web.Request) -> web.Response:
    user = _user(_init_data_from(request))
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    items = [_order_view(o) for o in get_seller_orders(owner)]
    items.sort(key=lambda o: o["id"] or 0, reverse=True)
    return web.json_response(items)


async def seller_order_status(request: web.Request) -> web.Response:
    try:
        oid = int(request.match_info["id"])
    except (KeyError, ValueError):
        return _err("bad id", 400)
    body = await _body(request)
    user = _user(body.get("initData"))
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    o = get_order_by_id(oid)
    if not o:
        return _err("not found", 404)
    if o.get("seller_id") != owner:
        return _err("forbidden", 403)
    status = str(body.get("status") or "")
    if status not in ALLOWED_ORDER_STATUS:
        return _err("bad status", 400)
    update_order_status(oid, status)
    _notify_buyer_status(o, status)
    return web.json_response({"ok": True})


def _notify_buyer_status(order: dict, status: str) -> None:
    """Xaridorga holat o'zgargani haqida (imkon bo'lsa) xabar yuboradi."""
    buyer_id = order.get("buyer_id")
    if not buyer_id:
        return
    labels = {
        "processing": "🔄 Tayyorlanmoqda",
        "shipped": "🚚 Yo'lga chiqdi",
        "delivered": "✅ Yetkazib berildi",
        "cancelled": "❌ Bekor qilindi",
    }
    if status not in labels:
        return
    text = (f"Buyurtmangiz #{order.get('id')} holati yangilandi:\n"
            f"{labels[status]}\n\n{order.get('product_name', '')}")
    try:
        import asyncio
        from app.bot.bot import bot
        asyncio.create_task(bot.send_message(int(buyer_id), text))
    except Exception:
        logger.exception("Xaridorga xabar yuborilmadi (#%s)", order.get("id"))


# ─── SELLER: do'kon ma'lumotlari ─────────────────────────────────────────────
async def seller_shop(request: web.Request) -> web.Response:
    user = _user(_init_data_from(request))
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    s = get_seller(owner) or {}
    return web.json_response({
        "shop_name": s.get("shop_name", ""),
        "full_name": s.get("full_name", ""),
        "phone": s.get("phone", ""),
        "card_number": s.get("card_number", ""),
        "city": s.get("city", ""),
        "is_owner": owner == int(user["id"]),
    })


async def seller_update_shop(request: web.Request) -> web.Response:
    body = await _body(request)
    user = _user(body.get("initData"))
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    fields = {}
    for k in ("shop_name", "phone", "card_number", "city"):
        if k in body:
            fields[k] = str(body.get(k) or "").strip()
    if not fields.get("shop_name", "x"):
        return _err("no shop name", 400)
    update_seller(owner, fields)
    return web.json_response({"ok": True})


# ─── SELLER: statistika ──────────────────────────────────────────────────────
async def seller_stats(request: web.Request) -> web.Response:
    user = _user(_init_data_from(request))
    if not user:
        return _err("auth", 401)
    owner = get_owner_id(int(user["id"]))
    if owner is None:
        return _err("forbidden", 403)
    orders = get_seller_orders(owner)
    by_status = {}
    revenue = 0
    for o in orders:
        st = o.get("status", "pending")
        by_status[st] = by_status.get(st, 0) + 1
        if st in ("paid", "processing", "shipped", "delivered"):
            revenue += to_int(o.get("total"), 0)
    products = get_seller_products(owner)
    active = sum(1 for p in products if _is_available(p))
    return web.json_response({
        "products": len(products),
        "active_products": active,
        "orders_total": len(orders),
        "by_status": by_status,
        "revenue": revenue,
    })


# ─── ADMIN: mahsulotlar (owner + sub-admin) ──────────────────────────────────
async def admin_products(request: web.Request) -> web.Response:
    user = _user(_init_data_from(request))
    if not user or not _is_admin(int(user["id"])):
        return _err("forbidden", 403)
    items = [_admin_card(p) for p in get_all_products()]
    items.sort(key=lambda c: c["id"] or 0, reverse=True)
    return web.json_response(items)


async def admin_sellers(request: web.Request) -> web.Response:
    """Mahsulot qo'shishda do'kon tanlash uchun ro'yxat."""
    user = _user(_init_data_from(request))
    if not user or not _is_admin(int(user["id"])):
        return _err("forbidden", 403)
    out = []
    for sid, s in get_sellers().items():
        out.append({"id": int(sid), "shop_name": s.get("shop_name", "")
                    or s.get("full_name", "") or sid,
                    "city": s.get("city", "")})
    out.sort(key=lambda x: x["shop_name"].lower())
    return web.json_response(out)


async def admin_create_product(request: web.Request) -> web.Response:
    init_data, payload, new_urls = await _parse_product_form(request)
    user = _user(init_data)
    if not user or not _is_admin(int(user["id"])):
        return _err("forbidden", 403)
    try:
        sid = int(payload.get("seller_id"))
    except (TypeError, ValueError):
        return _err("no seller", 400)
    seller = get_seller(sid)
    if not seller:
        return _err("seller not found", 404)
    fields = _product_fields(payload, new_urls)
    if not fields.get("name"):
        return _err("no name", 400)
    product = {
        "seller_id": sid,
        "shop_name": seller.get("shop_name", ""),
        "city": seller.get("city", ""),
        "category": payload.get("category", "other"),
        **fields,
    }
    add_product(product)
    return web.json_response({"ok": True})


async def admin_update_product(request: web.Request) -> web.Response:
    try:
        pid = int(request.match_info["id"])
    except (KeyError, ValueError):
        return _err("bad id", 400)
    init_data, payload, new_urls = await _parse_product_form(request)
    user = _user(init_data)
    if not user or not _is_admin(int(user["id"])):
        return _err("forbidden", 403)
    p = get_product_by_id(pid)
    if not p:
        return _err("not found", 404)
    fields = _product_fields(payload, _final_photos(p, payload, new_urls))
    update_product(pid, fields)
    return web.json_response({"ok": True})


async def admin_delete_product_ep(request: web.Request) -> web.Response:
    try:
        pid = int(request.match_info["id"])
    except (KeyError, ValueError):
        return _err("bad id", 400)
    user = _user((await _body(request)).get("initData")
                 or _init_data_from(request))
    if not user or not _is_admin(int(user["id"])):
        return _err("forbidden", 403)
    ok = admin_delete_product(pid)
    return web.json_response({"ok": ok})
