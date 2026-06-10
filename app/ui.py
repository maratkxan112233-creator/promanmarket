"""Bot ko'rinishi uchun umumiy yordamchilar.

Butun bot bo'ylab xabar va tugmalar bir xil, toza, zamonaviy ko'rinishi uchun
shu yerda jamlangan. Bu yerni o'zgartirsangiz — hamma joyda bir vaqtda o'zgaradi.
"""

# Ingichka ajratgich (xabar bo'limlarini toza ajratish uchun).
DIVIDER = "──────────────"

# Mahsulot bo'limlari (kategoriyalari): (kod, ko'rinadigan nom).
# Kod — diskda (products.json) saqlanadi, nom — foydalanuvchiga ko'rinadi.
# Eski (bo'limsiz) mahsulotlar avtomatik "other" hisoblanadi.
CATEGORIES = [
    ("tv",      "📺 Televizorlar"),
    ("washer",  "🧺 Kir yuvish mashinalari"),
    ("fridge",  "🧊 Muzlatgichlar"),
    ("stove",   "🍳 Pishirish texnikasi"),
    ("aircon",  "❄️ Konditsionerlar"),
    ("phone",   "📱 Telefonlar"),
    ("other",   "📦 Boshqa"),
]

_CATEGORY_MAP = dict(CATEGORIES)


def category_label(code) -> str:
    """Bo'lim kodi bo'yicha ko'rinadigan nomni qaytaradi."""
    return _CATEGORY_MAP.get(code or "other", _CATEGORY_MAP["other"])


def product_category(p: dict) -> str:
    """Mahsulotning bo'lim kodi (eski mahsulotlarda — 'other')."""
    code = (p or {}).get("category")
    return code if code in _CATEGORY_MAP else "other"


def money(value) -> str:
    """Narxni bir xil ko'rinishda formatlash: 150 000 so'm (probel bilan).

    Matnli narx ("150 000", "150,000") kelsa ham to'g'ri ishlaydi.
    """
    if isinstance(value, str):
        value = value.replace(" ", "").replace(",", "").replace("'", "")
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        n = 0
    return f"{n:,}".replace(",", " ") + " so'm"


def divider() -> str:
    """Ingichka ajratgich qatori."""
    return DIVIDER


def title(emoji: str, text: str) -> str:
    """Bir xil sarlavha uslubi: emoji + qalin matn."""
    return f"{emoji} <b>{text}</b>"
