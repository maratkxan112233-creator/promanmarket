"""Bir martalik xavfsiz "seed": DinamoKids do'koniga bolalar aravachalari
(kolyaska) qo'shadi.

Bot ishga tushganda chaqiriladi. Do'konni topish, qo'shish va MAVJUD
mahsulotlar rasmlarini yangilash mantig'i [seed_bikes.seed_products] da —
shu yerdan qayta ishlatiladi. Mahsulot allaqachon bo'lsa takror qo'shilmaydi.

Mahsulotlar Instagram'dagi @dinamo_kids_market do'konining eng ko'p reklama
qiladigan toifasi — kolyaskalar. Nom, narx va rasmlar Uzum Market'dan
(images.uzum.uz CDN) olingan. Jami 34 ta: sayr (progulochnaya), transformer
(2 va 3 in 1), dron-aravacha (360° aylanadigan), hassa/tayoqcha (yengil
sayohat), egizaklar uchun va premium modellar.
"""

import logging

from app.seed_bikes import _find_seller, seed_products

logger = logging.getLogger(__name__)

# (nom, tavsif, narx so'm, Uzum rasm ID)
_STROLLERS = [
    # ── Yengil / sayohat aravachalari (hassa, tayoqcha) ─────────────────────
    ("Sayohat uchun chaqaloq aravachasi (tayoqcha)",
     "Yengil tayoqcha (hassa) aravacha — sayohat va kundalik sayr uchun. Ixcham "
     "yig'iladi, kam joy egallaydi. Yangi tug'ilgan chaqaloqlardan boshlab.",
     361228, "d6tpiu3sv8vlb6mhk910"),
    ("Bolalar hassa aravachasi, sayr uchun",
     "Yengil hassa (sayr) aravachasi — bir harakat bilan yig'iladi. Shahar "
     "sharoitida va sayohatda olib yurish uchun qulay.",
     382190, "d77nloq1146ojv9bh63g"),
    ("Bolalar sayr aravachasi, hassa, sayohat uchun",
     "Yengil va ixcham sayr aravachasi — hassa turidagi, sayohat uchun "
     "mo'ljallangan. Oson yig'iladi va ochiladi.",
     391990, "d3vfsv6j76ol453cri5g"),
    ("Sayr aravachasi \"Qamish\", yig'iluvchi mexanizmli",
     "Bolalar uchun sayr qilish aravachasi, yig'iluvchi mexanizm bilan. Yengil "
     "ramka, qulay o'rindiq — kundalik sayrlar uchun.",
     449820, "cpijrqnfrr82f0a62h90"),

    # ── Dron-aravachalar (360° aylanadigan o'rindiq) ────────────────────────
    ("Mini dron-aravacha 0-2 yosh, 360° aylanadi",
     "0-2 yoshli bolalar uchun mini dron aravachasi — o'rindig'i 360 darajaga "
     "aylanadi, orqa qismi (suyanchig'i) sozlanadi. Yengil va ixcham.",
     528220, "cuqu8aei4n32hnc2e0qg"),
    ("Dron-aravacha 0-4 yosh, 360° aylanadi",
     "0-4 yoshli bolalar uchun dron aravachasi — o'rindig'i 360° buriladi, "
     "orqasi sozlanadi. Bolaning yuzini onaga yoki yo'lga qaratish mumkin.",
     832020, "d5ka0m8jsv1q0h27n650"),
    ("Dron-aravacha PHOENIX K-1, yig'iladigan",
     "PHOENIX K-1 dron-aravachasi — yengil, yig'iladigan, sayohat uchun. "
     "O'rindiq aylanadi, mustahkam ramka. Ommabop model.",
     930020, "d11srfa7s4fq7e8ucgp0"),
    ("Dron-aravacha A8 model",
     "A8 model bolalar dron-aravachasi — aylanadigan o'rindiq, sozlanadigan "
     "suyanchiq. Yengil alyumin ramka, sayr va sayohat uchun.",
     783020, "d82oesi1146tv07044k0"),

    # ── Butun mavsum / sayr aravachalari ────────────────────────────────────
    ("Bolalar aravachasi - tez va oson yig'iladi",
     "Bolalar aravachasi — bir harakatda tez va oson yig'iladi. Yengil, "
     "kundalik sayr uchun qulay va ishonchli.",
     577220, "d8h6k221146tv075ab0g"),
    ("Buklanadigan yengil aravacha (sayohat)",
     "Bolalar aravachasi — buklanadigan, yengil, juda ixcham. Sayohat uchun "
     "ideal: chamadonga ham sig'adi.",
     568302, "cukh1ilht56sc95dthl0"),
    ("Aravacha, oson yig'ish va sozlash (3 yoshgacha)",
     "Bolalar aravachasi — oson yig'ish va sozlash imkoniyati bilan, 3 "
     "yoshgacha. Qulay suyanchiq va mustahkam g'ildiraklar.",
     568390, "d846dd3sv8vo2t0f5cpg"),
    ("Bolalar aravachasi Adil, butun mavsum (0-3)",
     "Adil bolalar aravachasi — butun mavsum uchun, yig'iladigan, 0-3 yosh. "
     "Issiq va salqin havoga moslashadi, mustahkam.",
     729580, "d0u269gn274lpu37mjv0"),
    ("Bolalar aravachasi Adil, butun mavsum, yig'iladigan",
     "Adil aravacha — butun mavsum uchun, yig'iladigan, 0-3 yoshgacha. Yengil "
     "ramka, qulay tutqich va keng savatcha.",
     774200, "d0u26tq7s4fo7mqbr270"),
    ("Bolalar aravachasi Adil, butun mavsum, yurish uchun",
     "Adil aravacha — butun mavsum, sayr va yurish uchun. Mustahkam quvurli "
     "ramka, amortizatorli g'ildiraklar, keng o'rindiq.",
     881020, "d6ejpd7qkmak8dt8ejb0"),
    ("Barcha fasllar uchun bolalar kolyaskasi (kulrang)",
     "Barcha fasllar uchun bolalar kolyaskasi — kulrang. Issiq qoplama, "
     "yomg'irdan himoya, qulay suyanchiq sozlamalari.",
     754600, "d2q431r4eu2h0tmpt9dg"),
    ("Barcha fasllar uchun bolalar kolyaskasi (sarg'ish)",
     "Barcha fasllar uchun bolalar kolyaskasi — sarg'ish. To'liq jihozlangan: "
     "issiq xalta, savatcha va himoya soyaboni bilan.",
     823200, "d2q3var4eu2h0tmpt8ag"),
    ("Bolalar sayr aravachasi 2 in 1, musiqa va fara bilan",
     "Bolalar sayr aravachasi — yig'iladigan, 2 tasi 1 da transformer. Musiqa "
     "va fara (chiroq) bilan, qulay va zamonaviy.",
     636990, "d32odcniub35i07l24p0"),

    # ── Transformer (2-in-1, 3-in-1) aravachalar ────────────────────────────
    ("Easywalker Harvey 3 transformator, 2 in 1",
     "Katta sumkali Easywalker Harvey 3 aravachasi — transformator, 2 dan 1 "
     "gacha. Yotoq blok va sayr o'rindig'i, premium dizayn.",
     783020, "d3b8dkt2lln30qq3n720"),
    ("Transformer aravacha, katta sumkali",
     "Transformer bolalar aravachasi — katta (ona) sumkasi bilan. 2 in 1: "
     "yotoq va sayr rejimi. Mustahkam va keng.",
     1097982, "d5jphcbs2tab83sbuuk0"),
    ("Katta sumkali aravacha transformeri",
     "Katta sumkali bolalar aravachasi — transformer. Yangi tug'ilgan "
     "chaqaloqdan boshlab: yotoq blok va sayr o'rindig'i bir komplektda.",
     882000, "d5i1gc0jsv1q0h26v240"),
    ("Katta sumkali transformer kalyaska",
     "Bolalar aravachasi — katta sumkali, transformer kalyaska. To'liq "
     "komplekt: issiq xalta, soyabon va ona sumkasi bilan.",
     1609561, "cvsie2mi4n37npao719g"),
    ("Start joy ST-03, qaytariladigan tutqichli",
     "Start joy ST-03 aravachasi — qaytariladigan (perekidnoy) tutqich bilan: "
     "bolani onaga yoki yo'lga qaratish mumkin. Yengil va qulay.",
     734020, "d39o5gd2lln52upu63n0"),
    ("Start joy ST-09 transformator, katta sumka bilan",
     "Start joy ST-09 transformator aravachasi — katta sumka bilan. "
     "Qaytariladigan tutqich, yotoq rejimi, amortizatorli g'ildiraklar.",
     930020, "d39tk5d2lln52upu8tr0"),
    ("Start Jop ST-09 transformator (katta sumkali)",
     "Start Jop ST-09 transformator aravachasi — katta sumkali. 2 in 1 "
     "tizim: chaqaloq yotog'i va sayr o'rindig'i. Mustahkam ramka.",
     921690, "d0cthhi7s4fo7mq81f30"),
    ("Transformer aravacha KIDILO K-08",
     "KIDILO K-08 transformer aravachasi — yotoq va sayr rejimlari. Qulay "
     "suyanchiq, keng savatcha, sifatli g'ildiraklar.",
     881020, "d2k81n34eu2g1liv30a0"),

    # ── Kidilo brendi (chamadon, aylanuvchi, premium) ───────────────────────
    ("Bolalar chamadon aravachasi Kidilo 535",
     "Kidilo 535 chamadon aravachasi — chamadondek yig'iladi, samolyotga olib "
     "chiqsa bo'ladi. Yengil, ixcham, sayohat uchun ideal.",
     783020, "d56dsdbs2tab83s89ag0"),
    ("Bolalar aylanuvchi aravacha Kidilo 535",
     "Kidilo 535 aylanish aravachasi — o'rindiq buriladi, perekidnoy tutqich. "
     "Chamadondek yig'iladi, 0-3 yosh bolalar uchun.",
     783020, "d2jf4bfiub35i07h2ks0"),
    ("Bolalar aravachasi Kidilo M9",
     "Kidilo M9 bolalar aravachasi — zamonaviy dizayn, qaytariladigan "
     "tutqich, yengil ramka. Sayr va sayohat uchun qulay.",
     783020, "d8ko2brsv8vo2t0l46f0"),
    ("Bolalar aravachasi Kidilo C6 (0-22 kg)",
     "Kidilo C6 aravachasi — 0-22 kg gacha, yengil va yig'iladigan kolyaska. "
     "Bola katta bo'lguncha xizmat qiladi, mustahkam.",
     668467, "d5bmttbtqdhjp1vdiv10"),
    ("Bolalar aravachasi Kidilo H2D, transformer",
     "Kidilo H2D aravachasi — transformer, tutqichi oldiga otadi (perekidnoy). "
     "Premium komplekt, yumshoq amortizatsiya, keng o'rindiq.",
     1254468, "cs6u6fm9ucrd5cir4il0"),

    # ── Egizaklar va premium ────────────────────────────────────────────────
    ("Egizaklar uchun aravacha (kalyaska)",
     "Egizaklar (ikki bola) uchun aravacha — yonma-yon ikki o'rindiq. "
     "Mustahkam ramka, mustaqil sozlanadigan suyanchiqlar.",
     1152607, "d6g20a8s9rfd9u945nmg"),
    ("Anex air-Q kolyaska (Polsha brendi)",
     "Anex air-Q bolalar aravachasi — Polsha brendi, premium sifat. Sayr "
     "qilish uchun, yengil va zamonaviy. Eksklyuziv model.",
     4277700, "d7te7ik9g1ktqmlkdddg"),

    # ── 3 in 1 (aravacha + tolokar + tebranuvchi) ───────────────────────────
    ("3 in 1 otcha-aravacha (tolokar, tebranuvchi)",
     "Bolalar uchun 3 in 1 otcha mashina — tebranuvchi (kachalka), tolokar "
     "tutqichli va xavfsizlik kamari bilan. O'yin va sayr bir vaqtda.",
     360640, "d8820ejsv8vo2t0gkvl0"),
]


def seed_strollers() -> int:
    """Bolalar aravachalarini DinamoKids do'koniga qo'shadi/yangilaydi."""
    return seed_products(_STROLLERS, _find_seller, "kolyaskalar")
