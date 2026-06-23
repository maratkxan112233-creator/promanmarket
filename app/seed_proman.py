"""Bir martalik xavfsiz "seed": ProMan Electronics do'koniga mahsulotlar qo'shadi.

Bot ishga tushganda chaqiriladi. Do'konni nom yoki telefon bo'yicha topadi va
mahsulotlarni faqat HALI YO'Q bo'lsa qo'shadi — shuning uchun bot necha marta
qayta ishga tushsa ham takror qo'shilmaydi va mavjud mahsulotlarga tegmaydi.

25 ta eng talabgir, kunlik hayotda zarur maishiy texnika/elektronika.
MUHIM: hamma narx 300 000 so'mdan YUQORI — botda 300k+ xaridga yetkazib berish
BEPUL (FREE_DELIVERY_THRESHOLD), bu xaridorni rag'batlantiradi.
Narx, nom va rasm manzillari Uzum Market'dan (images.uzum.uz CDN) olingan.
"""

import logging

from app import storage
from app.seed_bikes import seed_products

logger = logging.getLogger(__name__)

# Do'konni aniqlash uchun: nom "ProMan Electronics" (kichik harf bilan tekshiriladi).
_SELLER_SHOP_NAME = "proman electronics"

_IMG = "https://images.uzum.uz/{}/t_product_540_high.jpg"

# (nom, tavsif, narx so'm, [Uzum rasm ID lari]) — har birida 3 ta rasm.
_PRODUCTS = [
    ("Changyutgich Samsung PSR-433, 4000 Vt",
     "Samsung PSR-433 kuchli changyutgich, 4000 Vt quvvat. Uy va ofis uchun — "
     "kuchli so'rish va qulay tozalash.",
     1249000, ["d6fknjrvgbklj92hkai0", "d6b0dptv2sjhfufi6je0", "d6766pvqkmalqfnb3hig"]),

    ("Changyutgich Power Cyclone 3400 Vt, qopsiz",
     "3400 Vt quvvatli changyutgich, 3 litrli stakanli (qopsiz), teleskopik "
     "trubka va HEPA filtri bilan.",
     659990, ["d8436ac9g1ktqmln61og", "d8436absv8vo2t0f3740", "d8436a21146tv070m3ng"]),

    ("Mikroto'lqinli pech Midea MM 720C2MV-B, 20 L",
     "Midea MM 720C2MV-B mikroto'lqinli pech, 20 litr, 8 ta dastur, bug' bilan "
     "tozalash tizimi.",
     888000, ["d7k75trsv8vghom2a9o0", "d7k75t21146ojv9go0j0", "d7k75t3sv8vghom2a9n0"]),

    ("Mikroto'lqinli pech LG MS2042, 20 L",
     "LG MS2042 mikroto'lqinli pech, 20 litr, i-Wave texnologiyasi — tez va bir "
     "tekis isitadi.",
     1399000, ["d8jbn8bsv8vo2t0ki7ig", "d8jbnbbsv8vo2t0ki7l0", "d8jvugrsv8vo2t0kpqag"]),

    ("Multivarka Sonifer SF-1505, 600 Vt",
     "Sonifer SF-1505 ko'p funksiyali multivarka, 600 Vt, bug'da pishirish — "
     "kichik oilalar uchun qulay.",
     319000, ["d6g8c0jvgbklj92hu14g", "d6g8cai1146jevjr7mq0", "d6g8c0bvgbklj92hu140"]),

    ("Aerogril BOMA 8–14 L, 2600 Vt",
     "BOMA 8–14 litrli aerogril, 2600 Vt, ikkita savatli, 8–12 dastur — yog'siz, "
     "sog'lom va tez pishirish.",
     1000000, ["d7qqi421146tv06srhm0", "d7l4mt8i00ag7tp7noog", "d7melci1146tv06r0ap0"]),

    ("Aerogril Deime 6–10 L, 1800 Vt",
     "Deime aerogril, 6–10 litr, 1800 Vt — yog'siz qovurish uchun ko'p funksiyali "
     "havoli fritюрница.",
     1050000, ["d79sq7q1146ojv9cdckg", "d0bksclpb7f4kq791pdg", "d3c38dt2lln30qq3uleg"]),

    ("Go'sht maydalagich Sofaner SF-312, 4000 Vt",
     "Sofaner SF-312 elektr go'sht maydalagich, 4000 Vt quvvat, kolbasa va qiyma "
     "nasadkalari bilan.",
     399000, ["d64av0bvgbkv4qpqtei0", "d64b8sjvgbkv4qpqtk1g", "d64bdks3obpn7570k6og"]),

    ("Planetar mikser BOMA BM-6004, 6 L, 1500 Vt",
     "BOMA BM-6004 planetar mikser, 6 litr, 1500 Vt — xamir va krem uchun oshxona "
     "kombayni.",
     967000, ["d7rjblq1146tv06t5u90", "d7rjc53sv8vo2t0bimqg", "d7rjcd3sv8vo2t0bin0g"]),

    ("Suv isitgich Ziffler 50/80 L (boyler)",
     "Ziffler 50/80 litrli elektr suv isitgich (boyler) — uy uchun ishonchli va "
     "tejamkor isitish qozoni.",
     1297900, ["d83bspk9g1ktqmlmsl8g", "d83bt721146tv070cf70", "d83bspk9g1ktqmlmsl80"]),

    ("Sensorli elektr plita",
     "Sensorli elektr plita — tez qiziydi, oson boshqariladi, oshxona uchun "
     "ixcham va qulay yechim.",
     790000, ["cr84funiraat934rhspg", "cr84g0dbnta1ogm7o2dg", "cqnu1kkqvsse8leuj8n0"]),

    ("Televizor Artel A32PHCH010 Smart, HD, Google TV",
     "Artel A32PHCH010 Smart televizor, HD, Google TV — ovozli qidiruv va "
     "ilovalar bilan.",
     1755000, ["d2o434r4eu2h0tmpe0pg", "cv01rq3vgbkm5ehh5edg", "ctl4o3mi4n368aadafpg"]),

    ("Televizor TCL 43\" S5400A Full HD Smart",
     "TCL 43 dyuym S5400A Full HD Smart televizor, Dolby Audio, HDR10 — uy "
     "kinoteatri uchun.",
     2999000, ["crlfvbgj5no2jr72rrhg", "crlfusijot51rkb1sv70", "crlfuskhug2lhicncm3g"]),

    ("Smartfon Samsung Galaxy A17, 6/128 GB",
     "Samsung Galaxy A17 smartfon, sAMOLED 90 Hz ekran, 50 MP kamera, 5000 "
     "mA/soat batareya, 25 Vt quvvatlash.",
     2499000, ["d395anj4eu2s0bgjc9d0", "d395bld2llnbilepi4b0", "d395ctg9oh640qb7p1tg"]),

    ("Smartfon Xiaomi Redmi Note 15, 108 MP",
     "Xiaomi Redmi Note 15, 6.77\" FHD+ AMOLED ekran, 108 MP kamera, 6000 mA/soat "
     "batareya.",
     2699000, ["d622vknqkmamvfqt0b2g", "d622sinqkmamvfqt09ng", "d62rlr43obpn756vumpg"]),

    ("Noutbuk HP AMD Ryzen 5-7520U, 15.6\" FHD",
     "HP noutbuk: AMD Ryzen 5-7520U, 8 GB DDR5, 512 GB SSD, 15.6\" FHD ekran, "
     "Windows 11 — ish va o'qish uchun.",
     5888000, ["d4rrl33tqdhgicat60rg", "d2eq5mfiub3brtuame1g", "d5uesc6f4hvsl3r1rhi0"]),

    ("Aqlli fitnes braslet HUAWEI Band 11",
     "HUAWEI Band 11 aqlli fitnes brasleti, 1.62\" AMOLED ekran, yurak urishi va "
     "uyqu kuzatuvi.",
     619000, ["d8gkiajsv8vo2t0jgpmg", "d8gkj5q1146tv0753dqg", "d8h98cjsv8vo2t0jp2h0"]),

    ("Qahva mashinasi Sonifer SF-3575 (espresso)",
     "Sonifer SF-3575 ko'p funksiyali qahva mashinasi — espresso, latte va "
     "kapuchino tayyorlash uchun.",
     1399000, ["d5f9ei3tqdhjp1vei7i0", "d3a2h7l2lln52upub0g0", "d5f9ea8jsv1neactam5g"]),

    ("Bug'li dazmol Arshia AS2108-9025, 2.2 L",
     "Arshia AS2108-9025 bug'li dazmol, 2.2 litr — kuchli bug', kiyimni tez va "
     "silliq dazmollaydi.",
     599000, ["cs3qbhs0u44g6joreoo0", "ctffk245j42dmkoj13eg", "d1rnddfnrko24u2h4j70"]),

    ("Robot changyutgich Polaris PVCR 3600 Wi-Fi",
     "Polaris PVCR 3600 Wi-Fi robot changyutgich — quruq va nam tozalash, "
     "ilovadan boshqariladi.",
     1799000, ["d1eg420s9rf9j55t56o0", "d1eg43a1146jmb900g0g", "d1eg440s9rf9j55t56p0"]),

    ("Proyektor HY300 Pro Android 13, Wi-Fi",
     "HY300 Pro Android 13 proyektor, Wi-Fi — film va uy videolarini katta "
     "ekranda ko'rish uchun.",
     382000, ["d8kdhhs9g1ktqmlt133g", "d8kdhlk9g1ktqmlt135g", "d8kdpd49g1ktqmlt152g"]),

    ("Wi-Fi router Xiaomi AX3000T, Wi-Fi 6, Mesh",
     "Xiaomi AX3000T Wi-Fi 6 router, 3000 Mbit/s, Mesh qo'llab-quvvatlash — tez "
     "va barqaror internet.",
     549000, ["cmn26mbifoubkc6oubtg", "d3ae13a1146g78h3ki6g", "conjq5nj2e4ghqnp38gg"]),

    ("Gaz plitasi Ferre LP 60G, 3 gaz + 1 elektr",
     "Ferre LP 60G gaz plita: 3 ta gaz + 1 ta elektr konforka, pechli — oilaviy "
     "oshxona uchun.",
     2199000, ["d409em6j76ol453d410g", "d409equj76ol453d412g", "d409eqtv2sjj05ors9c0"]),

    ("Monitor Premier PRM120 24–27\", IPS, 120 Hz",
     "Premier PRM120LEDM monitor, 24–27\", IPS, 120 Hz, Full HD, HDMI+VGA — ish "
     "va o'yin uchun.",
     1050000, ["d6kv53dsp2tohdbclokg", "d6kv575sp2tohdbclol0", "d6kv58dsp2tohdbclolg"]),

    ("Printer Epson L3250 Wi-Fi (3 in 1)",
     "Epson L3250 Wi-Fi rangli printer-skaner-kopya (3 in 1) — uy va ofis uchun "
     "tejamkor.",
     2499000, ["d8an1qs9g1ktqmlpldd0", "d7qpv7c9g1ktqmljb3vg", "d7qpv8s9g1ktqmljb41g"]),
]


def _find_proman_seller():
    """ProMan Electronics do'konini nom bo'yicha topadi (nomida 'proman' bo'lsa)."""
    for sid, s in storage.get_sellers().items():
        name = str(s.get("shop_name", "")).strip().lower()
        if name == _SELLER_SHOP_NAME or "proman" in name:
            return int(sid), s
    return None


def seed_proman() -> int:
    """ProMan Electronics do'koniga mahsulotlarni (yo'q bo'lsa) qo'shadi."""
    return seed_products(_PRODUCTS, _find_proman_seller, "ProMan Electronics")
