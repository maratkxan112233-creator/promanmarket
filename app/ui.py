"""Bot ko'rinishi uchun umumiy yordamchilar.

Butun bot bo'ylab xabar va tugmalar bir xil, toza, zamonaviy ko'rinishi uchun
shu yerda jamlangan. Bu yerni o'zgartirsangiz — hamma joyda bir vaqtda o'zgaradi.
"""

import re

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


# Mahsulot guruhlari: (kalit so'zlar, emoji, guruh nomi). Lotin + kirill + keng
# tarqalgan xato yozilishlar. TARTIB MUHIM: bu ham katalogdagi kategoriya
# ketma-ketligini belgilaydi, ham birinchi mos kelgan guruh tanlanadi —
# shuning uchun aniqroq/torroq so'zlar oldinroq turadi (masalan "kir yuvish"
# "mashina" dan oldin, aks holda mashina guruhiga tushib ketardi).
_PRODUCT_GROUPS = [
    (("kir yuvish", "стирал", "yarim avtomat", "avtomat kir"),          "🧺", "Kir yuvish mashinalari"),
    (("kondits", "kondis", "кондиц", "split", "spilit"),                "❄️", "Konditsionerlar"),
    (("muzlatgich", "xolodil", "холодильник", "morozil", "sovutkich", "vitrina sovut"), "🧊", "Muzlatgich va sovutgichlar"),
    (("televizor", "телевизор", "smart tv"),                            "📺", "Televizorlar"),
    (("mikrovoln", "mikroto", "микроволн"),                             "♨️", "Mikroto'lqin pechlar"),
    (("gaz plita", "plita", "плита", "pech", "духовка", "oven", "gaz panel", "pishirish panel"), "🍳", "Plita va pishirish"),
    (("chang yutgich", "changyutgich", "pyleso", "пылесос"),            "🧹", "Chang yutgichlar"),
    (("kuller", "кулер", "dispenser", "диспенсер", "suv sovutgich", "suv apparat"), "🚰", "Suv kulerlari"),
    (("choynak", "чайник", "termopot"),                                 "🫖", "Choynak va termopotlar"),
    (("aerogril", "multipech", "multivark", "toster", "gril", "sendvich", "shashlik",
      "kombayn", "sharbat", "kofe", "qahva", "vafli", "blinchik", "meva quritgich",
      "maydalagich", "vakuumator"),                                     "🥘", "Oshxona texnikasi"),
    (("qozon", "kastryul", "kostryul", "mantovarka", "mantiqasqon", "qasqon",
      "skovorod", "wok", "chinni", "servis", "pichoq", "menajnitsa", "keskich",
      "idish"),                                                         "🍽", "Idish-tovoq va qozonlar"),
    (("blender", "mikser", "блендер", "миксер"),                        "🥣", "Blender va mikserlar"),
    (("dazmol", "утюг"),                                                "👔", "Dazmollar"),
    (("ventil", "vintel", "ventel", "вентил"),                          "🌀", "Ventilyatorlar"),
    (("isitgich", "obogrev", "обогрев", "obogrevatel"),                 "🔥", "Isitgichlar"),
    (("soch quritgich", "fen", "фен", "kir quritgich", "quritgich"),    "💨", "Quritgichlar"),
    (("tarozi", "весы", "scale"),                                       "⚖️", "Tarozilar"),
    (("telefon", "smartfon", "смартфон", "iphone", "redmi"),            "📱", "Telefonlar"),
    (("noutbuk", "kompyuter", "ноутбук", "компьютер", "laptop"),        "💻", "Noutbuk va kompyuterlar"),
    (("planshet", "планшет", "ipad"),                                   "📲", "Planshetlar"),
    (("quloqchin", "aquloqchin", "naushnik", "наушник", "tarjimon"),    "🎧", "Quloqchinlar"),
    (("kolonka", "kalonka", "колонка", "muzika", "speaker"),            "🔊", "Kolonkalar"),
    (("kamera", "камера"),                                              "📷", "Kameralar"),
    (("soat", "часы", "watch"),                                         "⌚", "Soatlar"),
    (("velosiped", "велосипед"),                                        "🚲", "Velosipedlar"),
    (("elektromobil", "tolokar", "minadigan mashina", "bolalar mashina", "akkumulyatorli mashina", "elektr mashina", "jip", "jeep"), "🚗", "Bolalar mashinalari"),
    (("aravacha", "kolyaska", "коляска", "stroller"),                   "👶", "Bolalar aravachalari"),
    (("basseyn", "bassen", "бассейн", "pool"),                          "🏊", "Basseynlar"),
    (("trimmer", "trimo", "триммер"),                                   "✂️", "Trimmerlar"),
    (("atirgul", "atir gul", "роза", "gullar", "buket"),               "🌸", "Gullar"),
    (("organayzer", "органайзер", "organizer"),                         "🗂️", "Organayzerlar"),
    (("kabel", "кабель", "зарядка", "charger", "quvvatlash"),           "🔌", "Kabel va quvvatlagichlar"),
    (("etajerka", "stellaj", "polka", "стеллаж"),                       "🪜", "Javon va etajerkalar"),
    (("chivin to'r", "chivin tor", "deraza to'r", "setka"),            "🦟", "Chivin to'rlari"),
]

# Guruhga mos kelmaganlar uchun (eng oxirda turadi).
_OTHER_LABEL = "Boshqa mahsulotlar"


def _match_group(p):
    """Mahsulotga mos guruhni (kalitlar, emoji, nom) qaytaradi yoki None."""
    name = p.get("name", "") if isinstance(p, dict) else (p or "")
    low = str(name).lower()
    for g in _PRODUCT_GROUPS:
        if any(k in low for k in g[0]):
            return g
    return None


def product_emoji(p) -> str:
    """Mahsulot nomiga qarab mos emoji. Topilmasa — bo'lim emojisi, u ham
    bo'lmasa 📦. `p` — mahsulot dict'i yoki nom (str)."""
    g = _match_group(p)
    if g:
        return g[1]
    if isinstance(p, dict):
        return category_label(product_category(p)).split()[0]
    return "📦"


def product_group_label(p) -> str:
    """Mahsulot guruhining ko'rinadigan nomi (katalog sarlavhalari uchun)."""
    g = _match_group(p)
    return g[2] if g else _OTHER_LABEL


def product_groups() -> list[tuple[str, str]]:
    """(emoji, nom) juftliklari — katalog kategoriyalari tartibida.
    Oxirgi element — guruhga mos kelmaganlar ("Boshqa mahsulotlar");
    uning indeksi product_sort_key() qaytaradigan len(_PRODUCT_GROUPS) bilan mos."""
    return [(g[1], g[2]) for g in _PRODUCT_GROUPS] + [("📦", _OTHER_LABEL)]


def product_sort_key(p) -> int:
    """Mahsulotni kategoriya tartibiga soladi (katalog guruhlash uchun).
    Bir guruhdagilar yonma-yon keladi, aralash chiqmaydi. Topilmasa — oxirga."""
    name = p.get("name", "") if isinstance(p, dict) else (p or "")
    low = str(name).lower()
    for i, g in enumerate(_PRODUCT_GROUPS):
        if any(k in low for k in g[0]):
            return i
    return len(_PRODUCT_GROUPS)


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


def normalize_uz_phone(raw) -> str | None:
    """Telefonni +998XXXXXXXXX ko'rinishiga keltiradi; yaroqsiz bo'lsa None.

    Qabul qilinadigan shakllar: +998 90 123 45 67, 998901234567, 90-123-45-67.
    """
    if not raw:
        return None
    digits = re.sub(r"[\s\-\(\)\.\+]", "", str(raw).strip())
    if not digits.isdigit():
        return None
    if len(digits) == 12 and digits.startswith("998"):
        return "+" + digits
    if len(digits) == 9:  # 901234567 — operator kodi bilan mahalliy shakl
        return "+998" + digits
    return None


def divider() -> str:
    """Ingichka ajratgich qatori."""
    return DIVIDER


def title(emoji: str, text: str) -> str:
    """Bir xil sarlavha uslubi: emoji + qalin matn."""
    return f"{emoji} <b>{text}</b>"


# Buyurtma holati zanjiri: Buyurtmalarim bo'limida ko'rsatiladi.
_PROGRESS_STEPS = [
    "📦 Buyurtma qabul qilindi",
    "💳 To'lov tekshirilmoqda",
    "📦 Tayyorlanmoqda",
    "🚚 Yo'lda",
    "✅ Yetkazildi",
]


def order_progress(status: str, has_receipt: bool = False) -> str:
    """Buyurtma holatini bosqichma-bosqich zanjir ko'rinishida qaytaradi.

    O'tilgan bosqich — ✅, joriy bosqich — qalin, kelgusi — ▫️.
    Bekor qilingan buyurtma zanjirsiz ko'rsatiladi."""
    if status == "cancelled":
        return "✕ <b>Bekor qilindi</b>"
    current = {
        "pending":    1 if has_receipt else 0,
        "paid":       2,
        "processing": 2,
        "shipped":    3,
        "delivered":  4,
    }.get(status, 0)
    lines = []
    for i, step in enumerate(_PROGRESS_STEPS):
        if i < current:
            lines.append(f"✅ {step.split(' ', 1)[1]}")
        elif i == current:
            lines.append(f"{step.split(' ', 1)[0]} <b>{step.split(' ', 1)[1]}</b> ◀️")
        else:
            lines.append(f"▫️ {step.split(' ', 1)[1]}")
    return "\n".join(lines)
