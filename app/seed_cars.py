"""Bir martalik xavfsiz "seed": DinamoKids do'koniga bolalar minadigan
mashinalarini (elektromobil) qo'shadi.

Bot ishga tushganda chaqiriladi. Do'konni topish, qo'shish va MAVJUD
mahsulotlar rasmlarini yangilash mantig'i [seed_bikes.seed_products] da —
shu yerdan qayta ishlatiladi.

Jami 15 ta: turli markalar (Mercedes, BMW, Ferrari), jip/SUV, yo'ltanlamas,
tolokar va arzon modellar. Har bir mahsulotda bir nechta rasm (Uzum Market'dan,
images.uzum.uz) — kartochkada albom bo'lib ko'rinadi.
"""

import logging

from app.seed_bikes import _find_seller, seed_products

logger = logging.getLogger(__name__)

# (nom, tavsif, narx so'm, Uzum rasm ID lari ro'yxati)
_CARS = [
    ("Bolalar elektromobili Mercedes-Benz G63 AMG",
     "Akkumulyatorli Mercedes-Benz G63 AMG elektromobil — pultli boshqaruv, "
     "LED chiroqlar va musiqa bilan. Kichkina haydovchilar uchun premium model.",
     2043840, [
        "d7n4s6jsv8vo2t09nhjg", "d7n4r83sv8vo2t09nh20", "d7n4s2a1146tv06rajp0",
        "d7n4r821146tv06rajb0", "d7n4s2k9g1ktqmlhqp6g", "d7n4ra49g1ktqmlhqos0",
        "d7n4s3c9g1ktqmlhqp7g", "d7n4raq1146tv06rajcg", "d7n4s3rsv8vo2t09nhh0",
        "d7n4rbc9g1ktqmlhqosg"]),
    ("Bolalar elektromobili BMW, pultli",
     "BMW elektromobil — ota-ona masofadan pult bilan boshqarishi mumkin. "
     "Akkumulyatorli, yumshoq yurish, 2–6 yosh bolalar uchun.",
     2111040, [
        "d7oek0jsv8vo2t0a9ibg", "d05uehmi4n37npaq8aj0", "d0n1bu0n274j5scnrelg",
        "d0q70kb3uvph509vug2g", "d0rmtlb3uvph50a0a1cg", "d0rmtnb3uvph50a0a1d0",
        "d0rmui27s4fo7mqbcgk0", "d0rmutq7s4fo7mqbcgmg", "d0rmvson274j5scosss0",
        "d018mvlpb7fbmqmoi5hg"]),
    ("Bolalar mashinasi BMW (akkumulyatorli)",
     "BMW uslubidagi bolalar elektromobili — akkumulyatorli, chiroq va musiqali. "
     "Hovli va xona ichida yurish uchun.",
     1151040, [
        "d7acctk3obpufnha1neg", "d7acdbbsv8vlb6mmhe00", "d7acdcbsv8vlb6mmhe0g",
        "d7acdd3sv8vlb6mmhe10", "d7acddq1146ojv9cilsg", "d7accti1146ojv9cileg",
        "d7acdds3obpufnha1npg", "d7acctjsv8vlb6mmhdjg", "d7acctjsv8vlb6mmhdk0",
        "d7acctjsv8vlb6mmhdkg"]),
    ("Bolalar elektromobili Ferrari, pultli",
     "Ferrari uslubidagi sport elektromobil — pultli boshqaruv, yorqin dizayn, "
     "LED chiroqlar va musiqa bilan.",
     1247040, [
        "cv1jj25pb7f9qcnf71sg", "cv1jj83vgbkm5ehhkerg", "cv1jj9mi4n36ls3sgqng",
        "cv1jj2jvgbkm5ehhkeqg", "cv1jj8ui4n36ls3sgqmg", "cv1jjadpb7f9qcnf71vg",
        "cv1jj36i4n36ls3sgqlg"]),
    ("Bolalar elektrojipi (akkumulyatorli)",
     "Katta bolalar elektrojipi — baland klirens, mustahkam g'ildiraklar, "
     "akkumulyatorli. Hovlida ham, tekis yo'lda ham yuradi.",
     1910400, [
        "d6a4s5nqkmalqfncdlog", "d6a50qtv2sjru7250h0g", "d6a512he6ph7gqpipb7g",
        "d6a5159e6ph7gqpipbb0", "d6a4sohe6ph7gqpip7a0", "d6a50sfqkmalqfncdq40",
        "d6a510nqkmalqfncdq90", "d6a516vqkmalqfncdqgg", "d6a4t5he6ph7gqpip7lg",
        "d6a50tnqkmalqfncdq5g"]),
    ("Bolalar elektr SUV mashina, 7 km/soat",
     "Kuchli bolalar elektr SUV — 1–10 yosh uchun, 7 km/soatgacha tezlik, "
     "xavfsiz va barqaror. Keng o'rindiq va kuchli motor.",
     2726697, [
        "d86p2ua1146tv071o1rg", "d84k5221146tv070rsfg", "d7gcc3k3obpkks0vujbg",
        "d84k8hq1146tv070rsrg", "d84k6jrsv8vo2t0f90cg", "d84kmn49g1ktqmlnbrm0",
        "d84knsk9g1ktqmlnbrug", "d84kpsk9g1ktqmlnbscg", "d7gcbhk3obpkks0vuik0",
        "d84k1tk9g1ktqmlnbod0"]),
    ("Bolalar elektr UTV 12V, pult, LED, USB musiqa",
     "Bolalar elektr UTV bagi — 12V, 2.4GHz pult, LED chiroqlar, 35 kg gacha, "
     "2–13 yosh, USB musiqa. Ikki kishilik mustahkam model.",
     2495040, [
        "d8jq8vi1146tv0768oag", "d5u6soef4hvsl3r1m2b0", "d8jq9mq1146tv0768oi0",
        "d8jq9jq1146tv0768og0", "d8jq8vi1146tv0768ob0", "d5u6sobq345o6s40i87g",
        "d8l5kla1146tv076q8tg", "d8l5q8s9g1ktqmltaso0", "d5u6sguf4hvsl3r1m230",
        "d8jqaci1146tv0768ovg"]),
    ("Bolalar elektromobili yo'ltanlamas JM-3188",
     "JM-3188 yo'ltanlamas (offroad) bolalar elektromobili — katta g'ildiraklar, "
     "pultli boshqaruv, hovli va notekis yo'llar uchun.",
     1631040, [
        "d30pr7fiub35i07kgv1g", "d30pri52llnd6julpvf0", "d30ptmfiub35i07kgvrg",
        "d30pvgr4eu2up0ato440", "d30pvk7iub35i07kh0fg", "d30pvkt2llnd6julq0mg"]),
    ("Bolalar elektromobili yo'ltanlamas XW2188A",
     "XW2188A yo'ltanlamas bolalar elektr avtomobili — baland korpus, mustahkam "
     "g'ildiraklar, pult va musiqa bilan.",
     1559040, [
        "d6kirq0s9rf3ubqvggcg", "d6kis1i1146th72sqk10", "d6kis3a1146th72sqk3g"]),
    ("Bolalar elektromobili yo'ltanlamas NEL901",
     "NEL901 yo'ltanlamas bolalar elektromobili — kuchli motor, pultli boshqaruv, "
     "LED chiroqlar. Hovlida yurish uchun ideal.",
     1645440, [
        "d1u9so34eu2jc8ghms5g", "cvvlhjmi4n37npaos9t0", "d1uac5niub3cuo9d5lgg",
        "d1uac934eu2jc8ghn2ig", "d1uaccr4eu2jc8ghn2kg", "d1ua61fiub3cuo9d5irg",
        "d1u9soviub3cuo9d5fbg", "d1ua86b4eu2jc8ghn0o0", "d1uaaoviub3cuo9d5kng"]),
    ("Bolalar Tolokar mashinasi (itarib + akkumulyator)",
     "Tolokar — kichkina bolalar uchun: ota-ona dasta bilan itaradi yoki "
     "akkumulyatorda mustaqil yuradi. 1–4 yosh uchun.",
     664329, [
        "d6fq4bjvgbklj92hl72g", "d03ts9ui4n37npappt8g", "d6uqffs3obpjedc322c0",
        "d6uqf9i1146ojv9807cg", "d6fq99gs9rfd9u9418pg", "d6uqfd3sv8vlb6mhuv30",
        "d03tsb5pb7f46s881di0", "cmnt6uh25ku8ad8ifkhg", "conj827j2e4ghqnp34ig",
        "cmnt6up25ku8ad8ifkig"]),
    ("Bolalar elektromobili (akkumulyatorli)",
     "Akkumulyatorli bolalar elektr mashinasi — chiroq va musiqali, qulay "
     "o'rindiq. Sayr va o'yin uchun.",
     1535990, [
        "d7s6dhi1146tv06tcrv0", "d7s67ejsv8vo2t0bpep0", "d8037kjsv8vo2t0dc0hg",
        "d7o762jsv8vo2t0a4f60", "d1h62di1146jmb90k6ag", "d7t1ckjsv8vo2t0c7010",
        "d1h62ags9rffrfkvcjlg", "d8036tq1146tv06uuvdg", "cvqc72lpb7fbmqmmv90g",
        "cvqc6rlpb7fbmqmmv8ug"]),
    ("Bolalar elektromobili (arzon model)",
     "Sodda va arzon bolalar elektr mashinasi — akkumulyatorli, yengil. "
     "Birinchi elektromobil sifatida mos.",
     470438, [
        "d7s6dhi1146tv06tcrv0", "d7s67ejsv8vo2t0bpep0", "d8037kjsv8vo2t0dc0hg",
        "d7o762jsv8vo2t0a4f60", "d1h62di1146jmb90k6ag", "d7t1ckjsv8vo2t0c7010",
        "d1h62ags9rffrfkvcjlg", "d8036tq1146tv06uuvdg", "cvqc72lpb7fbmqmmv90g",
        "cvqc6rlpb7fbmqmmv8ug"]),
    ("Bolalar elektromobili (katta, premium)",
     "Katta o'lchamdagi premium bolalar elektromobili — keng o'rindiq, kuchli "
     "motor, to'liq jihozlangan. Kattaroq bolalar uchun.",
     3456000, [
        "d7l3tbvuc85egd1kpt5g", "d7l3tqbsv8vo2t08n300", "d7l3tdoi00ag7tp7n6mg",
        "d7l3tfnuc85egd1kpta0"]),
    ("Bolalar mashinasi (oddiy, arzon)",
     "Kichkina bolalar uchun oddiy minadigan mashina — yengil, xavfsiz va arzon. "
     "Xona ichi o'yinlari uchun qulay.",
     135388, [
        "d0s45j33uvph50a0che0", "d0s45j0n274j5scovc6g", "d0s45j0n274j5scovc60",
        "d0s45j33uvph50a0chdg"]),
]


def seed_cars() -> int:
    """Bolalar mashinalarini DinamoKids do'koniga qo'shadi/rasmlarini yangilaydi.
    Qo'shilgan + yangilangan mahsulotlar sonini qaytaradi."""
    return seed_products(_CARS, _find_seller, "bolalar mashinalari")
