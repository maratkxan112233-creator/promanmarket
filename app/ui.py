"""Bot ko'rinishi uchun umumiy yordamchilar.

Butun bot bo'ylab xabar va tugmalar bir xil, toza, zamonaviy ko'rinishi uchun
shu yerda jamlangan. Bu yerni o'zgartirsangiz — hamma joyda bir vaqtda o'zgaradi.
"""

# Ingichka ajratgich (xabar bo'limlarini toza ajratish uchun).
DIVIDER = "──────────────"


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
