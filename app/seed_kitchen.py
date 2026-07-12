"""Bir martalik xavfsiz "seed": ProMan Electronics do'koniga OSHXONA buyumlarini qo'shadi.

Bot ishga tushganda chaqiriladi. Do'kon nom bo'yicha topiladi va mahsulotlar
faqat HALI YO'Q bo'lsa qo'shiladi — bot necha marta qayta ishga tushsa ham
takror qo'shilmaydi va mavjud mahsulotlarga tegilmaydi.

Uzum Market'da ENG YAXSHI SOTILAYOTGAN 40 xil oshxona buyumi (2026-yil iyul
tahlili bo'yicha). Har birida 3 ta rasm. Narx, nom va rasm manzillari Uzum
Market'dan (images.uzum.uz CDN) olingan. Asosiy mezon: 300 000 so'mdan yuqori
narx (botda 300k+ xaridga yetkazib berish BEPUL). 4 ta buyum bundan arzon,
lekin Uzum'dagi eng ko'p sotilganlar qatoriga kirgani uchun qo'shildi.
"""

import logging

from app.seed_bikes import seed_products
from app.seed_proman import _find_proman_seller

logger = logging.getLogger(__name__)

_IMG = "https://images.uzum.uz/{}/t_product_540_high.jpg"

# (nom, tavsif, narx so'm, [Uzum rasm ID lari]) — har birida 3 ta rasm.
_PRODUCTS = [
    # ---------- Oshxona texnikasi ----------
    ("Toster Sonifer SF-6055, 2 bo'limli",
     "Sonifer SF-6055 tosteri — nonushtani bir daqiqada tayyorlaydi. Qizarish "
     "darajasi sozlanadi, ushlagichi qizimaydi.",
     362000, ["d4skgnrs2ta3qj5jlva0", "d4skh2js2ta3qj5jlvh0", "d4skh2bs2ta3qj5jlvgg"]),

    ("Vafli pishirgich Uakeen GERMANY, 7 tasi 1 da",
     "Uakeen ko'p funksiyali pishirgich — vafli, sendvich va tost uchun almashinadigan "
     "panellar. Yopishmaydigan qoplama, tez qiziydi.",
     699000, ["d5ua1k6f4hvsl3r1oi4g", "d5ua1juf4hvsl3r1oi40", "d5ua1jrq345o6s40kh8g"]),

    ("Toster-gril Sofaner, ochiq sirtli, 2200 Vt",
     "Sofaner kontakt grili, 2200 Vt — go'sht, sabzavot va lavash uchun. Ochiladigan "
     "sirt katta taomlarga ham qulay.",
     629000, ["d38hfnl2llnbilepcr3g", "d38hfsd2llnbilepcr60", "d38hfsj4eu2s0bgj72k0"]),

    ("Elektr shashlik pishirgich, 12 six, barbekyu",
     "Uy sharoitida tutunsiz shashlik — 12 ta six aylanib, bir tekis pishiradi. "
     "Oila va mehmonlar uchun ideal.",
     699000, ["d49fvlej76ohd6e13920", "d49fvhuj76ohd6e138v0", "d49fvdtsp2tr82i3q03g"]),

    ("Oshxona kombayni 4 tasi 1 da, sharbat siqqich va maydalagich",
     "To'rt vazifa bitta qurilmada: sharbat siqish, maydalash, aralashtirish va "
     "qahva tayyorlash. Oshxonada joy tejaydi.",
     615000, ["d4g0496j76ooegrm7teg", "d0gqj7q7s4fo7mq8rotg", "d0gqjab3uvph509tp2pg"]),

    ("Mikser Artel ART-HM-5035",
     "Artel qo'l mikseri — xamir, krem va qaymoq uchun. Bir necha tezlik rejimi, "
     "yengil va qulay korpus.",
     820710, ["cs7ltctpq3ghb2qj8vng", "d6ophtos9rf3ubr1ba20", "d6ophtq1146th72ui620"]),

    ("Kofe mashina UAKEEN, avtomatik kapuchinatorli, 20 bar",
     "UAKEEN GERMANY espresso mashinasi — 20 bar bosim, avtomatik kapuchinator. "
     "Uyda barista darajasidagi kofe.",
     1499000, ["d5ovld6ojia393mt2380", "d5ovlcuj76og35gjs3tg", "d5p6353q345softls3eg"]),

    ("Kofe maydalagich BOSCH TSM6A011W",
     "Bosch kofe maydalagichi — donni bir tekis, xushbo'y holda maydalaydi. "
     "Ixcham, ishonchli, yillar xizmat qiladi.",
     390690, ["ck1itmsvutvccfo29icg", "ck1itn4jvf2qegt3lk5g", "ck1itn4jvf2qegt3lk60"]),

    ("Termopot BQ TP501, 5 L, 1400 Vt",
     "BQ TP501 termopot — 5 litr suvni qaynatib, kun bo'yi issiq saqlaydi. Katta "
     "oila va mehmonxona uchun ayni muddao.",
     1299000, ["cqq6ed7frr8a72r7jm9g", "cqq6edcqvsse8lev2gcg", "cpan4b7j2e4hhrn36uug"]),

    ("Elektr choynak Xiaomi Mijia, 1.5 L, metall",
     "Xiaomi Mijia elektr choynagi — zanglamas po'lat, 1.5 litr, tez qaynatish. "
     "Minimalist dizayn, xavfsiz avtomatik o'chish.",
     329000, ["d5u69fmf4hvsl3r1ln40", "d5ofvnmj76og35gjn42g", "d5ofvnmojia393mst4eg"]),

    ("Mini pech Artel 3216 E, elektr duxovka",
     "Artel mini pechi — pishiriq, tovuq va qotirma uchun ixcham duxovka. Harorat "
     "sozlanadi, ichki yoritish qulay.",
     1099000, ["d5tmkl6f4hvsl3r1gg40", "d41i48dsp2tj49o7kv1g", "d41i3ttsp2tj49o7kuvg"]),

    ("Elektr gril BQ GR3007, 2200 Vt",
     "BQ GR3007 elektr grili — yong'inga qarshi qoplama, 2200 Vt quvvat. Go'sht va "
     "sabzavotni yog'siz, mazali pishiradi.",
     725000, ["curi1f3vgbkm5ehfvn7g", "cuvesllpb7f9qcneiks0", "curi1f5pb7f8r31vsp0g"]),

    ("Meva quritgich Blackton FD1112, 5 poddon",
     "Blackton meva-sabzavot quritgichi — 5 poddon, 240 Vt. Qish uchun quritilgan "
     "meva va ko'katlarni uyda tayyorlang.",
     951000, ["d2vtipviub35i07k7mkg", "d2r8b7d2llnd6juka900", "d2r8b7d2llnd6juka8vg"]),

    ("Sendvich pishirgich, 5 tasi 1 da",
     "Besh xil panel bitta qurilmada — sendvich, vafli, gril va donut. Nonushta "
     "har kuni yangicha bo'ladi.",
     359000, ["ct2072j4nkdilc6cldug", "ct2072bvgbkpg1no6h3g", "crpt4r4hug2lhicod67g"]),

    ("Non pechi Sonifer SF-4025, uy nonvoyxonasi",
     "Sonifer SF-4025 non pechi — uyda yumshoq, xushbo'y non. Xamirni o'zi "
     "qoradi, pishiradi — faqat masalliq soling.",
     999000, ["d8vskr49g1ku9j5eaaag", "d8vsksa1146phmqg54vg", "d8vsku3sv8vnuj11a8vg"]),

    ("Smart aerogril-multipech, 12 tasi 1 da, 2 TEN",
     "Ikki TENli smart aerogril — 12 rejim, yog'siz qovurish, katta oynali korpus. "
     "Fri, tovuq va pishiriqlar sog'lom usulda.",
     870000, ["d7k51g3sv8vghom28rd0", "d7k51gs3obpkks11hi50", "d7k51ki1146ojv9gmiq0"]),

    ("Sharbat chiqargich SOFANER, professional",
     "SOFANER sharbat chiqargichi — olma, sabzi va uzumdan bir zumda toza sharbat. "
     "Keng og'izli, yuvish oson.",
     599000, ["d6lrhdi1146th72tb6m0", "d7dq3jc3obpufnhbfde0", "d7dq3jc3obpufnhbfdf0"]),

    ("Aerogril Uakeen GERMANY, 12 L, 10 tasi 1 da",
     "Uakeen 12 litrli katta aerogril — butun tovuqni ham sig'diradi. 10 tayyor "
     "dastur, yog'siz va tez pishirish.",
     849000, ["d6adoh7qkmalqfncirng", "d6d1lv7qkmak8dt7qv2g", "d6adohdv2sjhfufhu5d0"]),

    ("Multivarka Redmond RMC-M70",
     "Redmond RMC-M70 multivarkasi — palov, sho'rva, bug'da pishirish va yana "
     "o'nlab rejim. Kechiktirilgan start funksiyasi bor.",
     699000, ["cs4bl1eo5c8cka40cevg", "cs4bl1ufh2vj1qtjsai0", "cs4bl2eo5c8cka40cf00"]),

    ("Planetar mikser Bemonde, 10 L, 1600 Vt",
     "Bemonde planetar mikseri — 10 litrli katta idish, 1600 Vt. Katta hajmdagi "
     "xamir va kremlar uchun professional yechim.",
     1649000, ["cvbrmnmi4n36ls3v8ufg", "d2o5jlfiub35i07ibu5g", "cvbrn1tpb7f9qcnhvc9g"]),

    ("Go'sht maydalagich elektr, 6 tasi 1 da, 3000 Vt",
     "Kuchli 3000 Vt elektr go'sht maydalagich — revers funksiyasi, po'lat korpus, "
     "6 xil nasadka. Qiyma bir zumda tayyor.",
     549000, ["d1ntprdsp2tm1pihvjfg", "d1nl0vdsp2tm1pihs6eg", "d1nl0vg9oh61u9a3ur90"]),

    ("Oshxona kombayni MARSEL SM-01, xamir qoruvchi",
     "MARSEL SM-01 professional kombayn — go'sht maydalagich, blender, xamir "
     "qoruvchi va xamir yoygich bitta qurilmada.",
     3299000, ["d96kk8rsv8vsdeu76u9g", "d96kk8q1146phmqj3tug", "d5tjr2adk6jhqj0t0h00"]),

    ("Qahva qaynatgich ARDESTO YCM-D060, 600 ml",
     "ARDESTO tomchilatib qahva qaynatgichi — 600 ml, tejamkor 650 Vt. Ertalabki "
     "qahva o'zi damlanib turadi.",
     226710, ["d8c03li1146tv073eb50", "d8c03l21146tv073eb40", "d8c03li1146tv073eb5g"]),

    ("Blinchik pishirgich Sonifer SF-3055, elektr tova",
     "Sonifer SF-3055 blinchik apparati — yopishmaydigan yuza, bir tekis qizish. "
     "Yupqa va mazali blinchiklar oson tayyorlanadi.",
     203940, ["d6ertirvgbksikmkdf0g", "d6ertios9rfd9u93j1lg", "d6ertigs9rfd9u93j1k0"]),

    ("Elektr qozon NanJiren, 2 qavatli parda pishirgich",
     "NanJiren ikki qavatli elektr qozon — bug'da va suvda birga pishirish. Talaba "
     "va kichik oshxonalar uchun qulay.",
     350000, ["d8p8fh49g1ku9j5bh2f0", "d21hadt2llnbjcofpkc0", "d21hagviub3cuo9duacg"]),

    # ---------- Idish-tovoq va qozonlar ----------
    ("Mantovarka po'lat, 30 L, 5 yarusli",
     "Zanglamas po'lat mantovarka — 30 litr, 5 yarus. Katta oila uchun manti, "
     "chuchvara va bug'dagi taomlar birdaniga.",
     339000, ["d4vf2qgjsv1o95cievsg", "d4vf2qjtqdhua1usf4n0", "d4vf2qrtqdhua1usf4ng"]),

    ("Idishlar to'plami emal, 7 buyum, 3 kostryulka va tova",
     "Oq emal idishlar to'plami — 3 kostryulka, 25 sm tova va qopqoqlar. Klassik, "
     "bardoshli va har qanday plitaga mos.",
     1039000, ["d5og9qmj76og35gjn920", "d5og9s6ojia393mst9fg", "d5og9uuj76og35gjn94g"]),

    ("Oshxona idishlari to'plami VICALINA, 6 buyum",
     "VICALINA to'plami — kostryulkalar, tova va damlagich birga. Uzum'da minglab "
     "xaridor tanlagan ishonchli to'plam.",
     599000, ["cvmddjdpb7f8td1j9s10", "cvjt693vgbkm5ehmju9g", "cvjt696i4n36ls41g5jg"]),

    ("Qozonlar to'plami, 12 qism, zanglamas po'lat",
     "12 qismli po'lat qozonlar to'plami — turli hajmlar, shisha qopqoqlar. Butun "
     "oshxona bir xarid bilan jihozlanadi.",
     629000, ["d88n5sa1146tv072fa40", "d7k77ea1146ojv9go28g", "d7k77ec3obpkks11j150"]),

    ("Idish-tovoq to'plami granit, 10 buyum, kuyishga qarshi",
     "Granit qoplamali 10 buyumlik to'plam — kuydirmaydi, yopishmaydi. Shisha "
     "qopqoqli qozonlar zamonaviy oshxona ko'rki.",
     499100, ["d5ecn9btqdhjp1ve7p90", "d5ecn98jsv1neact08qg", "d5ecn9bs2tab83sa3ap0"]),

    ("WOK skovorodka, zanglamas po'lat",
     "Nerjaveyka WOK tovasi — qovurish, dimlash va tez pishirish uchun. Restoran "
     "uslubidagi taomlar endi uyda.",
     650000, ["d8f8aus9g1ktqmlr1da0", "d8f8b1a1146tv074h280", "d8f8b1rsv8vo2t0iuku0"]),

    ("Cho'yan qozon, yog'och qopqoqli, 4–7 L",
     "Haqiqiy cho'yan qozon — kimyoviy qoplamasiz, yog'och qopqoq bilan. Palov va "
     "qovurdoq uchun eng to'g'ri tanlov.",
     499000, ["d4t7118jsv1o95chlsjg", "d4rgc6bs2taeh32799n0", "d2lesgniub35i07hj39g"]),

    ("Chinni servis, 60 buyum, 12 kishilik",
     "60 buyumlik chinni servis — 12 kishilik dasturxonga to'liq bezak. Uzum'da "
     "2500+ marta sotilgan mashhur to'plam.",
     771210, ["d8ucbgs9g1ku9j5dk9e0", "d8ucbdbsv8vnuj10k8o0", "d8ucb8a1146phmqff37g"]),

    ("Pichoqlar to'plami Vicalina, taglikda",
     "Vicalina pichoqlar to'plami — o'tkir po'lat tig'lar, chiroyli taglik bilan. "
     "Har turdagi masalliq uchun alohida pichoq.",
     433990, ["d3rn62gs9rfdsl9e0jtg", "d3rn6234eu2v21ph0asg", "d3rn638s9rfdsl9e0ju0"]),

    ("Menajnitsa oltin naqshli, quruq mevalar uchun",
     "Oltin naqshli menajnitsa — yarim oy va yulduz shaklida. Quruq meva va "
     "yong'oqlar uchun bayramona idish.",
     299000, ["d5mj09qi5abomerovrv0", "d5mj0a6ojia393ms5o2g", "d5mj07eojia393ms5o1g"]),

    ("Mantiqasqon alyuminiy, 4 qavatli, 6–13 L",
     "Alyuminiy mantiqasqon — 4 qavat, yengil va tez qiziydi. Manti, xinkali va "
     "bug'dagi taomlar an'anaviy usulda.",
     580630, ["d8ipg821146tv075u9j0", "d4mn5rlv2sjnqk4k99ng", "d4mn5rlv2sjnqk4k99o0"]),

    ("Oshxona idishlari to'plami Zepter, 6 buyum",
     "Zepter uslubidagi 6 buyumlik to'plam — kostryulkalar va tova. Qalin tag "
     "taomni bir tekis pishiradi.",
     527000, ["d77std43obpufnh947ng", "d77std3sv8vlb6mlk3s0", "d1gh37gs9rffrfkv7m3g"]),

    ("Sirlangan cho'yan kastryulka, 7 L",
     "7 litrli sirlangan cho'yan kastryulka — issiqni uzoq saqlaydi, dimlama va "
     "sho'rvalar ayniqsa mazali chiqadi.",
     599000, ["d948nek9g1ku9j5g6tu0", "d948nf21146phmqi1mig", "d948nejsv8vsdeu64in0"]),

    ("Chinni idishlar to'plami, 30 buyum, 6 kishilik",
     "30 buyumlik chinni to'plam — 6 kishilik oila dasturxoni uchun. Nafis dizayn, "
     "kundalik va bayram uchun birdek mos.",
     760000, ["d7lmmq2d955cjr7cun9g", "d7lmmuq1146tv06qil50", "d7lmn03sv8vo2t08vc0g"]),

    ("Ugra keskich, xamir yoyish uchun, 15 sm",
     "Qo'lda ishlatiladigan ugra keskich — uy lag'moni va ugra uchun xamirni tez, "
     "bir tekis kesadi. Uzum'da 300+ ijobiy sharh.",
     169000, ["cv0kl4rvgbkm5ehhaopg", "cjpqilcjvf2hdh3efi20", "cjpqiqjk9fq13g44uqm0"]),
]


def seed_kitchen() -> int:
    """ProMan Electronics do'koniga 40 xil oshxona buyumini (yo'q bo'lsa) qo'shadi."""
    return seed_products(_PRODUCTS, _find_proman_seller, "ProMan Kitchen")
