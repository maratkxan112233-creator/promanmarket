"""Bir martalik xavfsiz "seed": Bravo electronics do'koniga konditsionerlar qo'shadi.

Bot ishga tushganda chaqiriladi. Do'konni telefon yoki nom bo'yicha topadi va
14 ta konditsionerni faqat HALI YO'Q bo'lsa qo'shadi — shuning uchun bot necha
marta qayta ishga tushsa ham takror qo'shilmaydi va mavjud mahsulotlarga tegmaydi.

Rasm manzillari Uzum Market CDN'idan (images.uzum.uz) olingan.
"""

import logging

from app import storage

logger = logging.getLogger(__name__)

# Do'konni aniqlash uchun (ekrandagi ma'lumot bo'yicha):
#   telefon: 998951002505  →  oxirgi 9 raqami "951002505"
#   nom:     "Bravo electronics"
_SELLER_PHONE_TAIL = "951002505"
_SELLER_SHOP_NAME = "bravo electronics"

_IMG = "https://images.uzum.uz/{}/t_product_540_high.jpg"

# (nom, tavsif, narx so'm, Uzum rasm ID)
_AIR_CONDITIONERS = [
    ("Konditsioner Shivaki SHVSIM5AW12BE Inverter, A",
     "12 000 BTU invertorli split-konditsioner. ~35 m² xonani sovutadi va isitadi, "
     "A klass energiya tejamkor, sokin ishlaydi.",
     3563010, "d6pbu0i1146th72uq9ng"),
    ("Konditsioner Artel Marvarid 12BE Inverter",
     "Artel Marvarid 12 BTU invertorli konditsioner. ~35 m² xona uchun, sovutish va "
     "isitish, tejamkor hamda shovqinsiz.",
     3365010, "d7vl7ojsv8vo2t0d8k1g"),
    ("Konditsioner IMMER 12 Full DC Inverter, R32",
     "IMMER Full DC invertorli konditsioner (12/18/24 BTU), R32 freon, shovqinsiz va "
     "energiya tejamkor.",
     3404610, "d8g0gbk9g1ktqmlrc2a0"),
    ("Konditsioner Artel Iceberg 12 Inverter + TEN",
     "Artel Iceberg 12 BTU invertorli, isitish uchun TEN bilan — qishda ham issiq "
     "beradi, ~35 m² xona uchun.",
     4008510, "d8l6d821146tv076qo9g"),
    ("Konditsioner Shivaki Elegant 12 Inverter",
     "Shivaki Elegant 12 BTU invertorli konditsioner, zamonaviy dizayn, "
     "sovutish-isitish, tejamkor.",
     3549150, "co8giicqk7bc30trgqig"),
    ("Konditsioner Avalon Brussel 12 Inverter + TEN",
     "Avalon Brussel 12 BTU invertorli, TEN isitgich bilan, past kuchlanishda ham "
     "ishlaydi, ~35 m² xona uchun.",
     5385600, "d8epbqs9g1ktqmlqt9d0"),
    ("Konditsioner Rulls Strom 12 Inverter",
     "Rulls Strom 12 BTU invertorli konditsioner, sovutish va isitish, sokin hamda "
     "tejamkor.",
     3266010, "d8jcq3k9g1ktqmlslp60"),
    ("Konditsioner Midea ALBA PRO Inverter",
     "Midea Alba Pro invertorli konditsioner, R32, jim ishlaydi, 30% gacha energiya "
     "tejaydi, past kuchlanishga chidamli.",
     4652010, "d7obc7i1146tv06rqgqg"),
    ("Konditsioner Haier AS35PHC2HRA Full DC Inverter, 12000 BTU",
     "Haier Full DC invertorli, 12000 BTU, R32 freon, sovutish-isitish, sokin va "
     "tejamkor.",
     3959010, "d8l58fbsv8vo2t0l7am0"),
    ("Konditsioner Chigo 12 DC Inverter, R32",
     "Chigo DC invertorli konditsioner (12/18/24 BTU), R32 freon, Turbo sovutish, "
     "premium dizayn.",
     3662010, "d8l939a1146tv076sk00"),
    ("Konditsioner AUX ASW 12 Inverter",
     "AUX invertorli konditsioner (12/18 BTU), Turbo rejim va namlik datchigi bilan, "
     "samarali sovutish.",
     4479037, "d8kj42i1146tv076jgd0"),
    ("Konditsioner Artel Shahrisabz 12 Inverter, Wi-Fi",
     "Artel Shahrisabz 12 BTU invertorli, Wi-Fi boshqaruvi, ~35 m² xona uchun, "
     "sovutish va isitish.",
     4276800, "d0d0la0n274j5sclj8c0"),
    ("Konditsioner Samsung 12 kBTU AR12DXHQASINEV Inverter",
     "Samsung 12 kBTU invertorli konditsioner, 35 m² gacha xonalar uchun, sokin va "
     "energiya tejamkor.",
     4694580, "d1tp75niub3cuo9d2dqg"),
    ("Konditsioner TCL Split 12 Inverter",
     "TCL invertorli split-konditsioner (12/24 BTU), 70 m² gacha, R32 freon, "
     "tejamkor va shovqinsiz.",
     3959010, "cqo6askqvsse8leujoc0"),
]


def _find_bravo_seller() -> tuple[int, dict] | None:
    """Bravo electronics do'konini telefon yoki nom bo'yicha topadi."""
    for sid, s in storage.get_sellers().items():
        phone_ok = storage.normalize_phone(s.get("phone")) == _SELLER_PHONE_TAIL
        name_ok = str(s.get("shop_name", "")).strip().lower() == _SELLER_SHOP_NAME
        if phone_ok or name_ok:
            return int(sid), s
    return None


def seed_air_conditioners() -> int:
    """Yo'q konditsionerlarni qo'shadi. Qo'shilgan mahsulotlar sonini qaytaradi."""
    found = _find_bravo_seller()
    if not found:
        logger.warning("Seed: 'Bravo electronics' do'koni topilmadi — konditsioner qo'shilmadi.")
        return 0
    seller_id, seller = found
    shop_name = seller.get("shop_name", "Bravo electronics")
    city = seller.get("city", "")

    existing = {
        str(p.get("name", "")).strip().lower()
        for p in storage.get_seller_products(seller_id)
    }

    added = 0
    for name, desc, price, img_id in _AIR_CONDITIONERS:
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
        logger.info("Seed: %s ta konditsioner '%s' do'koniga qo'shildi.", added, shop_name)
    else:
        logger.info("Seed: barcha konditsionerlar allaqachon mavjud — qo'shilmadi.")
    return added
