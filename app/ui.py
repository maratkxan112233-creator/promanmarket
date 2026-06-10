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


# Mahsulot nomidagi kalit so'z → emoji (lotin va kirill yozuvlari).
# Tartib muhim: aniqroq so'zlar oldinroq turadi, birinchi mos kelgani olinadi.
_NAME_EMOJI = [
    (("kir yuvish", "стирал"),                            "🧺"),
    # "vintel/ventel" — keng tarqalgan xato yozilishlar ham qabul qilinadi
    (("ventil", "vintel", "ventel", "вентил"),            "🌀"),
    (("kondits", "kondis", "кондиц"),                     "❄️"),
    (("muzlatgich", "xolodil", "холодильник", "morozil"), "🧊"),
    (("televizor", "телевизор"),                          "📺"),
    (("kuller", "кулер", "dispenser", "диспенсер"),       "🚰"),
    (("mikrovoln", "mikroto", "микроволн"),               "♨️"),
    (("plita", "плита", "pech", "духовка", "oven"),       "🍳"),
    (("chang yutgich", "changyutgich", "pyleso", "пылесос"), "🧹"),
    (("choynak", "чайник", "termopot"),                   "🫖"),
    (("blender", "mikser", "блендер", "миксер"),          "🥣"),
    (("telefon", "smartfon", "смартфон", "iphone", "redmi"), "📱"),
    (("noutbuk", "kompyuter", "ноутбук", "компьютер"),    "💻"),
    (("planshet", "планшет", "ipad"),                     "📲"),
    (("quloqchin", "naushnik", "наушник"),                "🎧"),
    (("kolonka", "колонка", "muzika", "speaker"),         "🔊"),
    (("kamera", "камера"),                                "📷"),
    (("soat", "часы", "watch"),                           "⌚"),
    (("isitgich", "obogrev", "обогрев"),                  "🔥"),
    (("dazmol", "утюг"),                                  "👔"),
    (("velosiped", "велосипед"),                          "🚲"),
]


def product_emoji(p) -> str:
    """Mahsulot nomiga qarab avtomatik emoji.

    Nomda kalit so'z topilmasa — bo'lim emojisi, u ham bo'lmasa 📦.
    `p` — mahsulot dict'i yoki shunchaki nom (str).
    """
    name = p.get("name", "") if isinstance(p, dict) else (p or "")
    low = str(name).lower()
    for keys, emoji in _NAME_EMOJI:
        if any(k in low for k in keys):
            return emoji
    if isinstance(p, dict):
        # Bo'lim nomining birinchi qismi — uning emojisi.
        return category_label(product_category(p)).split()[0]
    return "📦"


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
