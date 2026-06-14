"""Bir martalik xavfsiz "seed": Bravo electronics do'koniga mahsulotlar qo'shadi.

Bot ishga tushganda chaqiriladi. Do'konni telefon yoki nom bo'yicha topadi va
mahsulotlarni faqat HALI YO'Q bo'lsa qo'shadi — shuning uchun bot necha marta
qayta ishga tushsa ham takror qo'shilmaydi va mavjud mahsulotlarga tegmaydi.

Hozircha: konditsionerlar va kir yuvish mashinalari.
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

# Eng ko'p sotilayotgan kir yuvish mashinalari (Uzum'dagi ommabop, sharhlari ko'p).
# (nom, tavsif, narx so'm, Uzum rasm ID)
_WASHING_MACHINES = [
    ("Kir yuvish mashinasi JPE Invertor BLDC, 6-8-10 kg",
     "Avtomat kir yuvish mashinasi, BLDC invertor motor, 6/8/10 kg, kechiktirish "
     "funksiyasi va Child-Lock. Eng ko'p sotilganlardan biri.",
     2410174, "crfbbk60t1lqb8aqt2r0"),
    ("Yarim avtomatik kir yuvish mashinasi Rosso R90WM, 9 kg",
     "Yarim avtomat kir yuvish mashinasi, 9 kg, ikki barabanli (yuvish + quritish), "
     "tejamkor va ishonchli.",
     1345410, "cvgerqjvgbkm5ehljia0"),
    ("Kirmoshina WM-4088, 4 kg, qurutish barabani bilan",
     "Ixcham yarim avtomat kir yuvish mashinasi, 4 kg, alohida qurutish barabani "
     "bilan — kichik xonadonlar uchun qulay.",
     548460, "d1rmni7nrko24u2h49c0"),
    ("Kir yuvish mashinasi ELITE ELT WM-4199, yarim avtomatik",
     "Yarim avtomat kir yuvish mashinasi, ikki barabanli, tejamkor va arzon — "
     "kundalik foydalanish uchun.",
     1088010, "cqd5denfrr885gh2mteg"),
    ("Kir yuvish mashinasi QLT 6/8/10 kg",
     "Avtomat kir yuvish mashinasi, 6/8/10 kg variantlari, ko'p dasturli, "
     "tejamkor va sokin.",
     2177010, "d6begl7qkmarvs5i1in0"),
    ("Kir yuvish mashinasi Artel SE25 Mini, 2,5 kg, oq",
     "Mini avtomat kir yuvish mashinasi, 2,5 kg — talabalar va kichik oilalar "
     "uchun ixcham yechim.",
     710820, "cv0k6sui4n36ls3s6tbg"),
    ("Kir yuvish mashinasi Artel 2.5 kg",
     "Ixcham kir yuvish mashinasi, 2,5 kg, kam joy egallaydi, oson boshqariladi.",
     701910, "cujete45j42bjc4d1dp0"),
    ("Kir yuvish mashinasi Magna Inverter, 6 kg, 1000 ob/daq",
     "Avtomat kir yuvish mashinasi, invertor motor, 6 kg, 1000 ob/daq siqish, "
     "bug' bilan yuvish funksiyasi.",
     2474010, "d80t9qbsv8vo2t0dojlg"),
    ("Kir yuvish mashinasi Hofmann WM610BWH2/HF, 6 kg, BLDC Inverter",
     "Avtomat kir yuvish mashinasi, BLDC invertor motor, 6 kg, 12 ta dastur, "
     "A+++ energiya klassi.",
     3563010, "d7p0abi1146tv06s41u0"),
    ("HOFMANN avtomat kir yuvish mashinasi, 6 kg",
     "Avtomat kir yuvish mashinasi, 6 kg, ko'p dasturli, tejamkor va ishonchli — "
     "ommabop model.",
     3266010, "d8al9di1146tv073465g"),
]


def _find_bravo_seller() -> tuple[int, dict] | None:
    """Bravo electronics do'konini telefon yoki nom bo'yicha topadi."""
    for sid, s in storage.get_sellers().items():
        phone_ok = storage.normalize_phone(s.get("phone")) == _SELLER_PHONE_TAIL
        name_ok = str(s.get("shop_name", "")).strip().lower() == _SELLER_SHOP_NAME
        if phone_ok or name_ok:
            return int(sid), s
    return None


def _seed_products(items: list, label: str) -> int:
    """Berilgan mahsulotlarni Bravo electronics do'koniga (yo'q bo'lsa) qo'shadi.
    Qo'shilgan mahsulotlar sonini qaytaradi."""
    found = _find_bravo_seller()
    if not found:
        logger.warning("Seed: 'Bravo electronics' do'koni topilmadi — %s qo'shilmadi.", label)
        return 0
    seller_id, seller = found
    shop_name = seller.get("shop_name", "Bravo electronics")
    city = seller.get("city", "")

    existing = {
        str(p.get("name", "")).strip().lower()
        for p in storage.get_seller_products(seller_id)
    }

    added = 0
    for name, desc, price, img_id in items:
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
        logger.info("Seed: %s ta %s '%s' do'koniga qo'shildi.", added, label, shop_name)
    else:
        logger.info("Seed: barcha %s allaqachon mavjud — qo'shilmadi.", label)
    return added


def seed_air_conditioners() -> int:
    """Yo'q konditsionerlarni qo'shadi."""
    return _seed_products(_AIR_CONDITIONERS, "konditsioner")


def seed_washing_machines() -> int:
    """Yo'q kir yuvish mashinalarini qo'shadi."""
    return _seed_products(_WASHING_MACHINES, "kir yuvish mashinasi")


def seed_all() -> int:
    """Barcha kategoriyalarni seed qiladi. Jami qo'shilganlar sonini qaytaradi."""
    return seed_air_conditioners() + seed_washing_machines()
