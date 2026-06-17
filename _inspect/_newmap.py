# -*- coding: utf-8 -*-
"""Qolgan do'konlar (YANGI DINAMO, ProMan, Raduga, Azamatov, Nishonov,
DeFlora, Malaxitovaya) Uzum'mas rasmlarini Uzum rasmlariga almashtirish.
Har to'plam jonli Uzum mahsulot sahifasidan (galereya, >=3 rasm)."""

# ── Uzum rasm to'plamlari ────────────────────────────────────────────────────
# Televizorlar
TV_ARTEL32 = ["d2o434r4eu2h0tmpe0pg", "cv01rq3vgbkm5ehh5edg", "ctl4o3mi4n368aadafpg",
              "ctl4o4kopsf31vcrpptg", "ctl4o65ht56qpot8cbf0"]
TV_MOONX_A = ["d7l00s394ba5k493pljg", "d7l00s394ba5k493plj0", "d7l00s1qimkgrc91jt2g",
              "ctdg4pk5j428jv1fle40"]
TV_MOONX_B = ["ctdg4p5ht56hik5kgf1g", "ctdg4p45j428jv1fle30", "ctdg4p5ht56hik5kgf20"]
# Duxovkalar (mini-pech)
OV_ARTEL60 = ["d04ti6mi4n37npapvn50", "d2sikfb4eu2h0tmqfobg", "d2sikgniub35i07jcq5g",
              "d2sikhviub35i07jcq60", "d2sikir4eu2h0tmqfodg"]
OV_RETRO   = ["d13sum27s4fr083f1nhg", "cn9g4gp25kub33f49h30", "cn9g4grifoubkc6sgpng"]
OV_MAGNA   = ["d5fkms3s2tab83safq1g", "d5fkmtbs2tab83safq2g", "d8l7htq1146tv076rdt0",
              "d8l7hus9g1ktqmltbvog", "d5fkn53s2tab83safq70"]
# Ventilyatorlar (Bravo ishidan qayta ishlatilgan)
F_LAMO   = ["d8kp3lbsv8vo2t0l4km0", "d8kp3eq1146tv076nblg", "d8kp3i49g1ktqmlt7p5g"]
F_UNIVER = ["d8c1isrsv8vo2t0hslvg", "d8c1isq1146tv073f440", "d8c1iss9g1ktqmlpvifg",
            "d8c1it3sv8vo2t0hsm00", "d8c1isc9g1ktqmlpvie0"]
F_AKALON = ["d8lb0hbsv8vo2t0lbmi0", "d8lb0h3sv8vo2t0lbmh0", "d8lb0h3sv8vo2t0lbmhg",
            "d8la06k9g1ktqmlte320"]
# AI tarjimon quloqchinlar
EAR_BLACK   = ["d7vc0ak9g1ktqmll6pmg", "d7vc0ak9g1ktqmll6pl0", "d7vc0ai1146tv06ummm0",
               "d7vc0ak9g1ktqmll6pkg"]
EAR_CREAM_A = ["d7vf31i1146tv06uo4vg", "d7vf3021146tv06uo4tg", "d7vf3121146tv06uo4ug",
               "d7vf313sv8vo2t0d5290"]
EAR_CREAM_B = ["d7vf31a1146tv06uo4v0", "d7vf31jsv8vo2t0d529g", "d7vf31jsv8vo2t0d52a0"]
# Quvvatlash kabellari
CABLE_A = ["d6k4vglsp2tohdbca3fg", "d6k4vhos9rf3ubqvbc5g", "d0rupmi7s4fo7mqbd0lg",
           "d0ta4hq7s4fo7mqbmo9g"]
CABLE_B = ["cs19c9k0u44g6joqqt80", "cs19c9ksslojjk5riac0", "cs19c9ksslojjk5riacg",
           "cs19c9ssslojjk5riadg"]
# Kolonkalar (Raduga)
SPK_KAR_A = ["cvj4dj6i4n36ls419q1g", "cvj4dodpb7f9qcnk075g", "cvj4dktpb7f9qcnk0740",
             "cvj4doei4n36ls419q40"]
SPK_KAR_B = ["cvj4dlui4n36ls419q2g", "cvj4dmlpb7f9qcnk074g", "cvj4dobvgbkm5ehmdfu0"]
SPK_BAR   = ["d42ubt6j76okhkd9gvng", "d42ubt5sp2tj49o81pcg", "d42ubt6j76okhkd9gvn0"]
# Boshqa do'konlar
POOL    = ["d8ok2m3sv8vo2t0mmcl0", "d82352bsv8vo2t0e854g", "d82352i1146tv06vqtvg",
           "d03r0r47fd1idpht8l20"]                                         # karkasli basseyn
KOMOD   = ["d6293d3vgbkv4qppvl4g", "cpmgok36eisq2rkc6uag", "d48tdiuj76ohd6e0u8d0",
           "d48tditsp2tr82i3l07g", "d48tdjdsp2tr82i3l08g", "d48tditv2sjo4rvhj8sg"]  # trimo/komod
STELLAJ = ["d8h83ta1146tv075b4ag", "d8h7nc49g1ktqmlrr630", "d8h83uk9g1ktqmlrrc30",
           "d8h7nc3sv8vo2t0joa50", "d8h83vrsv8vo2t0joft0", "d8h7nc21146tv075aumg"]  # polka/stellaj
ORG     = ["d2i6qid2lln7hego4vug", "d2jdgkt2llnd6juib0o0", "d2jdgkviub35i07h1po0",
           "d2jdgkt2llnd6juib0p0", "d2i6qv34eu2g1liuf1o0", "d2i6r452lln7hego50ag",
           "d2i6sgr4eu2g1liuf2fg"]                                         # organayzer
TRENAJ  = ["d6srgus3obpjedc2dtc0", "d6srlma1146lmcd3c1s0", "d6srlma1146lmcd3c1rg"]  # trenajyor
BANKA   = ["ctaq0qlpb7f7ago7rg5g", "ctaq0rei4n3ehka2uupg"]                 # banochki

# ── product_id -> rasm to'plami ──────────────────────────────────────────────
MAP = {
    # YANGI DINAMO electronic
    163: TV_ARTEL32,  # Televizor Rosso 32 android
    164: TV_MOONX_A,  # Samsung 32 smart tv
    165: TV_MOONX_B,  # Televizor Rosso 43 android tv
    166: OV_MAGNA,    # Duxovka itimat 45 litr
    167: OV_RETRO,    # Duxovka artel 42 litr lux
    168: OV_ARTEL60,  # Duxovka Ideal 45 litr
    169: OV_RETRO,    # Duxovka artel 36 litr
    170: OV_ARTEL60,  # duxofka Itimat 65 litr
    171: F_UNIVER,    # Ventilyator (190k)
    172: F_LAMO,      # Ventilyator Air (330k)
    173: F_AKALON,    # Vintelyator temir 5 parrak (180k)

    # ProMan Electronics
    1:  EAR_BLACK,    # AI tarjimon Aquloqchin (180k)
    3:  EAR_CREAM_A,  # AI tarjimon quloqchin (183k)
    4:  EAR_CREAM_B,  # AI tarjimon quloqchin (193k)
    5:  EAR_BLACK,    # AI tarjimon quloqchin (230k)
    6:  EAR_CREAM_A,  # AI tarjimon quloqchin (230k)
    8:  CABLE_A,      # Quvvatlash kabeli (28k)
    9:  CABLE_B,      # tezkor quvvatlash kabel (28k)
    10: CABLE_A,      # Tezkor quvvatlash kabel (28k)

    # Raduga Electronika
    32: SPK_KAR_A,    # Kalonka (800k)
    33: SPK_BAR,      # Kalonka (600k)
    34: SPK_KAR_B,    # Kalonka (500k)

    # Azamatov Naimjon (ventilyatorlar - Bravo setlari)
    26: F_LAMO,       # Ventelyator (150k)
    27: F_UNIVER,     # Ventilator (450k)
    28: POOL,         # Bassen (2M)
    # Nishonov Toshboy
    29: KOMOD,        # Trimo = oynali tortmali komod (1.65M)
    59: STELLAJ,      # Polka = do'kon stellaji (8M)
    # Malaxitovaya shkatulca
    31: ORG,          # Organayzer (40k)
    161: TRENAJ,      # Trenajyor (30k)
    162: BANKA,       # Banochki (23k)
    # DeFlora id=30 (atirgul) — o'zgartirilmadi (gul do'koni o'z rasmi qoladi)
}

# ── qo'llash + restore zip ───────────────────────────────────────────────────
if __name__ == "__main__":
    import json, os, glob, zipfile
    from datetime import datetime
    HERE = os.path.dirname(os.path.abspath(__file__))
    IMG = "https://images.uzum.uz/{}/t_product_540_high.jpg"
    prods = json.load(open(os.path.join(HERE, "products.json"), encoding="utf-8"))
    changed = 0
    for p in prods:
        if p.get("id") in MAP:
            p["photos"] = [IMG.format(i) for i in MAP[p["id"]]]
            p.pop("photo", None)
            changed += 1
    json.dump(prods, open(os.path.join(HERE, "products.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"{changed} ta mahsulot rasmi yangilandi.")
    out = os.path.join(os.path.expanduser("~"), "Downloads",
                       f"restore_{datetime.now().strftime('%Y%m%d_%H%M')}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for f in glob.glob(os.path.join(HERE, "*.json")):
            z.write(f, arcname=os.path.basename(f))
    print("ZIP:", out)
