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

    # === 2-to'plam: Uzum'da oxirgi kunlarda eng ko'p sotilgan 200 000–350 000
    # so'mlik 25 mahsulot (mashhurlik bo'yicha). Narx va 3 rasm Uzum'dan olingan.
    ("Bug'li dazmol RAF HY, 2600 Vt, keramik",
     "RAF HY bug'li dazmol, 2600 Vt, keramik qoplamali tovon — kiyimni tez va "
     "silliq dazmollaydi.",
     245520, ["d5ii8ijtqdhu87jrmsa0", "cud195c5j42bjc4b6970", "d5ii8irtqdhu87jrmsag"]),

    ("Elektr sharbat siqqich, oshxona kombayni",
     "Ko'p funksiyali elektr sharbat siqqich — meva va sabzavotdan tezda toza "
     "sharbat tayyorlaydi.",
     298900, ["d6kgs5dsp2tohdbcdip0", "d6kgur5sp2tohdbcdk10", "d6kguv21146th72sph7g"]),

    ("Qo'l blenderi Sokany, 5 tasi 1 da",
     "Sokany qo'l blenderi, 5 ta nasadkali: aralashtirish, maydalash va venchik — "
     "sho'rva, smuzi va qiyma uchun.",
     244020, ["d7jvrirsv8vghom28ch0", "d7jvtdk3obpkks11h39g", "d7jvt743obpkks11h390"]),

    ("Multivarka, 21 rejimli",
     "21 rejimli multivarka: bug'da pishirish, guruch, palov va tez pishirish — "
     "retseptlar kitobi bilan.",
     242060, ["d7pgeqs9g1ktqmlipoqg", "cts9b1tht56ksubbh850", "cts9b3mi4n324lr284q0"]),

    ("Induksion plita VITEK V-7031, 3800 Vt",
     "VITEK V-7031 induksion plita, sensorli, 3800 Vt, 4 rejim — uy va hovli uchun "
     "tez va xavfsiz pishirish.",
     262640, ["d4n8n8dsp2tr82i87k0g", "d4n8n6uj76olj6nfes20", "d4n8n6tsp2tr82i87ju0"]),

    ("Marwa elektr plita",
     "Marwa elektr plita — ixcham va tejamkor, choy qaynatish hamda ovqat pishirish "
     "uchun qulay.",
     222332, ["d88uehk9g1ktqmlp3dn0", "d88uehbsv8vo2t0h0oeg", "d88lmdjsv8vo2t0grrh0"]),

    ("Pol ventilyatori 50 sm, 100 Vt",
     "Polga qo'yiladigan ventilyator, 50 sm, 100 Vt, 5 parrakli, 3 tezlik — kuchli "
     "va jim sovutish.",
     246510, ["d84ulua1146tv071136g", "d84uluc9g1ktqmlngva0", "d84uluc9g1ktqmlngvag"]),

    ("Konditsioner deflektori 9-12",
     "Konditsioner uchun himoya ekran-deflektor (9-12 model) — sovuq havoni "
     "yo'naltiradi, to'g'ridan shamollashdan saqlaydi.",
     244530, ["cpe1cbrmdtjnp737v950", "cg9cshnhj8j9g69a3q50", "cg9cshng49devoaapb20"]),

    ("Stol ventilyatori, 3 tezlikli",
     "Stol ustiga qo'yiladigan ventilyator, 3 tezlik, jim ishlaydi — uy va ofis "
     "uchun energiya tejamkor.",
     245025, ["d6vs51a1146ojv988ndg", "d6n61hlsp2tohdbdf0cg", "d3manjrq345l7k05pucg"]),

    ("Vakuumator + 50 ta paket",
     "Vakuum paket yopishtirgich (vakuumator), 50 ta paket bilan — mahsulotni "
     "havosiz, uzoq muddat saqlash uchun.",
     244020, ["d87bm921146tv071uul0", "d87bm93sv8vo2t0gc0gg", "d87bm921146tv071uukg"]),

    ("Portativ mini kir yuvish mashinasi",
     "Yig'ma portativ mini kir yuvish mashinasi — kichik kiyim, sayohat va ijara "
     "uy uchun qulay yechim.",
     296010, ["d846saq1146tv070ohpg", "d846sas9g1ktqmln8fc0", "d35q857iub30vbruct20"]),

    ("Bug'li tozalagich, 17 nasadkali",
     "Bug'li tozalagich (paroochistitel), 17 nasadka — uy, oshxona va hammomni "
     "kimyosiz, bug' bilan tozalaydi.",
     342054, ["d03onec7fd1idpht7sgg", "d03rm6k7fd1idpht8qsg", "d03rm6s7fd1idpht8qtg"]),

    ("Par dazmol SONIFER, bug'li",
     "SONIFER vertikal bug'li dazmol (parli) — osilgan kiyimni tez tekislaydi va "
     "dezinfeksiya qiladi.",
     341550, ["d58pukjtqdhjp1vd42d0", "d58pukbs2tab83s8tqgg", "d58pukgjsv1neacrrh80"]),

    ("Fotoepilyator, sovutish effektli",
     "Yuz va tana uchun professional fotoepilyator, sovutish effekti bilan — uyda "
     "ortiqcha tukni yo'qotish uchun.",
     290030, ["d7a2lsa1146ojv9cfsmg", "d7a2lsjsv8vlb6mmekbg", "d66jgu5sp2tk1m7i28fg"]),

    ("Soch dazmoli, taroqli stayler",
     "Taroqli soch dazmoli-stayler — sochni to'g'rilash va jingalak qilish uchun "
     "ko'p funksiyali keramik uskuna.",
     334640, ["ctbvoglpb7f7ago86al0", "ctbvogmi4n3ehka39keg", "d3dqog52lln30qq4cs50"]),

    ("Fen-taroq VGR V-498, 360 daraja",
     "VGR V-498 fen-taroq, 360 daraja aylanadi, keramik qoplama — quritish va "
     "turmaklash bir vaqtning o'zida.",
     271503, ["csgtruj4nkdhfdv7ffkg", "csb00m3vgbkl7noksong", "csb00m5pq3ghb2qk49bg"]),

    ("Simsiz trimmer VGR 107",
     "VGR 107 professional simsiz trimmer — soqol, mo'ylov va soch olish uchun, "
     "akkumulyatorli va ixcham.",
     252103, ["d4u2eljs2ta3qj5k6ltg", "d4u2el8jsv1o95ci0mjg", "d4u2elbs2ta3qj5k6lt0"]),

    ("Fen-stayler 7 in 1, barcha sochlar uchun",
     "7 in 1 fen-stayler — barcha turdagi sochlar uchun: quritish, to'g'rilash va "
     "jingalak nasadkalari bilan.",
     349200, ["d83v7321146tv070k5h0", "d83v8349g1ktqmln46d0", "d83v8349g1ktqmln46c0"]),

    ("Induksion plita Bosch, sensorli",
     "Sensorli induksion plita Bosch, 4 rejimli — uy va hovli uchun tez qizadigan "
     "zamonaviy elektr plita.",
     290080, ["d64m6bedd7e7njq7t0eg", "d7lnenbsv8vo2t08vtf0", "d7gr6ma1146ojv9f8oe0"]),

    ("Smart Watch x series, aqlli soat",
     "Aqlli soat (Smart Watch x series) — erkak va ayollar uchun: qadam, yurak "
     "urishi va telefon bildirishnomalari.",
     249900, ["d5pr8jmj76og35gk7080", "d52j8crs2tab83s75usg", "d5pr8j6j76og35gk7070"]),

    ("Wi-Fi router CPE 4G/5G, SIM kartali",
     "CPE Wi-Fi router, 4G/5G, SIM kartali, ikki diapazonli — uy va ofisga simli "
     "internetsiz tez Wi-Fi.",
     325710, ["cumtip45j42bjc4e3ql0", "cq72q7s0u44j0e4m79ag", "cq72q9k0u44j0e4m79bg"]),

    ("Tugmali telefon GM-B311V (Gusto 3)",
     "GM-B311V (Gusto 3) tugmali telefon, 2 SIM, 1.3 MP kamera, 800 mA·soat — sodda "
     "va ishonchli aloqa.",
     276210, ["d71aj5c3obpjedc3t380", "d71aj3k3obpjedc3t35g", "d71aj421146ojv98r3r0"]),

    ("Smart TV Box Android 4K, Wi-Fi",
     "Android Smart TV Box, 4K, Wi-Fi, IPTV — oddiy televizorni smart televizorga "
     "aylantiradi, ilovalar bilan.",
     266310, ["d6nq0o21146th72u1un0", "d6npu2i1146th72u1u3g", "d7esu8rsv8vlb6mobud0"]),

    ("O'yin pristavkasi Game Stick M15, 4K",
     "Game Stick M15 o'yin pristavkasi, 4K Ultra HD, mingdan ortiq retro o'yin — "
     "televizorga to'g'ridan ulanadi.",
     303930, ["cp27vf40u44tu6dpmb40", "cjmbkdcjvf2ofbh8a4dg", "cjmbkdcjvf2ofbh8a4d0"]),

    ("Simsiz quloqchin Hoco EQ27, ANC",
     "Hoco EQ27 simsiz quloqchin — ANC shovqin bostirish va AI tarjimon funksiyasi "
     "bilan, toza ovoz.",
     222130, ["d6ltaqi1146th72tc1ag", "d6ltav8s9rf3ubr02020", "d6ltb1i1146th72tc1h0"]),
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
