"""Bir martalik xavfsiz "seed": DinamoKids do'koniga konditsionerlar qo'shadi.

Markalar: Artel, AUX, Premier — har biridan turli modellar (jami 18 ta).
Do'konni topish va idempotentlik (takror qo'shmaslik) mantig'i [seed_bikes]
bilan bir xil. Rasm va narxlar Uzum Market'dan (images.uzum.uz).
"""

import logging

from app.seed_bikes import _find_seller, seed_products

logger = logging.getLogger(__name__)

# (nom, tavsif, narx so'm, Uzum rasm ID)
_CONDITIONERS = [
    # ── Artel ────────────────────────────────────────────────────────────────
    ("Konditsioner Artel Marvarid 12BE Inverter",
     "Artel Marvarid 12 BTU invertorli konditsioner — ~35 m² xona uchun, "
     "sovutish va isitish, Turbo rejim, tejamkor va shovqinsiz.",
     3563010, ["d7q9uu3sv8vo2t0b39ug", "d7qsbhs9g1ktqmljcemg", "d8k6j0c9g1ktqmlt06ig"]),
    ("Konditsioner Artel Shahrisabz 12 Inverter, Wi-Fi, Turbo",
     "Artel Shahrisabz 12 BTU invertorli, Wi-Fi boshqaruvi va Turbo sovutish "
     "bilan — ~35 m² xona uchun, zamonaviy va tejamkor.",
     4275810, ["d7srsoa1146tv06tm870", "d7srsobsv8vo2t0c33c0", "d0o0j68n274j5sco1qvg"]),
    ("Konditsioner Artel Shahrisabz 12 Full DC Inverter, Wi-Fi + TEN",
     "Artel Shahrisabz Full DC invertorli, Wi-Fi va isitish TEN'i bilan — past "
     "kuchlanishda (120V) ham ishlaydi, qishda issiq beradi.",
     4305510, ["d8l69c3sv8vo2t0l80gg", "d6qm01q1146th72vbjb0", "d7ov3pi1146tv06s32p0"]),
    ("Konditsioner Artel Iceberg 12 Inverter + TEN",
     "Artel Iceberg 12 BTU invertorli, isitish uchun TEN bilan — ~35 m² xona "
     "uchun, sovutish-isitish, tejamkor.",
     4008510, ["d8l6d821146tv076qo9g", "d44747tsp2tj49o8ce20", "d4475j5sp2tj49o8cegg"]),
    ("Konditsioner Artel Marvarid 18 Inverter",
     "Artel Marvarid 18 BTU invertorli konditsioner — ~50 m² katta xona uchun, "
     "kuchli sovutish va isitish, tejamkor.",
     4939110, ["d717g83sv8vlb6minnv0", "d1ejv30s9rf1c8knsjog", "ctb76l5pb7f7ago7u2v0"]),
    ("Konditsioner Artel Iceberg 18BE Inverter",
     "Artel Iceberg 18 BTU invertorli — katta xonalar uchun kuchli havo "
     "sovutgich, sovutish-isitish, sokin ishlaydi.",
     8432127, "d84mqo21146tv070st80"),

    # ── AUX ──────────────────────────────────────────────────────────────────
    ("Konditsioner AUX ASW-H12A4/JMR Inverter, 35–40 m²",
     "AUX invertorli konditsioner, sovutish maydoni 35–40 m² — 12 BTU, "
     "tejamkor va shovqinsiz, sovutish va isitish.",
     4207500, ["d7l16mnuc85egd1knmdg", "d7l16r1qimkgrc91l5e0", "d7l174fuc85egd1knmq0"]),
    ("Konditsioner AUX ASW 12/18/24 Inverter, namlik datchigi",
     "AUX invertorli konditsioner (12/18/24 BTU), Turbo rejim va namlik "
     "datchigi bilan — samarali va qulay sovutish.",
     4613400, ["d7htiv3sv8vghom1ccjg", "d793mo3sv8vlb6mm14bg", "d793mq21146ojv9c2860"]),
    ("Konditsioner AUX Inverter, Wi-Fi, namlik sensori, Turbo",
     "AUX invertorli konditsioner — Wi-Fi boshqaruvi, namlik sensori va Turbo "
     "sovutish bilan, zamonaviy iqlim nazorati.",
     4685670, ["d7srmda1146tv06tm2cg", "d7srmmi1146tv06tm2n0", "d7ssem3sv8vo2t0c3j6g"]),
    ("Konditsioner AUX J seriyasi Inverter LRDI + TEN",
     "AUX J seriyasi invertorli konditsioner, isitish TEN'i bilan — qishda ham "
     "issiq beradi, tejamkor va ishonchli.",
     4508460, "d83h2bi1146tv070g33g"),
    ("Konditsioner AUX 12000 BTU, R410 + DC Inverter",
     "AUX 12000 BTU konditsioner — R410 freon, DC invertor, past shovqin "
     "darajasi, qulay va tejamkor muhit.",
     4554000, "d79ua83sv8vlb6mmd2u0"),
    ("Konditsioner AUX ASW 12/18 Inverter, Turbo namlik",
     "AUX invertorli konditsioner (12/18 BTU), Turbo rejim va namlik datchigi "
     "bilan — samarali sovutish, energiya tejamkor.",
     4479037, ["d8kj42i1146tv076jgd0", "d8kj4349g1ktqmlt402g", "d8kj43rsv8vo2t0l0rj0"]),

    # ── Premier ──────────────────────────────────────────────────────────────
    ("Konditsioner Premier PRM-12COSPA-INV/W DC Inverter",
     "Premier 12 BTU DC invertorli konditsioner — ~35 m² xona uchun, sovutish "
     "va isitish, tejamkor va sokin.",
     3662010, ["d7q9utk9g1ktqmlj6b00", "d7q9v1i1146tv06smi6g", "d7ecc5q1146ojv9e77jg"]),
    ("Konditsioner Premier Calido PRM-12CASPA-INV, Inverter",
     "Premier Calido 12 BTU invertorli konditsioner, Full HD displey — zamonaviy "
     "dizayn, samarali sovutish-isitish.",
     3712500, ["d7qrvrc9g1ktqmljc72g", "d7qrvqjsv8vo2t0b967g", "d7qrvqi1146tv06ssbbg"]),
    ("Konditsioner Premier PRM-12SRSPA-INV, Full DC Inverter",
     "Premier 12 BTU Full DC invertorli konditsioner — energiya tejamkor, "
     "shovqinsiz, ~35 m² xona uchun.",
     3988710, ["d8h619c9g1ktqmlrq8u0", "d8n8e13sv8vo2t0m3big", "d8n8rgbsv8vo2t0m3jk0"]),
    ("Konditsioner Premier PRMFR-12SNR1-INV, 35 m², A+++",
     "Premier 12 BTU invertorli konditsioner, A+++ energiya klassi — ~35 m² "
     "xona uchun, juda tejamkor va kuchli.",
     5674482, ["cvsvpl5pb7fbmqmnjh3g", "cvsvprs7fd1p445sd6m0", "cvsvpt47fd1p445sd6mg"]),
    ("Konditsioner Premier Genius PRMGE-12SNR1-INV, Wi-Fi, R32",
     "Premier Genius 12 BTU invertorli — Wi-Fi boshqaruvi, R32 freon, A++ "
     "energiya klassi, zamonaviy iqlim nazorati.",
     6920100, ["d6mkgj8s9rf3ubr0e110", "d6mkgkdsp2tohdbd9ru0"]),
    ("Konditsioner Premier PRMSR-18CMDS-INV, R410A, A klass, LED",
     "Premier 18 BTU invertorli konditsioner — R410A freon, A klass, 150–240V "
     "kuchlanishda ishlaydi, LED displey. Katta xona uchun.",
     6534000, ["d6mlgh21146th72tlbc0", "d6mlgidsp2tohdbdadg0"]),
]


def seed_conditioners() -> int:
    """Konditsionerlarni DinamoKids do'koniga qo'shadi/rasmlarini yangilaydi.
    Qo'shilgan + yangilangan mahsulotlar sonini qaytaradi."""
    return seed_products(_CONDITIONERS, _find_seller, "konditsionerlar")
