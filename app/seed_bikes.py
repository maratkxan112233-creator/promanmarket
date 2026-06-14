"""Bir martalik xavfsiz "seed": DinamoKids do'koniga velosipedlar qo'shadi.

Bot ishga tushganda chaqiriladi. Do'konni telefon yoki nom bo'yicha topadi va
velosipedlarni faqat HALI YO'Q bo'lsa qo'shadi — shuning uchun bot necha marta
qayta ishga tushsa ham takror qo'shilmaydi va mavjud mahsulotlarga tegmaydi.

Har xil o'lcham: 3 g'ildirakli (kichkina bolalar) → 12"/14"/16"/20" bolalar →
24" o'smir → 26"/28" kattalar (tog' va shahar) → fat-bike. Jami 30 ta.
Rasm va narxlar Uzum Market'dan (images.uzum.uz CDN) olingan.
"""

import logging

from app import storage

logger = logging.getLogger(__name__)

# Do'konni aniqlash uchun (ekrandagi ma'lumot bo'yicha):
#   telefon: 998335424245  →  oxirgi 9 raqami "335424245"
#   nom:     "DinamoKids"
_SELLER_PHONE_TAIL = "335424245"
_SELLER_SHOP_NAME = "dinamokids"

_IMG = "https://images.uzum.uz/{}/t_product_540_high.jpg"

# (nom, tavsif, narx so'm, Uzum rasm ID)
_BIKES = [
    # ── Kichkina bolalar: 3 g'ildirakli va yon g'ildirakli ──────────────────
    ("Uch g'ildirakli bolalar velosipedi (mini)",
     "Eng kichik bolalar uchun 3 oyoqli (g'ildirakli) velosiped. Yiqilmaydi, "
     "xavfsiz — 1,5–3 yosh bolalar uchun birinchi velosiped.",
     290030, "cvl9uetpb7f8td1j28dg"),
    ("Uch g'ildirakli bolalar velosipedi BONVI",
     "BONVI 3 g'ildirakli velosiped, dastasi va savatchasi bilan. 2–5 yoshli "
     "bolalar uchun mustahkam va qulay.",
     950600, "copr23f6cpg3jdti04hg"),
    ("Bolalar velosipedi qo'shimcha o'rindiq va savatcha bilan",
     "Yosh bolalar uchun ikki g'ildirakli velosiped, yordamchi yon g'ildiraklari, "
     "qo'shimcha o'rindiq va old savatchasi bilan.",
     564540, "d0pi24b3uvph509vq9d0"),
    ("ARIVO bolalar velosipedi 12\"/16\", yon g'ildirakli",
     "ARIVO po'lat ramli bolalar velosipedi (12\" yoki 16\"), old savat va "
     "yordamchi yon g'ildiraklar bilan. 3–6 yosh uchun.",
     649900, "d2k0hsj4eu2g1liuv760"),

    # ── Bolalar: 12"/14"/16"/20" (qiz va o'g'il bolalar) ────────────────────
    ("Bolalar velosipedi BONVI 12\"/16\"/20\"",
     "Ikki g'ildirakli BONVI bolalar velosipedi — 12, 16 yoki 20 dyuym. Yengil "
     "po'lat rama, yordamchi g'ildiraklar bilan.",
     475300, "d7b10t43obpufnhaarq0"),
    ("Bolalar velosipedi Velomax 12\"/14\"/16\"/20\"",
     "Velomax ikki g'ildirakli bolalar velosipedi, o'lchamlari 12/14/16/20 dyuym. "
     "Turli yoshdagi bolalar uchun.",
     522830, "d0rm590n274j5scosoag"),
    ("Bolalar velosipedi Demansh 776",
     "Demansh 776 ikki g'ildirakli bolalar velosipedi, mustahkam rama va "
     "yordamchi g'ildiraklar bilan.",
     552900, "d8hbgbbsv8vo2t0jqqag"),
    ("Bolalar velosipedi BONVI 5804",
     "Ikki g'ildirakli BONVI 5804 bolalar velosipedi — yengil, chiroyli dizayn, "
     "o'g'il bolalar uchun.",
     543200, "d79r8143obpufnh9rh8g"),
    ("Bolalar velosipedi DRONGO 12\"/16\"/20\"",
     "DRONGO bolalar velosipedi, o'lchamlari 12, 16, 20 dyuym. Zamonaviy ko'rinish, "
     "mustahkam qurilma.",
     533500, "cuvltnjvgbkm5ehh3cv0"),

    # ── Qizlar uchun (pushti, princessa) ────────────────────────────────────
    ("Qizlar uchun velosiped (3–12 yosh)",
     "Qizlar uchun chiroyli bolalar velosipedi, savatchasi bilan. 3–12 yosh "
     "bolalar uchun — pushti rang.",
     572300, "cvp5bsc7fd1p445rffo0"),
    ("PRINCESSA qizlar velosipedi 12\"/16\"/20\"",
     "PRINCESSA bolalar velosipedi (12/16/20 dyuym), old savat va bezaklar bilan — "
     "qizchalar uchun.",
     564540, "d7lrdk2d955cjr7d25m0"),
    ("Velosiped \"Printsessa\" 12\"/16\"/20\"",
     "\"Printsessa\" qizlar velosipedi, o'lchamlari 12, 16, 20 dyuym. Savatcha va "
     "yordamchi g'ildiraklar bilan.",
     620800, "cv6k6uei4n36ls3tq1tg"),
    ("Velosiped DRONGO Princessa (bayroqchali)",
     "DRONGO Princessa qizlar velosipedi, bayroqcha va savatcha bilan — yorqin va "
     "chiroyli dizayn.",
     727500, "d71u20a1146ojv992sq0"),

    # ── 20" (katta bolalar / o'smirlar) ─────────────────────────────────────
    ("Bolalar velosipedi 20\" VELOSPORT",
     "VELOSPORT ikki g'ildirakli 20 dyuymli bolalar velosipedi — 6–10 yoshli "
     "bolalar uchun mustahkam variant.",
     545140, "d87c3obsv8vo2t0gc7l0"),
    ("Sport bolalar velosipedi 20\" Neon Pro",
     "Neon Pro 20 dyuymli sport bolalar velosipedi, zamonaviy dizayn, yengil va "
     "tez — faol bolalar uchun.",
     1330975, "d6q4oqgs9rf3ubr1uaa0"),
    ("Bolalar tog' velosipedi BONVI 20\", qo'sh rom",
     "BONVI 20 dyuymli bolalar tog' velosipedi, qo'shaloq (ikki) romli mustahkam "
     "qurilma. ID:9458.",
     947690, "cppreqj6eisq2rkcqi4g"),
    ("Velosiped 20\", 21 tezlik",
     "20 dyuymli velosiped, 21 tezlikli uzatma bilan — o'smirlar va kichik "
     "bo'yli foydalanuvchilar uchun.",
     1212015, "d7lqkbq1146tv06qlimg"),
    ("Velosiped ADKIDS 20\"",
     "ADKIDS 20 dyuymli velosiped — yosh bolalar va o'smirlar uchun, sayr va "
     "kundalik yurish uchun qulay.",
     1358000, "co3r5a5lqsilsr3livq0"),
    ("Tog' velosipedi 999, 20×3.0, alyuminiy rama",
     "999 Model 20×3.0 tog' velosipedi — quyma alyuminiy rama, keng (fat) "
     "g'ildiraklar. Yengil va mustahkam.",
     1694153, "d8jb0mbsv8vo2t0khme0"),

    # ── 24" (o'smirlar) ─────────────────────────────────────────────────────
    ("Velosiped Demansh 20\"/24\"",
     "Demansh velosiped, 20 yoki 24 dyuym o'lchamda — o'smirlar uchun, tog' "
     "uslubidagi mustahkam rama.",
     965150, "d77kskc3obpufnh8utlg"),
    ("Tog' velosipedi 24\", 21 tezlik, amortizator",
     "24 dyuymli tog' velosipedi, 21 tezlik, disk tormoz va old amortizatsiya "
     "bilan — o'smirlar uchun sayr velosipedi.",
     1057290, "d7g9vsbsv8vghom0k5ig"),
    ("Tog' velosipedi 20\"/24\", 3.0 balon",
     "O'smirlar uchun 20.24 dyuymli tog' velosipedi, 3.0 qalin balonli — yo'lsiz "
     "hududlarda ham qulay.",
     1309500, "cv08c0dpb7f9qcnereh0"),

    # ── 26" tog' velosipedlari (kattalar) ───────────────────────────────────
    ("Tog' velosipedi DEMANSH 26\", 3.0 balon",
     "DEMANSH tog' velosipedi 26 dyuym, 3.0 qalin balonli, mustahkam rama — "
     "kattalar uchun yo'lsiz va shahar yo'llari uchun.",
     969030, "d2p8j8d2llnd6jujsph0"),
    ("Tog' velosipedi DEMANSH 26\", 2.5 balon, tezlikli",
     "DEMANSH tezlikli tog' velosipedi, 26 dyuym, 2.5 balon — sport va kundalik "
     "foydalanish uchun.",
     1023350, "d77m9rbsv8vlb6mlfiqg"),
    ("Tog' velosipedi BONVI 025, 26\"",
     "BONVI 025 tog' velosipedi, 26 dyuym, o'smir va kattalar uchun. ID:1507 — "
     "ishonchli va ommabop model.",
     1164000, "d4s0o48jsv1o95ch927g"),
    ("Tog' velosipedi 26\", 21 tezlik, amortizator",
     "26 dyuymli tog' velosipedi, 21 tezlik, disk tormoz va old amortizatsiya "
     "bilan — kattalar uchun.",
     1057300, "d7gp4d3sv8vghom0rc60"),
    ("Tog' velosipedi DREZ 26-R, 21 tezlik (Shimano)",
     "DREZ 26-R tog' velosipedi, 21 tezlik, Shimano uzatma kalitlari bilan. "
     "ID:13750 — kuchli va aniq uzatma.",
     1697500, "d76h9r3sv8vlb6mkufo0"),
    ("Fat-bike BAOL 26\" 4.0",
     "BAOL FAT BIKE 26 dyuym, 4.0 juda keng balonli amortizatorli velosiped — "
     "qor, qum va yo'lsiz hududlar uchun.",
     1881790, "crmjpc6vip07shn5br7g"),
    ("Tog' velosipedi Buyuk Bonvi 26\"",
     "Buyuk tog' Bonvi 26 dyuymli velosiped — mustahkam rama, kattalar uchun "
     "kundalik va sport yurish.",
     1212500, "d0mtuqi7s4fo7mqaa4hg"),

    # ── 28" shahar velosipedlari (kattalar) ─────────────────────────────────
    ("Shahar velosipedi Belarus 28\"",
     "Belarus 28 dyuymli shahar velosipedi (ID:377) — klassik, mustahkam, "
     "kundalik yurish uchun qulay.",
     970000, "clia28lennt6m2906u7g"),
    ("Shahar velosipedi Belarus 28\", Nexus",
     "Belarus 28 dyuymli shahar velosipedi, Nexus uzatma bilan — shaharda "
     "qulay va silliq yurish.",
     1110650, "d865uuq1146tv071go5g"),
    ("ARIVO 28\" shahar velosipedi, savatchali",
     "ARIVO 28 dyuymli shahar velosipedi, po'lat rama va old savatcha bilan — "
     "kattalar uchun klassik shahar modeli.",
     1358000, "d2k0ul52llnd6juig7tg"),

    # ── Universal / ko'p o'lchamli ──────────────────────────────────────────
    ("ARIVO velosiped 20\"/24\"/26\", savatchali",
     "ARIVO velosiped, o'lchamlari 20/24/26 dyuym, po'lat rama va old savatcha "
     "bilan — butun oila uchun.",
     1067000, "d2k0sr7iub35i07h70l0"),
    ("Universal velosiped 26\" (shahar va yo'lsiz)",
     "26 dyuymli universal velosiped — shahar ham, yo'lsiz hududlar uchun ham "
     "mos. Kattalar uchun ko'p maqsadli.",
     1270215, "d7lt1849g1ktqmlh6ii0"),
    ("Kattalar uchun velosiped BONVI Sport",
     "BONVI Sport kattalar velosipedi — yengil, tez va mustahkam, sport va "
     "kundalik yurish uchun.",
     1419789, "d12m78r3uvppu2aau16g"),
]


def _find_seller() -> tuple[int, dict] | None:
    """DinamoKids do'konini telefon yoki nom bo'yicha topadi."""
    for sid, s in storage.get_sellers().items():
        phone_ok = storage.normalize_phone(s.get("phone")) == _SELLER_PHONE_TAIL
        name_ok = str(s.get("shop_name", "")).strip().lower() == _SELLER_SHOP_NAME
        if phone_ok or name_ok:
            return int(sid), s
    return None


def seed_bikes() -> int:
    """Velosipedlarni DinamoKids do'koniga (yo'q bo'lsa) qo'shadi.
    Qo'shilgan mahsulotlar sonini qaytaradi."""
    found = _find_seller()
    if not found:
        logger.warning("Seed: 'DinamoKids' do'koni topilmadi — velosipedlar qo'shilmadi.")
        return 0
    seller_id, seller = found
    shop_name = seller.get("shop_name", "DinamoKids")
    city = seller.get("city", "")

    existing = {
        str(p.get("name", "")).strip().lower()
        for p in storage.get_seller_products(seller_id)
    }

    added = 0
    for name, desc, price, img_id in _BIKES:
        if name.strip().lower() in existing:
            continue
        storage.add_product({
            "seller_id": seller_id,
            "shop_name": shop_name,
            "city": city,
            "name": name,
            "description": desc,
            "price": price,
            "photos": [_IMG.format(img_id)],
        })
        added += 1

    if added:
        logger.info("Seed: %s ta velosiped '%s' do'koniga qo'shildi.", added, shop_name)
    else:
        logger.info("Seed: barcha velosipedlar allaqachon mavjud — qo'shilmadi.")
    return added
