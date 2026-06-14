"""Bir martalik xavfsiz "seed": DinamoKids do'koniga bolalar minadigan
mashinalarini (elektromobil) qo'shadi.

Bot ishga tushganda chaqiriladi. Do'konni topish va idempotentlik (takror
qo'shmaslik) mantig'i [seed_bikes] bilan bir xil — shu yerdan qayta ishlatiladi.

Jami 15 ta: turli markalar (Mercedes, BMW, Ferrari), jip/SUV, yo'ltanlamas,
tolokar va arzon modellar. Rasm va narxlar Uzum Market'dan (images.uzum.uz).
"""

import logging

from app import storage
from app.seed_bikes import _IMG, _find_seller

logger = logging.getLogger(__name__)

# (nom, tavsif, narx so'm, Uzum rasm ID)
_CARS = [
    ("Bolalar elektromobili Mercedes-Benz G63 AMG",
     "Akkumulyatorli Mercedes-Benz G63 AMG elektromobil — pultli boshqaruv, "
     "LED chiroqlar va musiqa bilan. Kichkina haydovchilar uchun premium model.",
     2043840, "cuuc8hui4n36ls3rikhg"),
    ("Bolalar elektromobili BMW, pultli",
     "BMW elektromobil — ota-ona masofadan pult bilan boshqarishi mumkin. "
     "Akkumulyatorli, yumshoq yurish, 2–6 yosh bolalar uchun.",
     2111040, "d7k3p9rsv8vghom28k1g"),
    ("Bolalar mashinasi BMW (akkumulyatorli)",
     "BMW uslubidagi bolalar elektromobili — akkumulyatorli, chiroq va musiqali. "
     "Hovli va xona ichida yurish uchun.",
     1151040, "d7acdds3obpufnha1npg"),
    ("Bolalar elektromobili Ferrari, pultli",
     "Ferrari uslubidagi sport elektromobil — pultli boshqaruv, yorqin dizayn, "
     "LED chiroqlar va musiqa bilan.",
     1247040, "cv1jj8ui4n36ls3sgqmg"),
    ("Bolalar elektrojipi (akkumulyatorli)",
     "Katta bolalar elektrojipi — baland klirens, mustahkam g'ildiraklar, "
     "akkumulyatorli. Hovlida ham, tekis yo'lda ham yuradi.",
     1910400, "d6a510nqkmalqfncdq90"),
    ("Bolalar elektr SUV mashina, 7 km/soat",
     "Kuchli bolalar elektr SUV — 1–10 yosh uchun, 7 km/soatgacha tezlik, "
     "xavfsiz va barqaror. Keng o'rindiq va kuchli motor.",
     2726697, "d83dcb21146tv070dapg"),
    ("Bolalar elektr UTV 12V, pult, LED, USB musiqa",
     "Bolalar elektr UTV bagi — 12V, 2.4GHz pult, LED chiroqlar, 35 kg gacha, "
     "2–13 yosh, USB musiqa. Ikki kishilik mustahkam model.",
     2495040, "d8l5klc9g1ktqmltaov0"),
    ("Bolalar elektromobili yo'ltanlamas JM-3188",
     "JM-3188 yo'ltanlamas (offroad) bolalar elektromobili — katta g'ildiraklar, "
     "pultli boshqaruv, hovli va notekis yo'llar uchun.",
     1631040, "d137r7a7s4fr083etb00"),
    ("Bolalar elektromobili yo'ltanlamas XW2188A",
     "XW2188A yo'ltanlamas bolalar elektr avtomobili — baland korpus, mustahkam "
     "g'ildiraklar, pult va musiqa bilan.",
     1559040, "d881lrrsv8vo2t0gkpag"),
    ("Bolalar elektromobili yo'ltanlamas NEL901",
     "NEL901 yo'ltanlamas bolalar elektromobili — kuchli motor, pultli boshqaruv, "
     "LED chiroqlar. Hovlida yurish uchun ideal.",
     1645440, "d87v5lk9g1ktqmlom6ig"),
    ("Bolalar Tolokar mashinasi (itarib + akkumulyator)",
     "Tolokar — kichkina bolalar uchun: ota-ona dasta bilan itaradi yoki "
     "akkumulyatorda mustaqil yuradi. 1–4 yosh uchun.",
     664329, "cmnt6v1s99ouqbfrmdt0"),
    ("Bolalar elektromobili (akkumulyatorli)",
     "Akkumulyatorli bolalar elektr mashinasi — chiroq va musiqali, qulay "
     "o'rindiq. Sayr va o'yin uchun.",
     1535990, "d7s67ejsv8vo2t0bpep0"),
    ("Bolalar elektromobili (arzon model)",
     "Sodda va arzon bolalar elektr mashinasi — akkumulyatorli, yengil. "
     "Birinchi elektromobil sifatida mos.",
     470438, "d1h62ags9rffrfkvcjlg"),
    ("Bolalar elektromobili (katta, premium)",
     "Katta o'lchamdagi premium bolalar elektromobili — keng o'rindiq, kuchli "
     "motor, to'liq jihozlangan. Kattaroq bolalar uchun.",
     3456000, "d2i3rg52lln7hego388g"),
    ("Bolalar mashinasi (oddiy, arzon)",
     "Kichkina bolalar uchun oddiy minadigan mashina — yengil, xavfsiz va arzon. "
     "Xona ichi o'yinlari uchun qulay.",
     135388, "d5pijh34eu2jdglfqi40"),
]


def seed_cars() -> int:
    """Bolalar mashinalarini DinamoKids do'koniga (yo'q bo'lsa) qo'shadi.
    Qo'shilgan mahsulotlar sonini qaytaradi."""
    found = _find_seller()
    if not found:
        logger.warning("Seed: 'DinamoKids' do'koni topilmadi — mashinalar qo'shilmadi.")
        return 0
    seller_id, seller = found
    shop_name = seller.get("shop_name", "DinamoKids")
    city = seller.get("city", "")

    existing = {
        str(p.get("name", "")).strip().lower()
        for p in storage.get_seller_products(seller_id)
    }

    added = 0
    for name, desc, price, img_id in _CARS:
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
        logger.info("Seed: %s ta bolalar mashinasi '%s' do'koniga qo'shildi.", added, shop_name)
    else:
        logger.info("Seed: barcha bolalar mashinalari allaqachon mavjud — qo'shilmadi.")
    return added
