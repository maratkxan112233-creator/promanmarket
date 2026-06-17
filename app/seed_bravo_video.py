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
]


def seed_bravo_video() -> int:
    """Video'dan aniqlangan mahsulotlarni Bravo electronics do'koniga qo'shadi."""
    return seed_products(_VIDEO_PRODUCTS, _find_bravo_seller, "video mahsulotlari (Bravo)")
