# -*- coding: utf-8 -*-
"""Startup'da mahsulot rasmlarini tuzatish (Telegram -> Uzum).

Ba'zi mahsulotlarning rasmlari Telegram'dan (file_id) yuklangan bo'lib, ular
do'kon ko'rinishini buzadi. Bu modul o'sha mahsulotlarni Uzum Market'ning
toza galereya rasmlari bilan almashtiradi.

Xavfsiz va idempotent:
  * Faqat pastdagi MAP'da ko'rsatilgan mahsulot id'lariga tegadi.
  * Faqat RASM (photos) maydonini o'zgartiradi — narx, nom, sotuvchi va boshqa
    hamma narsa tegilmaydi.
  * Mahsulotning hozirgi rasmi ALLAQACHON http (Uzum) bo'lsa — tegmaydi.
    Demak faqat "yomon" (Telegram file_id) rasmlar bir marta to'g'rilanadi;
    keyinroq qo'lda qo'yilgan to'g'ri rasm ustiga yozilmaydi.
  * /restore zip kerak emas — GitHub'ga yuklash kifoya.
"""

import logging

from app.storage import get_all_products, save_products

logger = logging.getLogger(__name__)

IMG = "https://images.uzum.uz/{}/t_product_540_high.jpg"

# ── Uzum rasm to'plamlari (jonli mahsulot sahifalaridan, har biri >=2) ───────
# --- Muzlatgichlar (Bravo) ---
A_ARTEL316 = ["d2a9m952lln4bo5dbrc0", "cnmv10tbl7rtgkb9pa00", "cnmv10ku2hhlb05hfbvg"]
B_BIRYUSA  = ["d6kn168s9rf3ubqvjohg", "d6kn18lsp2tohdbchvp0", "d6kn1aa1146th72stts0",
              "d6kn1c8s9rf3ubqvjon0", "d6kn1edsp2tohdbchvsg"]
C_FERRE    = ["d8nug1bsv8vo2t0mcqcg", "cmjphfbifoubkc6ocipg", "cmjphf925ku8ad8ho5ig",
              "cmjphb9s99ouqbfqv0pg", "cppckej6eisq2rkco4bg"]
# --- Ventilyatorlar ---
F_LAMO     = ["d8kp3lbsv8vo2t0l4km0", "d8kp3eq1146tv076nblg", "d8kp3i49g1ktqmlt7p5g"]
F_UNIVER   = ["d8c1isrsv8vo2t0hslvg", "d8c1isq1146tv073f440", "d8c1iss9g1ktqmlpvifg",
              "d8c1it3sv8vo2t0hsm00", "d8c1isc9g1ktqmlpvie0"]
F_AKALON   = ["d8lb0hbsv8vo2t0lbmi0", "d8lb0h3sv8vo2t0lbmh0", "d8lb0h3sv8vo2t0lbmhg",
              "d8la06k9g1ktqmlte320"]
# --- Kulerlar (Bravo) ---
K_WELL     = ["d4i3njdv2sjnqk4ilba0", "d4i3njdv2sjnqk4ilb9g", "d4i3njej76ooegrmragg",
              "d425hcdsp2tj49o7q5og"]
K_SENSOR   = ["d8jfts49g1ktqmlsn9ng", "d8jfts49g1ktqmlsn9n0", "d8jfts21146tv0766ut0",
              "d8jftsa1146tv0766utg", "d8i1req1146tv075m1ag"]
K_LORETTO  = ["d7pilo49g1ktqmlirglg", "d7ob1qa1146tv06rqa40", "d7pilhc9g1ktqmlirgfg",
              "d7pilsi1146tv06sbjp0", "d7pipbq1146tv06sbm0g"]
AIRCOOLER  = ["d8gn2jq1146tv0755g7g", "d8gn2jrsv8vo2t0jiss0", "d8gn2jq1146tv0755g6g",
              "d8gte5bsv8vo2t0jm7k0", "d8gteik9g1ktqmlrp38g"]
# --- Televizorlar (YANGI DINAMO) ---
TV_ARTEL32 = ["d2o434r4eu2h0tmpe0pg", "cv01rq3vgbkm5ehh5edg", "ctl4o3mi4n368aadafpg",
              "ctl4o4kopsf31vcrpptg", "ctl4o65ht56qpot8cbf0"]
TV_MOONX_A = ["d7l00s394ba5k493pljg", "d7l00s394ba5k493plj0", "d7l00s1qimkgrc91jt2g",
              "ctdg4pk5j428jv1fle40"]
TV_MOONX_B = ["ctdg4p5ht56hik5kgf1g", "ctdg4p45j428jv1fle30", "ctdg4p5ht56hik5kgf20"]
# --- Duxovkalar (mini-pech) ---
OV_ARTEL60 = ["d04ti6mi4n37npapvn50", "d2sikfb4eu2h0tmqfobg", "d2sikgniub35i07jcq5g",
              "d2sikhviub35i07jcq60", "d2sikir4eu2h0tmqfodg"]
OV_RETRO   = ["d13sum27s4fr083f1nhg", "cn9g4gp25kub33f49h30", "cn9g4grifoubkc6sgpng"]
OV_MAGNA   = ["d5fkms3s2tab83safq1g", "d5fkmtbs2tab83safq2g", "d8l7htq1146tv076rdt0",
              "d8l7hus9g1ktqmltbvog", "d5fkn53s2tab83safq70"]
# --- AI tarjimon quloqchin + kabel (ProMan) ---
EAR_BLACK   = ["d7vc0ak9g1ktqmll6pmg", "d7vc0ak9g1ktqmll6pl0", "d7vc0ai1146tv06ummm0",
               "d7vc0ak9g1ktqmll6pkg"]
EAR_CREAM_A = ["d7vf31i1146tv06uo4vg", "d7vf3021146tv06uo4tg", "d7vf3121146tv06uo4ug",
               "d7vf313sv8vo2t0d5290"]
EAR_CREAM_B = ["d7vf31a1146tv06uo4v0", "d7vf31jsv8vo2t0d529g", "d7vf31jsv8vo2t0d52a0"]
CABLE_A = ["d6k4vglsp2tohdbca3fg", "d6k4vhos9rf3ubqvbc5g", "d0rupmi7s4fo7mqbd0lg",
           "d0ta4hq7s4fo7mqbmo9g"]
CABLE_B = ["cs19c9k0u44g6joqqt80", "cs19c9ksslojjk5riac0", "cs19c9ksslojjk5riacg",
           "cs19c9ssslojjk5riadg"]
# --- Kolonkalar (Raduga) ---
SPK_KAR_A = ["cvj4dj6i4n36ls419q1g", "cvj4dodpb7f9qcnk075g", "cvj4dktpb7f9qcnk0740",
             "cvj4doei4n36ls419q40"]
SPK_KAR_B = ["cvj4dlui4n36ls419q2g", "cvj4dmlpb7f9qcnk074g", "cvj4dobvgbkm5ehmdfu0"]
SPK_BAR   = ["d42ubt6j76okhkd9gvng", "d42ubt5sp2tj49o81pcg", "d42ubt6j76okhkd9gvn0"]
# --- Boshqa do'konlar ---
POOL    = ["d8ok2m3sv8vo2t0mmcl0", "d82352bsv8vo2t0e854g", "d82352i1146tv06vqtvg",
           "d03r0r47fd1idpht8l20"]
KOMOD   = ["d6293d3vgbkv4qppvl4g", "cpmgok36eisq2rkc6uag", "d48tdiuj76ohd6e0u8d0",
           "d48tditsp2tr82i3l07g", "d48tdjdsp2tr82i3l08g", "d48tditv2sjo4rvhj8sg"]
STELLAJ = ["d8h83ta1146tv075b4ag", "d8h7nc49g1ktqmlrr630", "d8h83uk9g1ktqmlrrc30",
           "d8h7nc3sv8vo2t0joa50", "d8h83vrsv8vo2t0joft0", "d8h7nc21146tv075aumg"]
ORG     = ["d2i6qid2lln7hego4vug", "d2jdgkt2llnd6juib0o0", "d2jdgkviub35i07h1po0",
           "d2jdgkt2llnd6juib0p0", "d2i6qv34eu2g1liuf1o0", "d2i6r452lln7hego50ag",
           "d2i6sgr4eu2g1liuf2fg"]
TRENAJ  = ["d6srgus3obpjedc2dtc0", "d6srlma1146lmcd3c1s0", "d6srlma1146lmcd3c1rg"]
BANKA   = ["ctaq0qlpb7f7ago7rg5g", "ctaq0rei4n3ehka2uupg"]

# ── product_id -> rasm to'plami (46 ta) ──────────────────────────────────────
MAP = {
    # Bravo electronics (16)
    2: F_AKALON, 18: F_AKALON, 11: F_UNIVER, 19: F_UNIVER, 12: F_LAMO,
    13: AIRCOOLER, 14: K_SENSOR, 15: K_WELL, 16: K_LORETTO, 17: K_WELL,
    20: B_BIRYUSA, 21: A_ARTEL316, 22: C_FERRE, 23: B_BIRYUSA, 24: A_ARTEL316, 25: C_FERRE,
    # YANGI DINAMO electronic (11)
    163: TV_ARTEL32, 164: TV_MOONX_A, 165: TV_MOONX_B,
    166: OV_MAGNA, 167: OV_RETRO, 168: OV_ARTEL60, 169: OV_RETRO, 170: OV_ARTEL60,
    171: F_UNIVER, 172: F_LAMO, 173: F_AKALON,
    # ProMan Electronics (8)
    1: EAR_BLACK, 3: EAR_CREAM_A, 4: EAR_CREAM_B, 5: EAR_BLACK, 6: EAR_CREAM_A,
    8: CABLE_A, 9: CABLE_B, 10: CABLE_A,
    # Raduga Electronika (3)
    32: SPK_KAR_A, 33: SPK_BAR, 34: SPK_KAR_B,
    # Azamatov Naimjon (3)
    26: F_LAMO, 27: F_UNIVER, 28: POOL,
    # Nishonov Toshboy (2)
    29: KOMOD, 59: STELLAJ,
    # Malaxitovaya shkatulca (3)
    31: ORG, 161: TRENAJ, 162: BANKA,
}


def _is_uzum(photos) -> bool:
    """Mahsulotda allaqachon http (Uzum) rasm bormi?"""
    if not isinstance(photos, list):
        return False
    return any(isinstance(u, str) and u.startswith("http") for u in photos if u)


def fix_photos():
    """Yomon (Telegram) rasmli mahsulotlarni Uzum rasmlariga almashtiradi."""
    products = get_all_products()
    changed = 0
    for p in products:
        ids = MAP.get(p.get("id"))
        if not ids:
            continue
        # Allaqachon Uzum rasmli bo'lsa — tegmaymiz (idempotent, qo'lda
        # qo'yilgan to'g'ri rasm ustiga yozmaymiz).
        if _is_uzum(p.get("photos")):
            continue
        p["photos"] = [IMG.format(i) for i in ids]
        p.pop("photo", None)
        changed += 1
    if changed:
        save_products(products)
    logger.info("Rasm tuzatish: %d ta mahsulot yangilandi.", changed)
    return changed
