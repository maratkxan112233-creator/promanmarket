import json
import os
from typing import Any
from datetime import datetime

DATA_DIR = os.getenv("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)

SELLERS_FILE      = f"{DATA_DIR}/sellers.json"
APPLICATIONS_FILE = f"{DATA_DIR}/applications.json"
PRODUCTS_FILE     = f"{DATA_DIR}/products.json"
ORDERS_FILE       = f"{DATA_DIR}/orders.json"
REVIEWS_FILE      = f"{DATA_DIR}/reviews.json"
USERS_FILE        = f"{DATA_DIR}/users.json"
ADMINS_FILE       = f"{DATA_DIR}/admins.json"
COURIERS_FILE     = f"{DATA_DIR}/couriers.json"
AUDIT_FILE        = f"{DATA_DIR}/audit.json"
CITIES_FILE       = f"{DATA_DIR}/cities.json"
VIEW_STATE_FILE   = f"{DATA_DIR}/view_state.json"
FAVORITES_FILE    = f"{DATA_DIR}/favorites.json"
BLOCKED_FILE      = f"{DATA_DIR}/blocked.json"
PROMOS_FILE       = f"{DATA_DIR}/promos.json"

DEFAULT_CITIES = ["Olmaliq", "Angren", "Bekobod", "Ohangaron", "Chirchiq", "Yangiyo'l", "Toshkent"]

# Xotira keshi: har bir o'qishda diskdan JSON parse qilmaslik uchun.
# path -> (mtime_ns, data). Fayl mtime o'zgargandagina qayta o'qiymiz, shuning
# uchun boshqa thread/process (HTTP server) fayl yozsa ham eskirgan ma'lumot
# qaytmaydi. Bu bot javobini sezilarli tezlashtiradi (N+1 takroriy o'qishlar).
_CACHE: dict[str, tuple[int, Any]] = {}


def _read(path: str) -> Any:
    if not os.path.exists(path):
        return {}
    try:
        mtime = os.stat(path).st_mtime_ns
        cached = _CACHE.get(path)
        if cached is not None and cached[0] == mtime:
            return cached[1]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CACHE[path] = (mtime, data)
        return data
    except (json.JSONDecodeError, OSError):
        # Fayl buzilgan yoki bir vaqtda yozilayotgan bo'lsa — bo'sh qiymat qaytaramiz
        return {}

def _write(path: str, data: Any):
    # Atomik yozish: avval vaqtinchalik faylga yozib, keyin o'rnini almashtiramiz.
    # Bu HTTP server (boshqa thread) yarim yozilgan JSON'ni o'qib qolishining oldini oladi.
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        # indent'siz yozamiz: fayl kichik bo'ladi va yozish tezroq (event loop'ni
        # qisqaroq bloklaydi).
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)
    # Keshni yangi ma'lumot va yangi mtime bilan yangilaymiz (keyingi o'qish tez bo'lsin).
    try:
        _CACHE[path] = (os.stat(path).st_mtime_ns, data)
    except OSError:
        _CACHE.pop(path, None)


# ─── Applications ────────────────────────────────────────────────────────────
def get_applications() -> dict:
    return _read(APPLICATIONS_FILE)

def save_application(user_id: int, data: dict):
    apps = get_applications()
    apps[str(user_id)] = data
    _write(APPLICATIONS_FILE, apps)

def get_application(user_id: int) -> dict | None:
    return get_applications().get(str(user_id))

def update_application_status(user_id: int, status: str):
    apps = get_applications()
    if str(user_id) in apps:
        apps[str(user_id)]["status"] = status
        _write(APPLICATIONS_FILE, apps)


# ─── Sellers ─────────────────────────────────────────────────────────────────
def get_sellers() -> dict:
    return _read(SELLERS_FILE)

def add_seller(user_id: int, data: dict):
    sellers = get_sellers()
    sellers[str(user_id)] = data
    _write(SELLERS_FILE, sellers)

def is_seller(user_id: int) -> bool:
    return str(user_id) in get_sellers()

def get_seller(user_id: int) -> dict | None:
    return get_sellers().get(str(user_id))

def update_seller(user_id: int, fields: dict):
    sellers = get_sellers()
    if str(user_id) in sellers:
        sellers[str(user_id)].update(fields)
        _write(SELLERS_FILE, sellers)

def delete_seller(user_id: int):
    sellers = get_sellers()
    sellers.pop(str(user_id), None)
    _write(SELLERS_FILE, sellers)


# ─── Yordamchi sellerlar ─────────────────────────────────────────────────────
def get_owner_id(user_id: int) -> int | None:
    """O'zi seller bo'lsa — o'z id'si; yordamchi bo'lsa — do'kon egasining id'si."""
    sellers = get_sellers()
    if str(user_id) in sellers:
        return user_id
    for sid, s in sellers.items():
        if user_id in (s.get("assistants") or []):
            return int(sid)
    return None

def get_shop_seller(user_id: int) -> dict | None:
    """Ega yoki yordamchi uchun do'kon egasining yozuvini qaytaradi."""
    owner = get_owner_id(user_id)
    return get_seller(owner) if owner is not None else None

def is_shop_member(user_id: int) -> bool:
    return get_owner_id(user_id) is not None

def get_assistants(owner_id: int) -> list[int]:
    seller = get_seller(owner_id)
    return (seller or {}).get("assistants") or []

def add_assistant(owner_id: int, assistant_id: int) -> bool:
    assistants = get_assistants(owner_id)
    if assistant_id in assistants:
        return False
    assistants.append(assistant_id)
    update_seller(owner_id, {"assistants": assistants})
    return True

def remove_assistant(owner_id: int, assistant_id: int) -> bool:
    assistants = get_assistants(owner_id)
    if assistant_id not in assistants:
        return False
    assistants.remove(assistant_id)
    update_seller(owner_id, {"assistants": assistants})
    return True

def shop_notify_ids(owner_id: int) -> list[int]:
    """Buyurtma xabarlari boradigan barcha id'lar: ega + yordamchilar."""
    return [owner_id, *get_assistants(owner_id)]


def normalize_phone(phone) -> str:
    """Raqamdan faqat sonlarni qoldirib, oxirgi 9 tasini qaytaradi
    (+998 90 123-45-67 ham, 901234567 ham bir xil bo'ladi)."""
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    return digits[-9:] if len(digits) >= 9 else digits

def find_user_id_by_phone(phone) -> int | None:
    """Telefon raqami bo'yicha foydalanuvchi id'sini topadi.
    Qidiruv tartibi: users → buyurtmalar (oxirgilari avval) → arizalar → sellerlar."""
    target = normalize_phone(phone)
    if len(target) < 9:
        return None
    for uid, u in get_users().items():
        if normalize_phone(u.get("phone")) == target:
            return int(uid)
    for o in reversed(get_orders()):
        if o.get("buyer_id") and normalize_phone(o.get("phone")) == target:
            return int(o["buyer_id"])
    for uid, a in get_applications().items():
        if normalize_phone(a.get("phone")) == target:
            return int(uid)
    for sid, s in get_sellers().items():
        if normalize_phone(s.get("phone")) == target:
            return int(sid)
    return None


# ─── Users ───────────────────────────────────────────────────────────────────
def get_users() -> dict:
    return _read(USERS_FILE)

def register_user(user_id: int, data: dict):
    users = get_users()
    if str(user_id) not in users:
        users[str(user_id)] = data
        _write(USERS_FILE, users)

def delete_user(user_id: int):
    users = get_users()
    users.pop(str(user_id), None)
    _write(USERS_FILE, users)

def get_user(user_id: int) -> dict | None:
    return get_users().get(str(user_id))

def set_user_field(user_id: int, field: str, value):
    users = get_users()
    u = users.get(str(user_id), {})
    u[field] = value
    users[str(user_id)] = u
    _write(USERS_FILE, users)


# ─── Istaklar (sevimli mahsulotlar, ❤️) ─────────────────────────────────────
def get_favorites(user_id: int) -> list:
    """Foydalanuvchining saqlangan mahsulot id'lari ro'yxati."""
    favs = _read(FAVORITES_FILE)
    return [int(x) for x in favs.get(str(user_id), [])] if isinstance(favs, dict) else []

def is_favorite(user_id: int, product_id: int) -> bool:
    return int(product_id) in get_favorites(user_id)

def toggle_favorite(user_id: int, product_id: int) -> bool:
    """Saqlangan bo'lsa olib tashlaydi, bo'lmasa qo'shadi. True = endi saqlangan."""
    favs = _read(FAVORITES_FILE)
    if not isinstance(favs, dict):
        favs = {}
    lst = [int(x) for x in favs.get(str(user_id), [])]
    pid = int(product_id)
    if pid in lst:
        lst.remove(pid)
        added = False
    else:
        lst.append(pid)
        added = True
    favs[str(user_id)] = lst
    _write(FAVORITES_FILE, favs)
    return added


# ─── Botni bloklaganlar ──────────────────────────────────────────────────────
# Foydalanuvchi botni bloklaganda Telegram "my_chat_member" yangilanishini
# yuboradi (yangi holat = "kicked"). Shu paytda bu yerga yozib qo'yamiz, admin
# panelda "🚫 Bloklaganlar" bo'limida ko'rinadi. Blokdan chiqarsa — o'chiriladi.
# user_id (str) -> {"user_id", "name", "username", "blocked_at"}
def get_blocked() -> dict:
    data = _read(BLOCKED_FILE)
    return data if isinstance(data, dict) else {}

def mark_blocked(user_id: int, data: dict):
    blocked = get_blocked()
    data["blocked_at"] = datetime.now().isoformat()
    blocked[str(user_id)] = data
    _write(BLOCKED_FILE, blocked)

def unmark_blocked(user_id: int) -> bool:
    blocked = get_blocked()
    if str(user_id) in blocked:
        del blocked[str(user_id)]
        _write(BLOCKED_FILE, blocked)
        return True
    return False

def is_blocked(user_id: int) -> bool:
    return str(user_id) in get_blocked()


# ─── Shaharlar (tuman/shahar darajasi) ───────────────────────────────────────
def get_cities() -> list:
    data = _read(CITIES_FILE)
    if not data or not isinstance(data, list):
        _write(CITIES_FILE, DEFAULT_CITIES)
        return list(DEFAULT_CITIES)
    return data

def add_city(name: str) -> bool:
    name = name.strip()
    cities = get_cities()
    if name and name not in cities:
        cities.append(name)
        _write(CITIES_FILE, cities)
        return True
    return False

def remove_city(name: str) -> bool:
    cities = get_cities()
    if name in cities:
        cities.remove(name)
        _write(CITIES_FILE, cities)
        return True
    return False


# ─── Products ────────────────────────────────────────────────────────────────
def to_int(value, default: int = 0) -> int:
    """Narxni xavfsiz butun songa o'giradi.
    Eski/buzilgan ma'lumotda narx matn ("150 000", "150,000") bo'lib qolgan
    bo'lishi mumkin — `f"{price:,}"` formatlash bunda crash beradi. Shuning uchun
    o'qishda har doim int'ga keltiramiz."""
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        cleaned = value.replace(" ", "").replace(",", "").replace("'", "")
        try:
            return int(float(cleaned))
        except (ValueError, TypeError):
            return default
    return default

def _normalize_product(p: dict) -> dict:
    """Mahsulot narxlarini int'ga keltiradi (ko'rsatishda crash bo'lmasligi uchun)."""
    if isinstance(p, dict):
        p["price"] = to_int(p.get("price"), 0)
        if p.get("old_price") is not None:
            p["old_price"] = to_int(p.get("old_price"), 0)
    return p

def get_all_products() -> list:
    data = _read(PRODUCTS_FILE)
    if not isinstance(data, list):
        return []
    return [_normalize_product(p) for p in data if isinstance(p, dict)]

def get_seller_products(seller_id: int) -> list:
    return [p for p in get_all_products() if p.get("seller_id") == seller_id]

def get_product_by_id(product_id: int) -> dict | None:
    for p in get_all_products():
        if p.get("id") == product_id:
            return p
    return None

def product_photos(p: dict) -> list:
    """Mahsulot rasmlari ro'yxati (yangi 'photos' yoki eski 'photo' bilan moslik)."""
    if not p:
        return []
    photos = p.get("photos")
    if isinstance(photos, list) and photos:
        return [x for x in photos if x]
    one = p.get("photo")
    return [one] if one else []

def product_video(p: dict) -> str | None:
    """Mahsulotning qisqa video file_id'si (bo'lsa). Yo'q bo'lsa None."""
    if not p:
        return None
    v = p.get("video")
    return v if v else None

def add_product(product: dict):
    products = get_all_products()
    product["id"] = (max((p["id"] for p in products), default=0) + 1)
    products.append(product)
    _write(PRODUCTS_FILE, products)

def save_products(products: list):
    """Mahsulotlar ro'yxatini to'liq saqlaydi (bitta yozish).
    Ko'p mahsulotni birvarakayiga qo'shish/yangilashda har biriga alohida fayl
    yozmaslik uchun — masalan seed (startup) ancha tezlashadi."""
    _write(PRODUCTS_FILE, products)

def next_product_id() -> int:
    """Keyingi bo'sh mahsulot id'si (bulk qo'shishda foydali)."""
    return max((p["id"] for p in get_all_products()), default=0) + 1

def update_product(product_id: int, fields: dict):
    products = get_all_products()
    for p in products:
        if p["id"] == product_id:
            p.update(fields)
    _write(PRODUCTS_FILE, products)

def delete_product(product_id: int, seller_id: int) -> bool:
    products = get_all_products()
    new = [p for p in products if not (p["id"] == product_id and p["seller_id"] == seller_id)]
    if len(new) < len(products):
        _write(PRODUCTS_FILE, new)
        return True
    return False

def admin_delete_product(product_id: int) -> bool:
    products = get_all_products()
    new = [p for p in products if p["id"] != product_id]
    if len(new) < len(products):
        _write(PRODUCTS_FILE, new)
        return True
    return False

def delete_all_products() -> int:
    """Hamma mahsulotni o'chiradi. O'chirilgan sonni qaytaradi."""
    n = len(get_all_products())
    _write(PRODUCTS_FILE, [])
    return n

def search_products(query: str) -> list:
    """Fuzzy search: har bir so'z alohida tekshiriladi"""
    query = query.lower().strip()
    words = query.split()
    results = []
    for p in get_all_products():
        target = f"{p.get('name','')} {p.get('description','')} {p.get('shop_name','')}".lower()
        score = sum(1 for w in words if w in target)
        if score > 0:
            results.append((score, p))
    results.sort(key=lambda x: x[0], reverse=True)
    return [p for _, p in results]


# ─── Zaxira (ombordagi son) ──────────────────────────────────────────────────
# Mahsulotning 'stock' maydoni: butun son — omborda nechta bor. None bo'lsa
# (yoki maydon yo'q bo'lsa) — sotuvchi hisob yuritmaydi, cheksiz deb qaraladi.
def product_stock(p: dict):
    """Mahsulot zaxirasi. None — cheksiz (hisob yuritilmaydi)."""
    if not p:
        return None
    s = p.get("stock")
    return None if s is None else to_int(s, 0)

def decrement_stock(product_id: int, qty: int) -> None:
    """Zaxirani qty taga kamaytiradi. Cheksiz (stock=None) bo'lsa tegmaydi.
    0 ga yetsa — mahsulot avtomatik 'tugagan' deb belgilanadi."""
    products = get_all_products()
    changed = False
    for p in products:
        if p.get("id") == product_id and p.get("stock") is not None:
            new = max(to_int(p.get("stock"), 0) - max(int(qty), 0), 0)
            p["stock"] = new
            if new == 0:
                p["is_finished"] = True
            changed = True
    if changed:
        _write(PRODUCTS_FILE, products)


# ─── Orders ──────────────────────────────────────────────────────────────────
def _normalize_order(o: dict) -> dict:
    """Buyurtma summalarini int'ga keltiradi (formatlashda crash bo'lmasligi uchun)."""
    if isinstance(o, dict):
        for k in ("total", "prepay", "commission"):
            if o.get(k) is not None:
                o[k] = to_int(o.get(k), 0)
    return o

def get_orders() -> list:
    data = _read(ORDERS_FILE)
    if not isinstance(data, list):
        return []
    return [_normalize_order(o) for o in data if isinstance(o, dict)]

def save_order(order: dict):
    orders = get_orders()
    order["id"] = max((o["id"] for o in orders), default=0) + 1
    order["created_at"] = datetime.now().isoformat()
    orders.append(order)
    _write(ORDERS_FILE, orders)
    return order["id"]

def get_order_by_id(order_id: int) -> dict | None:
    for o in get_orders():
        if o.get("id") == order_id:
            return o
    return None

def update_order_fields(order_id: int, fields: dict):
    orders = get_orders()
    for o in orders:
        if o["id"] == order_id:
            o.update(fields)
            o["updated_at"] = datetime.now().isoformat()
    _write(ORDERS_FILE, orders)

def update_order_status(order_id: int, status: str):
    orders = get_orders()
    for o in orders:
        if o["id"] == order_id:
            o["status"] = status
            o["updated_at"] = datetime.now().isoformat()
    _write(ORDERS_FILE, orders)

def get_buyer_orders(user_id: int) -> list:
    return [o for o in get_orders() if o.get("buyer_id") == user_id]

def get_seller_orders(seller_id: int) -> list:
    return [o for o in get_orders() if o.get("seller_id") == seller_id]


# ─── Reviews ─────────────────────────────────────────────────────────────────
def get_reviews() -> list:
    data = _read(REVIEWS_FILE)
    return data if isinstance(data, list) else []

def add_review(review: dict):
    reviews = get_reviews()
    review["id"] = max((r["id"] for r in reviews), default=0) + 1
    review["created_at"] = datetime.now().isoformat()
    reviews.append(review)
    _write(REVIEWS_FILE, reviews)

def get_seller_reviews(seller_id: int) -> list:
    return [r for r in get_reviews() if r.get("seller_id") == seller_id]

def has_order_review(order_id: int) -> bool:
    """Bu buyurtma uchun allaqachon baho berilganmi (takror baholashning oldini
    olish — bir buyurtma faqat bir marta baholanadi)."""
    return any(r.get("order_id") == order_id for r in get_reviews())

def get_seller_rating(seller_id: int) -> tuple[float, int]:
    reviews = get_seller_reviews(seller_id)
    if not reviews:
        return 0.0, 0
    avg = sum(r["stars"] for r in reviews) / len(reviews)
    return round(avg, 1), len(reviews)


# ─── Promo-kodlar (chegirma) ─────────────────────────────────────────────────
# code (UPPER) -> {"code", "percent", "limit", "used", "active", "created_at"}
# limit = 0 → cheksiz ishlatish mumkin. percent → mahsulot narxidan chegirma %.
def _norm_code(code: str) -> str:
    return "".join(str(code or "").split()).upper()

def get_promos() -> dict:
    data = _read(PROMOS_FILE)
    return data if isinstance(data, dict) else {}

def get_promo(code: str) -> dict | None:
    return get_promos().get(_norm_code(code))

def add_promo(code: str, percent: int, limit: int = 0) -> bool:
    """Yangi promo-kod qo'shadi. Allaqachon mavjud bo'lsa False qaytaradi."""
    code = _norm_code(code)
    if not code:
        return False
    promos = get_promos()
    if code in promos:
        return False
    promos[code] = {
        "code":    code,
        "percent": max(1, min(int(percent), 90)),
        "limit":   max(int(limit), 0),
        "used":    0,
        "active":  True,
        "created_at": datetime.now().isoformat(),
    }
    _write(PROMOS_FILE, promos)
    return True

def delete_promo(code: str) -> bool:
    promos = get_promos()
    if _norm_code(code) in promos:
        del promos[_norm_code(code)]
        _write(PROMOS_FILE, promos)
        return True
    return False

def validate_promo(code: str) -> dict | None:
    """Kod yaroqli (faol va limit tugamagan) bo'lsa promo yozuvini qaytaradi,
    aks holda None."""
    p = get_promo(code)
    if not p or not p.get("active", True):
        return None
    limit = int(p.get("limit", 0))
    if limit and int(p.get("used", 0)) >= limit:
        return None
    return p

def use_promo(code: str) -> None:
    """Promo ishlatilganini belgilaydi (used +1). Limitga yetsa o'chmaydi —
    validate_promo keyingi safar None qaytaradi."""
    promos = get_promos()
    code = _norm_code(code)
    if code in promos:
        promos[code]["used"] = int(promos[code].get("used", 0)) + 1
        _write(PROMOS_FILE, promos)


# ─── Sub-adminlar ────────────────────────────────────────────────────────────
def get_admins() -> dict:
    return _read(ADMINS_FILE)

def add_admin(user_id: int, data: dict):
    admins = get_admins()
    admins[str(user_id)] = data
    _write(ADMINS_FILE, admins)

def remove_admin(user_id: int) -> bool:
    admins = get_admins()
    if str(user_id) in admins:
        del admins[str(user_id)]
        _write(ADMINS_FILE, admins)
        return True
    return False

def is_sub_admin(user_id: int) -> bool:
    return str(user_id) in get_admins()


# ─── Kurierlar ───────────────────────────────────────────────────────────────
# To'lov (10% oldindan) tasdiqlangan yetkazib berish zakazlari shu kurierlarga
# yuboriladi. user_id (str) -> {"user_id": int, "name": str}
def get_couriers() -> dict:
    data = _read(COURIERS_FILE)
    return data if isinstance(data, dict) else {}

def add_courier(user_id: int, data: dict):
    couriers = get_couriers()
    couriers[str(user_id)] = data
    _write(COURIERS_FILE, couriers)

def remove_courier(user_id) -> bool:
    couriers = get_couriers()
    if str(user_id) in couriers:
        del couriers[str(user_id)]
        _write(COURIERS_FILE, couriers)
        return True
    return False

def is_courier(user_id: int) -> bool:
    return str(user_id) in get_couriers()


# ─── Audit jurnali (kim nima qildi) ──────────────────────────────────────────
def get_audit() -> list:
    data = _read(AUDIT_FILE)
    return data if isinstance(data, list) else []

def add_audit(entry: dict):
    log = get_audit()
    entry["id"] = max((e.get("id", 0) for e in log), default=0) + 1
    entry["created_at"] = datetime.now().isoformat()
    log.append(entry)
    # Jurnal cheksiz o'smasin: faqat oxirgi 500 yozuv saqlanadi, aks holda har
    # yozishda butun fayl qayta yoziladi va vaqt o'tib sekinlashadi.
    _write(AUDIT_FILE, log[-500:])


# ─── Ko'rish holati (chatda hozir ko'rsatilgan mahsulot xabarlari) ────────────
# chat_id -> [message_id, ...]. FAQAT XOTIRADA saqlanadi (diskka yozilmaydi).
# Avval har mahsulot ko'rilganda butun view_state.json diskka yoziatilardi — bu
# eng tez-tez bajariladigan amal bo'lgani uchun event loop'ni bloklab, botni
# sekinlashtirardi. Endi xotirada — diskka yozish yo'q, mahsulot ko'rish bir
# necha barobar tez. Yagona farq: bot qayta ishga tushsa, undan OLDIN ko'rsatilgan
# mahsulot xabarlari avtomatik o'chmaydi (juda kichik, sezilmas farq).
_VIEW_MSGS: dict[int, list] = {}

def get_view_msgs(chat_id: int) -> list:
    return list(_VIEW_MSGS.get(chat_id, []))

def set_view_msgs(chat_id: int, ids: list):
    _VIEW_MSGS[chat_id] = list(ids)

def pop_view_msgs(chat_id: int) -> list:
    return _VIEW_MSGS.pop(chat_id, [])

def pop_all_view_msgs() -> dict:
    """Barcha chatlardagi ko'rsatilgan mahsulot xabar id'larini qaytaradi va
    xotirani tozalaydi. Restart paytida chatlarni tozalashda (ko'rilgan mahsulot
    kartochkalarini o'chirishda) ishlatiladi."""
    data = dict(_VIEW_MSGS)
    _VIEW_MSGS.clear()
    return data


# ─── Restart: xaridor tarixini tozalash ──────────────────────────────────────
def reset_buyer_data() -> dict:
    """Admin "Restart" bosganda chaqiriladi: xaridorlarning buyurtma, sharh
    (reyting) va profil tarixini to'liq tozalaydi — bot "bo'sh" holatga qaytadi.

    SAQLANADI: ❤️ istaklar (favorites), do'konlar (sellers), mahsulotlar
    (products), adminlar, kurierlar, shaharlar. O'chirilgan yozuvlar sonini
    qaytaradi (hisobot uchun)."""
    counts = {
        "orders":  len(get_orders()),
        "reviews": len(get_reviews()),
        "users":   len(get_users()),
    }
    _write(ORDERS_FILE, [])
    _write(REVIEWS_FILE, [])
    _write(USERS_FILE, {})
    _VIEW_MSGS.clear()
    return counts
