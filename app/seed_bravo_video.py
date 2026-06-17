"""Bir martalik xavfsiz "seed": Bravo electronics do'koniga VIDEO'dagi mahsulotlar.

Foydalanuvchi yuborgan do'kon videolaridan aniqlangan mahsulotlar. Har bir
mahsulot nomi, tavsifi, narxi va RASMLARI (har biri kamida 3 ta) Uzum Market'dan
(uzum.uz) olingan — narx chegirmali (joriy) narx, rasmlar esa mahsulotning o'z
galereyasidan (images.uzum.uz CDN).

Bot ishga tushganda chaqiriladi. Do'konni telefon yoki nom bo'yicha topadi va
mahsulotlarni faqat HALI YO'Q bo'lsa qo'shadi — takror qo'shilmaydi, mavjudlariga
tegmaydi (mantiq [seed_bikes.seed_products] da, qayta ishlatiladi).

Avtomat va Hofmann/QLT/JPE kir yuvish mashinalari [seed_ac] da (ko'p rasmga
yangilangan) — bu yerda video'dagi QOLGAN toifalar: yarim avtomat (ELITE/Artel),
vitrina sovutkich/muzlatgich, gaz pishirish panellari, suv purkagichli ventilyator,
kir quritgichlar va deraza chivin to'ri.
"""

import logging

from app.seed_ac import _find_bravo_seller
from app.seed_bikes import seed_products

logger = logging.getLogger(__name__)

# (nom, tavsif, narx so'm, Uzum rasm ID yoki ID lar ro'yxati)
_VIDEO_PRODUCTS = [
    # ── Yarim avtomat kir yuvish mashinalari (video: ELITE, Artel) ───────────
    ("Yarim avtomat kir yuvish mashinasi ELITE WM-5168, 10 kg",
     "Ikki barabanli (yuvish + siqish) yarim avtomat kir yuvish mashinasi, 10 kg, "
     "3 yil kafolat — tejamkor va ishonchli.",
     1474110, ["d72arjjsv8vlb6mj5b60", "d5g7fkbs2tab83san1dg",
               "d5g7flbtqdhodfdkmij0", "d5g7fmjs2tab83san1f0"]),
    ("Yarim avtomat kir yuvish mashinasi Artel ART-TG70FP, 7 kg",
     "Ikki barabanli yarim avtomat kir yuvish mashinasi, 7 kg, to'kish-siqish va "
     "quritish — kundalik foydalanish uchun qulay.",
     1484010, ["cvmfel5pb7fbmqmlvse0", "d2p8svl2llnd6jujssb0", "d2p8t0l2llnd6jujssbg"]),

    # ── Vitrina sovutkich / muzlatgich (video: ENERGY/dobon kabi) ───────────
    ("Vitrina sovutkichi Artel HS 520SN, 400 litr",
     "Tik (vertikal) shisha eshikli vitrina sovutkichi, 400 litr — ichimlik va "
     "mahsulotlarni ko'rsatib sovutish uchun do'kon va kafelarga mos.",
     6632010, ["d04tfotpb7f46s8873vg", "cvvled47fd1p445t07dg",
               "d2sjvmb4eu2h0tmqgd1g", "d2sjvnj4eu2h0tmqgd4g"]),
    ("Vitrina uchun muzlatgich Kleo VS 390 T, 365 litr",
     "Tik shisha eshikli vitrina muzlatgich, 365 litr — savdo nuqtalari uchun "
     "ko'rinadigan sovutish vitrinasi.",
     5345010, ["d0m30j0n274j5scnis90", "d0hgkej3uvph509tu910", "d0hgkegn274j5scmhh00",
               "cq8g634sslotj05k92sg", "cq8g43csslotj05k9270"]),

    # ── O'rnatiladigan gaz pishirish panellari (video: 4 ko'zli plitalar) ───
    ("Pishirish paneli Artel Moderno A64-0030 INOX",
     "O'rnatiladigan gaz pishirish paneli (varochnaya panel), zanglamas po'lat "
     "(INOX) sirt, oshxona stoliga o'rnatiladi.",
     1286010, ["d7o9hi3sv8vo2t0a67dg", "d7o9hf3sv8vo2t0a678g", "d7o9hgbsv8vo2t0a67bg"]),
    ("Pishirish paneli Hofmann CTBS631CIXS/HF (3 gaz + 1 elektr)",
     "Kombinatsiyalangan o'rnatiladigan pishirish paneli — 3 ta gaz va 1 ta elektr "
     "gorelka, zamonaviy dizayn.",
     1632510, ["d8ohlak9g1ktqmlunq2g", "d8ohlajsv8vo2t0mkcd0", "d8ohlai1146tv0786t10"]),

    # ── Suv purkagichli (tornado) ventilyator (video: turuvchi ventilyator) ─
    ("Suv purkagichli ventilyator, 40 litr",
     "40 litrli suv bakli turuvchi (pol) ventilyator — issiqda suv purkab "
     "havoni sovutadi, ochiq va keng joylar uchun samarali.",
     2871000, ["d8hhf249g1ktqmls0u40", "d18m7o0n274lpu39sh5g",
               "d18m7p33uvppu2ac8n90", "d18m7p0n274lpu39sh6g"]),

    # ── Kir quritgichlar (video: buklanadigan sushilkalar) ──────────────────
    ("Kir quritgich, yig'ma, polda o'rnatiladigan, g'ildirakli",
     "Polga qo'yiladigan buklanadigan kir quritgich, g'ildirakli — oson "
     "yig'iladi va siljitiladi, ko'p kir sig'adi.",
     455400, ["d8eletq1146tv074al6g", "d8eldsk9g1ktqmlqqtrg", "d8eldsjsv8vo2t0io690",
              "d8eldss9g1ktqmlqqts0", "d8cm8kjsv8vo2t0i3060"]),
    ("Kiyim quritgich, 3 qavatli, po'latdan, g'ildirakli",
     "Uch qavatli po'lat kiyim quritgich, g'ildirakli va buklanadigan — ko'p "
     "joy tejaydi, mustahkam.",
     432204, ["d7o3u921146tv06rlcrg", "d7o3u749g1ktqmli5eng", "d7pcpejsv8vo2t0akoq0",
              "d7pcpf49g1ktqmlinpg0", "d7pcpf21146tv06s7sh0"]),

    # ── Deraza chivin to'ri (video: moskit setka) ───────────────────────────
    ("Deraza uchun chivin to'ri (o'z-o'zidan yopishadigan)",
     "Derazaga mahkamlash lentasi bilan o'rnatiladigan chivinga qarshi to'r — "
     "chivin, pashsha va hasharotlardan himoya qiladi.",
     24500, ["d8m3rs21146tv0778tlg", "d8m48la1146tv0779460",
             "d8m48nrsv8vo2t0lmib0", "d8m48rs9g1ktqmltppb0"]),

    # ── Mikroto'lqinli pechlar (video: do'kon javonlarida ko'plab pech) ──────
    ("Mikroto'lqinli pech Artel MM20S01, 20 litr, 700 Vt",
     "20 litrli mikroto‘lqinli pech, 700 Vt quvvat — isitish va eritish uchun "
     "qulay, ixcham va ishonchli.",
     930020, ["d2slam34eu2h0tmqh260", "d2slak7iub35i07je4tg", "d2slb7viub35i07je570",
              "d2slcer4eu2h0tmqh350", "d2slc2r4eu2h0tmqh2ug"]),
    ("Mikroto'lqinli pech Bench BM-M20W02RB/RW, 20 litr",
     "Bench 20 litrli mikroto‘lqinli pech, mexanik boshqaruv — uy va ofis uchun "
     "tejamkor variant.",
     636020, ["d1ooqjvnrkoeo1hjvagg", "d055u7k7fd1idphtihn0", "d055u247fd1idphtihm0"]),
    ("Mikroto'lqinli pech Goodwell GMF, 20-23 litr, qora shisha",
     "Goodwell mikroto‘lqinli pech, 20-23 litr, qora shisha sirt — zamonaviy "
     "dizayn, oson tozalanadi.",
     783020, ["d6sibuq1146lmcd37820", "d6sibuq1146lmcd3782g",
              "d1ies50jsv1jqvb7eeq0", "d1ies50jsv1jqvb7eepg"]),

    # ── Suv sovutgich / kuler (video: oq-qora tik kulerlar) ─────────────────
    ("Suv sovutgichi WellStars, 3 rejimli (issiq/xona/sovuq)",
     "Tik turuvchi suv kuleri (dispenser), 3 rejim — issiq, xona va sovuq suv. "
     "Yuqoridan ballon o‘rnatiladi, ofis va uy uchun.",
     791010, ["d4i3njdv2sjnqk4ilba0", "d4i3njdv2sjnqk4ilb9g",
              "d4i3njej76ooegrmragg", "d425hcdsp2tj49o7q5og"]),

    # ── Muzlatgich (video: bir va ikki kamerali sovutgichlar) ───────────────
    ("Muzlatgich Ferre BCD-275, 225 litr, ikki kamerali",
     "Ikki kamerali maishiy sovutgich, 225 litr — yuqori sifat, tejamkor va "
     "keng saqlash hajmi.",
     2335410, ["d8nug1bsv8vo2t0mcqcg", "cmjphfbifoubkc6ocipg", "cmjphf925ku8ad8ho5ig",
               "cmjphb9s99ouqbfqv0pg", "cppckej6eisq2rkco4bg"]),
    ("Sandiq muzlatgich Biryusa 260KX, 240 litr",
     "Yopiq qopqoqli sandiq (lar) muzlatgich, 240 litr — muzqaymoq va ko'p "
     "mahsulot saqlash uchun, savdo nuqtalariga ham mos.",
     2969010, ["d6inv7i1146k64hufgv0", "d6invggs9rf3gtpkos4g",
               "cphi25vfrr82f0a5scfg", "cphi25u0t1llbtq5tvj0"]),

    # ── Erkin turuvchi gaz plita (video: duxovkali plitalar) ────────────────
    ("Gaz plitasi Artel Apetito 02-G, duxovkali, 4 ko'zli",
     "Erkin turuvchi gaz plita, 4 ko'zli va duxovkali (pech) — to'liq taom "
     "tayyorlash uchun, mustahkam va chiroyli.",
     3493858, ["d6hta8gs9rfd9u94uvvg", "d6hta8i1146jevjrsfl0", "d6hta8i1146jevjrsflg",
               "d6hta8gs9rfd9u94uvv0", "d6hta8jvgbklj92iika0"]),

    # ── Elektr choynak (video: Boinman elektr choynaklar) ───────────────────
    ("Elektr choynak HAN RIVER, 2.3 litr, metall",
     "Zanglamas po'lat elektr choynak, 2.3 litr — tez qaynaydi, avtomatik "
     "o'chish funksiyasi bilan.",
     107800, ["d13qrta7s4fr083f18og", "d13qsfa7s4fr083f18ug", "d13qsc8n274lpu38ofg0",
              "d13qse0n274lpu38ofh0", "d13qsbi7s4fr083f18tg"]),

    # ── Tarozi (video: elektron tarozi) ─────────────────────────────────────
    ("Aqlli pol tarozi Xiaomi Mi Smart Scale 2, 180 kg",
     "Xiaomi aqlli elektron tarozi, 180 kg gacha, ilova bilan bog'lanadi — "
     "vazn va tana ko'rsatkichlarini o'lchaydi.",
     260930, ["d7sap03sv8vo2t0bsni0", "cpvanjj6eisq2rkdugb0", "d7saovjsv8vo2t0bsnhg",
              "d7sap021146tv06tg1qg", "d7sap1c9g1ktqmljvsag"]),

    # ── Turuvchi ventilyator (video: oyoqli ventilyatorlar) ─────────────────
    ("Oyoqli ventilyator LAMO, masofadan boshqaruvli",
     "Balandligi rostlanadigan oyoqli (pol) ventilyator, pultli boshqaruv — "
     "kuchli havo oqimi, uy va ofis uchun.",
     484110, ["d8kp3lbsv8vo2t0l4km0", "d8kp3eq1146tv076nblg", "d8kp3i49g1ktqmlt7p5g"]),

    # ── Metall javon / etajerka (video: g'ildirakli javonlar) ───────────────
    ("Metall etajerka GHY2402, g'ildirakli, 3 qavatli",
     "G'ildirakli yig'ma metall etajerka (tokcha) — oshxona, hammom va xona "
     "uchun, oson siljitiladi va ko'p narsa sig'adi.",
     343000, ["d3r1c0bs2ta8m27ejudg", "ctplq26i4n324lr1rs2g", "ctplq245j42bjc4606ug",
              "ctplq1tht56ksubb532g", "ctplq25ht56ksubb5330"]),
]


def seed_bravo_video() -> int:
    """Video'dan aniqlangan mahsulotlarni Bravo electronics do'koniga qo'shadi."""
    return seed_products(_VIDEO_PRODUCTS, _find_bravo_seller, "video mahsulotlari (Bravo)")
