"""Ish vaqtida o'zgartiriladigan biznes sozlamalari va marketing matnlari.

Barcha qiymatlar admin panel (⚙️ Sozlamalar) orqali boshqariladi va
data/runtime.json da saqlanadi — kodga yozilmaydi. Handler'lar narx/foiz/matnni
shu modul orqali oladi, shunda admin qiymatni o'zgartirsa hamma joyda darhol
yangi qiymat ko'rinadi.
"""

from app.storage import get_runtime_config
from app.ui import money


# ─── Raqamli qiymatlar ────────────────────────────────────────────────────────
def delivery_fee() -> int:
    return int(get_runtime_config().get("delivery_fee", 19_000))


def free_threshold() -> int:
    return int(get_runtime_config().get("free_delivery_threshold", 300_000))


def prepay_percent() -> int:
    return int(get_runtime_config().get("prepay_percent", 10))


def prepay_rate() -> float:
    """0.10 ko'rinishida — summani hisoblash uchun."""
    return prepay_percent() / 100


def contact_phone() -> str:
    return str(get_runtime_config().get("contact_phone", "")).strip()


def gift_text() -> str:
    return str(get_runtime_config().get("gift_text", "Kafolatlangan sovg'a")).strip()


def popup() -> dict:
    return get_runtime_config().get("popup", {})


def about() -> dict:
    return get_runtime_config().get("about", {})


def fill_placeholders(text: str) -> str:
    """Matndagi {prepay}/{threshold}/{fee}/{phone} o'rinbosarlarini joriy
    qiymatlar bilan almashtiradi (FAQ javoblari va h.k. uchun)."""
    return (
        text.replace("{prepay}", str(prepay_percent()))
            .replace("{threshold}", f"{free_threshold():,}".replace(",", " "))
            .replace("{fee}", money(delivery_fee()))
            .replace("{phone}", contact_phone())
    )


# ─── Marketing matn bloklari ─────────────────────────────────────────────────
def _thr() -> str:
    return f"{free_threshold():,}".replace(",", " ")


def start_banner() -> str:
    """Bosh sahifa (START) banneri — ishonch va konversiya bloki."""
    lines = [
        "━━━━━━━━━━━━━━━━━━━",
        "",
        "🚚 <b>24 soat ichida yetkazib beramiz</b>",
        "",
        f"💳 Faqat {prepay_percent()}% oldindan to'lov",
        "",
        f"🎁 {_thr()} so'mdan yuqori xaridga kafolatlangan sovg'a",
        "",
        f"🚛 {_thr()} so'mdan yuqori xaridga BEPUL yetkazib berish",
        "",
        "✅ Tekshirilgan mahsulotlar",
        "",
        "━━━━━━━━━━━━━━━━━━━",
    ]
    extra = str(get_runtime_config().get("banner_extra", "")).strip()
    if extra:
        lines += ["", f"🔥 {extra}"]
    return "\n".join(lines)


def product_benefits_block(price: int, has_warranty: bool = False) -> str:
    """Har mahsulot kartasi ostidagi ishonch bloki (15-band)."""
    thr = free_threshold()
    fee = delivery_fee()
    lines = ["━━━━━━━━━━━━━━"]
    if has_warranty:
        lines.append("🛡 1 yil kafolat")
    else:
        lines.append("🛡 Kafolat mavjud")
    lines.append("🚚 <b>24 soatda yetkazamiz</b>")
    lines.append(f"💳 Faqat {prepay_percent()}% oldindan to'lov")
    lines.append(f"🎁 {_thr()}+ xaridga sovg'a")
    if price >= thr or fee == 0:
        lines.append("🚛 Yetkazib berish: <b>BEPUL</b>")
    else:
        lines.append(f"🚛 Yetkazish {money(fee)} · {_thr()}+ <b>BEPUL</b>")
    lines.append("━━━━━━━━━━━━━━")
    return "\n".join(lines)


def cta_label() -> str:
    """Buyurtma tugmasi matni (5-band)."""
    return f"🟢 {prepay_percent()}% to'lab buyurtma berish"


def why_us_text() -> str:
    """⭐ Nega aynan Pro Man Market? (2-band)."""
    return (
        "⭐ <b>Nega aynan Pro Man Market?</b>\n"
        "────────\n\n"
        "🚚 <b>24 soatda yetkazish</b>\n"
        "Buyurtmangiz to'lov tasdiqlangach 24 soat ichida qo'lingizda.\n\n"
        f"💳 <b>Faqat {prepay_percent()}% oldindan to'lov</b>\n"
        "Qolganini mahsulotni olganingizda to'laysiz.\n\n"
        "🛡 <b>Kafolat</b>\n"
        "Barcha mahsulotlar kafolat bilan sotiladi.\n\n"
        "✅ <b>Tekshirilgan sotuvchilar</b>\n"
        "Har bir sotuvchi tekshiruvdan o'tgan.\n\n"
        "📞 <b>Qo'llab-quvvatlash</b>\n"
        f"Savollaringizga tez javob beramiz: {contact_phone()}\n\n"
        f"🎁 <b>Sovg'a</b>\n"
        f"{_thr()} so'mdan yuqori xaridga — {gift_text().lower()}.\n\n"
        f"🚛 <b>Bepul yetkazib berish</b>\n"
        f"{_thr()} so'mdan yuqori xaridlarga yetkazib berish bepul, "
        f"qolganlariga {money(delivery_fee())}."
    )


def about_text() -> str:
    """🏢 Biz haqimizda (3-band)."""
    a = about()
    lines = ["🏢 <b>Biz haqimizda</b>", "────────", ""]
    if a.get("company"):
        lines += [a["company"], ""]
    if a.get("phone"):
        lines.append(f"📞 Telefon: {a['phone']}")
    if a.get("telegram"):
        lines.append(f"✈️ Telegram: {a['telegram']}")
    if a.get("work_hours"):
        lines.append(f"🕘 Ish vaqti: {a['work_hours']}")
    if a.get("address"):
        lines.append(f"📍 Manzil: {a['address']}")
    if a.get("requisites"):
        lines += ["", f"🧾 Rekvizitlar:\n{a['requisites']}"]
    return "\n".join(lines)


def faq_list() -> list:
    """FAQ ro'yxati — [{q, a}], o'rinbosarlar allaqachon almashtirilgan."""
    return [
        {"q": fill_placeholders(item.get("q", "")),
         "a": fill_placeholders(item.get("a", ""))}
        for item in get_runtime_config().get("faq", [])
        if item.get("q")
    ]
