"""Bir martalik xavfsiz "seed": DinamoKids do'koniga velosipedlar qo'shadi.

Bot ishga tushganda chaqiriladi. Do'konni telefon yoki nom bo'yicha topadi va
velosipedlarni faqat HALI YO'Q bo'lsa qo'shadi — shuning uchun bot necha marta
qayta ishga tushsa ham takror qo'shilmaydi va mavjud mahsulotlarga tegmaydi.

Har xil o'lcham: 3 g'ildirakli (kichkina bolalar) → 12"/14"/16"/20" bolalar →
24" o'smir → 26"/28" kattalar (tog' va shahar) → fat-bike. Jami 30 ta.
Rasm va narxlar Uzum Market'dan (images.uzum.uz CDN) olingan.
"""

import logging

from app import storage

logger = logging.getLogger(__name__)

# Do'konni aniqlash uchun (ekrandagi ma'lumot bo'yicha):
#   telefon: 998335424245  →  oxirgi 9 raqami "335424245"
#   nom:     "DinamoKids"
_SELLER_PHONE_TAIL = "335424245"
_SELLER_SHOP_NAME = "dinamokids"

_IMG = "https://images.uzum.uz/{}/t_product_540_high.jpg"

# (nom, tavsif, narx so'm, Uzum rasm ID)
_BIKES = [
    # ── Kichkina bolalar: 3 g'ildirakli va yon g'ildirakli ──────────────────
    ("Uch g'ildirakli bolalar velosipedi (mini)",
     "Eng kichik bolalar uchun 3 oyoqli (g'ildirakli) velosiped. Yiqilmaydi, "
     "xavfsiz — 1,5–3 yosh bolalar uchun birinchi velosiped.",
     290030, "cvl9uetpb7f8td1j28dg"),
    ("Uch g'ildirakli bolalar velosipedi BONVI",
     "BONVI 3 g'ildirakli velosiped, dastasi va savatchasi bilan. 2–5 yoshli "
     "bolalar uchun mustahkam va qulay.",
     950600, [
        "d3ajged2lln52upuflj0", "co9b8172u18gghcnk4m0", "copr23c0u44tu6dnt8mg",
        "clg3funn7c6qm23k6g50", "clg3g17n7c6qm23k6g70", "clhjvalennt1kt4drhng",
        "cohpvua1om4pepe0p120", "cnfiacdbl7rtgkb87800", "d3ajged2lln52upufljg",
        "co9b81283ve66on3j1fg"]),
    ("Bolalar velosipedi qo'shimcha o'rindiq va savatcha bilan",
     "Yosh bolalar uchun ikki g'ildirakli velosiped, yordamchi yon g'ildiraklari, "
     "qo'shimcha o'rindiq va old savatchasi bilan.",
     564540, "d0pi24b3uvph509vq9d0"),
    ("ARIVO bolalar velosipedi 12\"/16\", yon g'ildirakli",
     "ARIVO po'lat ramli bolalar velosipedi (12\" yoki 16\"), old savat va "
     "yordamchi yon g'ildiraklar bilan. 3–6 yosh uchun.",
     649900, "d2k0hsj4eu2g1liuv760"),

    # ── Bolalar: 12"/14"/16"/20" (qiz va o'g'il bolalar) ────────────────────
    ("Bolalar velosipedi BONVI 12\"/16\"/20\"",
     "Ikki g'ildirakli BONVI bolalar velosipedi — 12, 16 yoki 20 dyuym. Yengil "
     "po'lat rama, yordamchi g'ildiraklar bilan.",
     475300, [
        "d7b10ak3obpufnhaare0", "cqlmkjssslomdvnj2un0", "d2ha9r52lln9489nt4j0",
        "d7b1113sv8vlb6mmqfp0", "clu6rlrpvnpo2vtqsp80", "cqlmrv7frr8a72r6lk90",
        "d7b11q43obpufnhaasa0", "d7b12a21146ojv9crqp0", "d7b11cbsv8vlb6mmqfvg",
        "d7b10ci1146ojv9crpqg"]),
    ("Bolalar velosipedi Velomax 12\"/14\"/16\"/20\"",
     "Velomax ikki g'ildirakli bolalar velosipedi, o'lchamlari 12/14/16/20 dyuym. "
     "Turli yoshdagi bolalar uchun.",
     522830, [
        "d0rlungn274j5scosna0", "d0rm57r3uvph50a09t00", "d0rm590n274j5scosoag",
        "d6ku97lsp2tohdbclk5g", "d6ku9ags9rf3ubqvn9bg", "d0rlungn274j5scosnag",
        "d0rlungn274j5scosnb0", "d0rlungn274j5scosnbg"]),
    ("Bolalar velosipedi Demansh 776",
     "Demansh 776 ikki g'ildirakli bolalar velosipedi, mustahkam rama va "
     "yordamchi g'ildiraklar bilan.",
     552900, [
        "d8hbh4k9g1ktqmlrtn1g", "d87vosrsv8vo2t0gjpb0", "d8hb7ok9g1ktqmlrtft0",
        "d8hb73bsv8vo2t0jqkc0", "d8hbges9g1ktqmlrtmcg", "d87vp3s9g1ktqmlomilg",
        "d8hb73i1146tv075d7pg", "d8hbgfs9g1ktqmlrtme0", "d87vp8jsv8vo2t0gjpf0",
        "d8hbgbbsv8vo2t0jqqag"]),
    ("Bolalar velosipedi BONVI 5804",
     "Ikki g'ildirakli BONVI 5804 bolalar velosipedi — yengil, chiroyli dizayn, "
     "o'g'il bolalar uchun.",
     543200, [
        "d41e96lv2sjj05os67sg", "d41ea76j76ol453de000", "d41ebntv2sjj05os6890",
        "d79r7oa1146ojv9ccgbg", "d79r7ri1146ojv9ccgeg", "d79r7ua1146ojv9ccghg",
        "d79r813sv8vlb6mmb8bg", "cpprhmr5qt1gj8dc808g", "d41ec06j76ol453de070",
        "cli1imt6sfhvbd1j5uig"]),
    ("Bolalar velosipedi DRONGO 12\"/16\"/20\"",
     "DRONGO bolalar velosipedi, o'lchamlari 12, 16, 20 dyuym. Zamonaviy ko'rinish, "
     "mustahkam qurilma.",
     533500, [
        "cuvltl3vgbkm5ehh3cu0", "cuvltnjvgbkm5ehh3cv0", "cuvlvd6i4n36ls3rvncg",
        "cuvlul3vgbkm5ehh3d80", "cuvlve6i4n36ls3rvndg", "cuvlvvbvgbkm5ehh3dl0",
        "cuvlvervgbkm5ehh3dgg", "cuvlvubvgbkm5ehh3dk0"]),

    # ── Qizlar uchun (pushti, princessa) ────────────────────────────────────
    ("Qizlar uchun velosiped (3–12 yosh)",
     "Qizlar uchun chiroyli bolalar velosipedi, savatchasi bilan. 3–12 yosh "
     "bolalar uchun — pushti rang.",
     572300, [
        "d1jmenc3obprdtm8aldg", "cvk0ukrvgbkm5ehmkqg0", "cvk0uflpb7f9qcnk7ge0",
        "cvk0uljvgbkm5ehmkqgg", "cvk0ug3vgbkm5ehmkqf0", "cvp5br47fd1p445rffng",
        "cqk80e4sslomdvninhs0", "cvp5brlpb7fbmqmmlpng", "cqk80f7frr8a72r6a0a0",
        "cvp5bu6i4n37npanb91g"]),
    ("PRINCESSA qizlar velosipedi 12\"/16\"/20\"",
     "PRINCESSA bolalar velosipedi (12/16/20 dyuym), old savat va bezaklar bilan — "
     "qizchalar uchun.",
     564540, "d7lrdk2d955cjr7d25m0"),
    ("Velosiped \"Printsessa\" 12\"/16\"/20\"",
     "\"Printsessa\" qizlar velosipedi, o'lchamlari 12, 16, 20 dyuym. Savatcha va "
     "yordamchi g'ildiraklar bilan.",
     620800, [
        "cv6k6k3vgbkm5ehitisg", "cv6k755pb7f9qcngg8k0", "cv6k71mi4n36ls3tq1v0",
        "cv6k6qui4n36ls3tq1sg", "cv6k6uei4n36ls3tq1tg"]),
    ("Velosiped DRONGO Princessa (bayroqchali)",
     "DRONGO Princessa qizlar velosipedi, bayroqcha va savatcha bilan — yorqin va "
     "chiroyli dizayn.",
     727500, "d71u20a1146ojv992sq0"),

    # ── 20" (katta bolalar / o'smirlar) ─────────────────────────────────────
    ("Bolalar velosipedi 20\" VELOSPORT",
     "VELOSPORT ikki g'ildirakli 20 dyuymli bolalar velosipedi — 6–10 yoshli "
     "bolalar uchun mustahkam variant.",
     545140, [
        "d87c4jk9g1ktqmloevu0", "d87bpibsv8vo2t0gc2cg", "d87bpgbsv8vo2t0gc2bg",
        "d87c4jk9g1ktqmloevtg", "d87bpic9g1ktqmloeqg0", "d87bpg49g1ktqmloeqf0",
        "d87c4ji1146tv071v600", "d87c3qs9g1ktqmloeve0", "d87c3obsv8vo2t0gc7lg",
        "d87c4jc9g1ktqmloevt0"]),
    ("Sport bolalar velosipedi 20\" Neon Pro",
     "Neon Pro 20 dyuymli sport bolalar velosipedi, zamonaviy dizayn, yengil va "
     "tez — faol bolalar uchun.",
     1330975, "d6q4oqgs9rf3ubr1uaa0"),
    ("Bolalar tog' velosipedi BONVI 20\", qo'sh rom",
     "BONVI 20 dyuymli bolalar tog' velosipedi, qo'shaloq (ikki) romli mustahkam "
     "qurilma. ID:9458.",
     947690, "cppreqj6eisq2rkcqi4g"),
    ("Velosiped 20\", 21 tezlik",
     "20 dyuymli velosiped, 21 tezlikli uzatma bilan — o'smirlar va kichik "
     "bo'yli foydalanuvchilar uchun.",
     1212015, [
        "d7lqhubsv8vo2t0926qg", "d7lqj0jsv8vo2t0927o0", "d7lqj63sv8vo2t0927rg",
        "d7lqj7ad955cjr7d1mb0", "d7lqjmq1146tv06qli8g", "d7lqi221146tv06qlh30",
        "d7lqjk2d955cjr7d1mkg", "d7lqjn3sv8vo2t09285g", "d7lqjp3sv8vo2t092860",
        "d7lqk12d955cjr7d1mtg"]),
    ("Velosiped ADKIDS 20\"",
     "ADKIDS 20 dyuymli velosiped — yosh bolalar va o'smirlar uchun, sayr va "
     "kundalik yurish uchun qulay.",
     1358000, [
        "co0j7ampom4ma10qqjp0", "co3r4otlqsilsr3livo0", "co3r5a6pom4ma10rj62g",
        "co4g0hn2u18gghcmduc0", "co4g13mpom4ma10ro3bg", "co0j7bmpom4ma10qqjqg",
        "co3r4oupom4ma10rj5u0", "co3r5a5lqsilsr3livq0", "co4g0dn2u18gghcmdub0",
        "co4g106pom4ma10ro3a0"]),
    ("Tog' velosipedi 999, 20×3.0, alyuminiy rama",
     "999 Model 20×3.0 tog' velosipedi — quyma alyuminiy rama, keng (fat) "
     "g'ildiraklar. Yengil va mustahkam.",
     1694153, [
        "d8jai5q1146tv07641o0", "d8jb09c9g1ktqmlskj2g", "d8jb0hbsv8vo2t0khma0",
        "d8jb0nk9g1ktqmlskjb0", "d8javkrsv8vo2t0khlig", "d8jb0ba1146tv0764b0g",
        "d8jb0j49g1ktqmlskj70", "d8jb0oi1146tv0764b80", "d8jaj249g1ktqmlska00",
        "d8jb0ci1146tv0764b20"]),

    # ── 24" (o'smirlar) ─────────────────────────────────────────────────────
    ("Velosiped Demansh 20\"/24\"",
     "Demansh velosiped, 20 yoki 24 dyuym o'lchamda — o'smirlar uchun, tog' "
     "uslubidagi mustahkam rama.",
     965150, [
        "d77kqcs3obpufnh8usfg", "d0c6lf5ht56r9t7tj1l0", "d77kskk3obpufnh8utm0",
        "d77ku03sv8vlb6mleor0", "d77kv3i1146ojv9bfgpg", "d0c6lfdht56r9t7tj1lg",
        "d77ksk3sv8vlb6mleo1g", "d77ktvrsv8vlb6mleopg", "d77kv3i1146ojv9bfgp0",
        "d77kskbsv8vlb6mleo20"]),
    ("Tog' velosipedi 24\", 21 tezlik, amortizator",
     "24 dyuymli tog' velosipedi, 21 tezlik, disk tormoz va old amortizatsiya "
     "bilan — o'smirlar uchun sayr velosipedi.",
     1057290, [
        "d7g9v3c3obpkks0vsnd0", "d7g9vt21146ojv9f1c4g", "d7g9uuq1146ojv9f1bhg",
        "d7g9vsc3obpkks0vsnrg", "d7g9uujsv8vghom0k4v0", "d7g9vsk3obpkks0vsns0",
        "d7g9uuk3obpkks0vsnag", "d7g9vsbsv8vghom0k5i0", "d7g9uuk3obpkks0vsnb0",
        "d7g9vsbsv8vghom0k5hg"]),
    ("Tog' velosipedi 20\"/24\", 3.0 balon",
     "O'smirlar uchun 20.24 dyuymli tog' velosipedi, 3.0 qalin balonli — yo'lsiz "
     "hududlarda ham qulay.",
     1309500, "cv08c0dpb7f9qcnereh0"),

    # ── 26" tog' velosipedlari (kattalar) ───────────────────────────────────
    ("Tog' velosipedi DEMANSH 26\", 3.0 balon",
     "DEMANSH tog' velosipedi 26 dyuym, 3.0 qalin balonli, mustahkam rama — "
     "kattalar uchun yo'lsiz va shahar yo'llari uchun.",
     969030, [
        "d2p8ka7iub35i07ijke0", "d2qiq3b4eu2h0tmpvd6g", "d2p8k3l2llnd6jujspn0",
        "d2p8ioj4eu2h0tmpmg80", "d2p8j952llnd6jujsphg", "d2qiq1d2llnd6juk5ks0",
        "d2p8k1b4eu2h0tmpmgjg", "d2p8ik34eu2h0tmpmg60", "d2p8j7fiub35i07ijk50",
        "d2qiq2j4eu2h0tmpvd60"]),
    ("Tog' velosipedi DEMANSH 26\", 2.5 balon, tezlikli",
     "DEMANSH tezlikli tog' velosipedi, 26 dyuym, 2.5 balon — sport va kundalik "
     "foydalanish uchun.",
     1023350, [
        "d789hlq1146ojv9bnv70", "d77m9hjsv8vlb6mlfieg", "d789kfc3obpufnh978s0",
        "d77m9ci1146ojv9bg9q0", "d77m9r21146ojv9bgadg", "d77m9hi1146ojv9bga10",
        "d789kfa1146ojv9bo08g", "d77m9cq1146ojv9bg9qg", "d77m9ra1146ojv9bgae0",
        "d77m9ha1146ojv9bg9v0"]),
    ("Tog' velosipedi BONVI 025, 26\"",
     "BONVI 025 tog' velosipedi, 26 dyuym, o'smir va kattalar uchun. ID:1507 — "
     "ishonchli va ommabop model.",
     1164000, [
        "d4sjcd8jsv1o95chf2tg", "cmnnfdp25ku8ad8idubg", "d4s0o2jtqdhua1ur98c0",
        "d4s0nujtqdhua1ur9890", "d4s0o4btqdhua1ur98dg", "cnikujku2hhlb05gig60",
        "cuhev8c5j42bjc4ce2r0", "csurjbdpq3ggq63ebc20", "cqk7epkqvsse8letoom0",
        "csurje5pq3ggq63ebc40"]),
    ("Tog' velosipedi 26\", 21 tezlik, amortizator",
     "26 dyuymli tog' velosipedi, 21 tezlik, disk tormoz va old amortizatsiya "
     "bilan — kattalar uchun.",
     1057300, [
        "d7gp3fjsv8vghom0rc3g", "d7gp4d43obpkks103qig", "d7gp3i21146ojv9f8f50",
        "d7gp4d43obpkks103qj0", "d7gp3i21146ojv9f8f5g", "d7gp4d43obpkks103qk0",
        "d7gp3i21146ojv9f8f60", "d7gp4d43obpkks103qjg", "d7gp3hrsv8vghom0rc40",
        "d7gp4d3sv8vghom0rc60"]),
    ("Tog' velosipedi DREZ 26-R, 21 tezlik (Shimano)",
     "DREZ 26-R tog' velosipedi, 21 tezlik, Shimano uzatma kalitlari bilan. "
     "ID:13750 — kuchli va aniq uzatma.",
     1697500, [
        "d70knjc3obpjedc3k650", "d76h9r43obpufnh8dudg", "d76h9rbsv8vlb6mkufog",
        "d76h9ra1146ojv9avj00", "d76h9ra1146ojv9avj10", "d76h9r43obpufnh8due0",
        "d76h9r21146ojv9avivg", "d76h9r3sv8vlb6mkufo0"]),
    ("Fat-bike BAOL 26\" 4.0",
     "BAOL FAT BIKE 26 dyuym, 4.0 juda keng balonli amortizatorli velosiped — "
     "qor, qum va yo'lsiz hududlar uchun.",
     1881790, [
        "crmpf86vip07shn5e1tg", "cpi2rkbmdtjnp738saf0", "crmpe1mvip07shn5e1b0",
        "crmpd7ajot51rkb27kvg", "crmpdi2jot51rkb27l3g", "crmpdtevip07shn5e190",
        "crmpf0ijot51rkb27lk0", "crmpf2qjot51rkb27llg", "cpi2rkffrr82f0a5v5sg",
        "crmpe4chug2lhicnmtdg"]),
    ("Tog' velosipedi Buyuk Bonvi 26\"",
     "Buyuk tog' Bonvi 26 dyuymli velosiped — mustahkam rama, kattalar uchun "
     "kundalik va sport yurish.",
     1212500, "d0mtuqi7s4fo7mqaa4hg"),

    # ── 28" shahar velosipedlari (kattalar) ─────────────────────────────────
    ("Shahar velosipedi Belarus 28\"",
     "Belarus 28 dyuymli shahar velosipedi (ID:377) — klassik, mustahkam, "
     "kundalik yurish uchun qulay.",
     970000, "clia28lennt6m2906u7g"),
    ("Shahar velosipedi Belarus 28\", Nexus",
     "Belarus 28 dyuymli shahar velosipedi, Nexus uzatma bilan — shaharda "
     "qulay va silliq yurish.",
     1110650, "d865uuq1146tv071go5g"),
    ("ARIVO 28\" shahar velosipedi, savatchali",
     "ARIVO 28 dyuymli shahar velosipedi, po'lat rama va old savatcha bilan — "
     "kattalar uchun klassik shahar modeli.",
     1358000, "d2k0ul52llnd6juig7tg"),

    # ── Universal / ko'p o'lchamli ──────────────────────────────────────────
    ("ARIVO velosiped 20\"/24\"/26\", savatchali",
     "ARIVO velosiped, o'lchamlari 20/24/26 dyuym, po'lat rama va old savatcha "
     "bilan — butun oila uchun.",
     1067000, "d2k0sr7iub35i07h70l0"),
    ("Universal velosiped 26\" (shahar va yo'lsiz)",
     "26 dyuymli universal velosiped — shahar ham, yo'lsiz hududlar uchun ham "
     "mos. Kattalar uchun ko'p maqsadli.",
     1270215, "d7lt1849g1ktqmlh6ii0"),
    ("Kattalar uchun velosiped BONVI Sport",
     "BONVI Sport kattalar velosipedi — yengil, tez va mustahkam, sport va "
     "kundalik yurish uchun.",
     1419789, "d12m78r3uvppu2aau16g"),
]


def _find_seller() -> tuple[int, dict] | None:
    """DinamoKids do'konini telefon yoki nom bo'yicha topadi."""
    for sid, s in storage.get_sellers().items():
        phone_ok = storage.normalize_phone(s.get("phone")) == _SELLER_PHONE_TAIL
        name_ok = str(s.get("shop_name", "")).strip().lower() == _SELLER_SHOP_NAME
        if phone_ok or name_ok:
            return int(sid), s
    return None


def _photos_from(img_ids) -> list[str]:
    """Bitta rasm ID si ham, ID lar ro'yxati ham qabul qilinadi — Uzum rasm
    havolalari ro'yxatini qaytaradi."""
    ids = img_ids if isinstance(img_ids, (list, tuple)) else [img_ids]
    return [_IMG.format(i) for i in ids if i]


def seed_products(products, finder, label: str) -> int:
    """Umumiy seed: mahsulotlarni do'konga qo'shadi.

    products: (nom, tavsif, narx, rasm) ketma-ketligi. "rasm" bitta Uzum ID si
              yoki ID lar ro'yxati bo'lishi mumkin (bir nechta rasm uchun).
    finder:   do'konni topib (seller_id, seller) qaytaruvchi funksiya.

    MUHIM: mahsulot allaqachon mavjud bo'lsa ham, rasmlari o'zgargan bo'lsa
    YANGILANADI (shuning uchun 1 rasmli eski mahsulotlar bot qayta ishga
    tushganda avtomatik ko'p rasmli bo'ladi). Mavjud bo'lmasa — qo'shiladi.
    Qo'shilgan + yangilangan sonini qaytaradi."""
    found = finder()
    if not found:
        logger.warning("Seed: do'kon topilmadi — %s qo'shilmadi.", label)
        return 0
    seller_id, seller = found
    shop_name = seller.get("shop_name", "")
    city = seller.get("city", "")

    # Barcha mahsulotlarni bir marta o'qiymiz va xotirada o'zgartiramiz — oxirida
    # BITTA marta yozamiz (har mahsulotga alohida fayl yozmaymiz, startup tez bo'ladi).
    all_products = storage.get_all_products()
    by_name = {
        str(p.get("name", "")).strip().lower(): p
        for p in all_products if p.get("seller_id") == seller_id
    }
    next_id = max((p["id"] for p in all_products), default=0)

    added = updated = 0
    for name, desc, price, img_ids in products:
        photos = _photos_from(img_ids)
        ex = by_name.get(name.strip().lower())
        if ex is not None:
            # Mavjud mahsulotga TEGMAYMIZ — rasm/ma'lumotini qayta yozmaymiz.
            # (Avval mavjud mahsulot rasmlari farq qilsa ustiga yozilardi; shu
            # sabab admin/seller qo'lda o'zgartirgan yoki /restore bilan tiklangan
            # asl rasmlar har restartda Uzum rasmiga qaytib ketardi. Endi seed
            # faqat YANGI mahsulot qo'shadi, mavjudini o'zgartirmaydi.)
            continue
        next_id += 1
        new_p = {
            "id": next_id,
            "seller_id": seller_id,
            "shop_name": shop_name,
            "city": city,
            "name": name,
            "description": desc,
            "price": price,
            "photos": photos,
        }
        all_products.append(new_p)
        by_name[name.strip().lower()] = new_p
        added += 1

    if added or updated:
        storage.save_products(all_products)
    logger.info("Seed (%s): %s ta qo'shildi, %s ta rasm yangilandi ('%s').",
                label, added, updated, shop_name)
    return added + updated


def seed_bikes() -> int:
    """Velosipedlarni DinamoKids do'koniga qo'shadi/rasmlarini yangilaydi."""
    return seed_products(_BIKES, _find_seller, "velosipedlar")
