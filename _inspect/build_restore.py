# -*- coding: utf-8 -*-
"""Bravo electronics mahsulotlarining Uzum'mas (Telegram) rasmlarini Uzum
rasmlariga almashtiradi (faqat 'photos', narx va boshqa narsalar tegmaydi).
Keyin barcha .json fayllarni /restore uchun bitta zip qiladi."""
import json, os, glob, zipfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = "https://images.uzum.uz/{}/t_product_540_high.jpg"
def urls(ids): return [IMG.format(i) for i in ids]

# ── Uzum rasm to'plamlari (jonli sahifalardan, galereya, har biri >=3) ───────
# Muzlatgichlar
A_ARTEL316 = ["d2a9m952lln4bo5dbrc0", "cnmv10tbl7rtgkb9pa00", "cnmv10ku2hhlb05hfbvg"]
B_BIRYUSA  = ["d6kn168s9rf3ubqvjohg", "d6kn18lsp2tohdbchvp0", "d6kn1aa1146th72stts0",
              "d6kn1c8s9rf3ubqvjon0", "d6kn1edsp2tohdbchvsg"]
C_FERRE    = ["d8nug1bsv8vo2t0mcqcg", "cmjphfbifoubkc6ocipg", "cmjphf925ku8ad8ho5ig",
              "cmjphb9s99ouqbfqv0pg", "cppckej6eisq2rkco4bg"]
# Ventilyatorlar
F_LAMO     = ["d8kp3lbsv8vo2t0l4km0", "d8kp3eq1146tv076nblg", "d8kp3i49g1ktqmlt7p5g"]
F_UNIVER   = ["d8c1isrsv8vo2t0hslvg", "d8c1isq1146tv073f440", "d8c1iss9g1ktqmlpvifg",
              "d8c1it3sv8vo2t0hsm00", "d8c1isc9g1ktqmlpvie0"]
F_AKALON   = ["d8lb0hbsv8vo2t0lbmi0", "d8lb0h3sv8vo2t0lbmh0", "d8lb0h3sv8vo2t0lbmhg",
              "d8la06k9g1ktqmlte320"]
# Kulerlar
K_WELL     = ["d4i3njdv2sjnqk4ilba0", "d4i3njdv2sjnqk4ilb9g", "d4i3njej76ooegrmragg",
              "d425hcdsp2tj49o7q5og"]
K_SENSOR   = ["d8jfts49g1ktqmlsn9ng", "d8jfts49g1ktqmlsn9n0", "d8jfts21146tv0766ut0",
              "d8jftsa1146tv0766utg", "d8i1req1146tv075m1ag"]
K_LORETTO  = ["d7pilo49g1ktqmlirglg", "d7ob1qa1146tv06rqa40", "d7pilhc9g1ktqmlirgfg",
              "d7pilsi1146tv06sbjp0", "d7pipbq1146tv06sbm0g"]
# Mini konditsioner (havo sovutgich)
AIRCOOLER  = ["d8gn2jq1146tv0755g7g", "d8gn2jrsv8vo2t0jiss0", "d8gn2jq1146tv0755g6g",
              "d8gte5bsv8vo2t0jm7k0", "d8gteik9g1ktqmlrp38g"]

# ── product_id -> rasm to'plami (Bravo electronics) ─────────────────────────
MAP = {
    # Ventilyatorlar
    2:  F_AKALON,   # Vintelyator (77k, kichik)
    18: F_AKALON,   # Ventilyator (75k, kichik)
    11: F_UNIVER,   # Venteliyator (200k)
    19: F_UNIVER,   # Ventilyator (220k)
    12: F_LAMO,     # Venteliyator (180k)
    # Mini konditsioner
    13: AIRCOOLER,  # Mini Konditsioner (750k)
    # Kulerlar
    14: K_SENSOR,   # KULLER (1.9M)
    15: K_WELL,     # KULLER (1.3M)
    16: K_LORETTO,  # KULLER LORETTO (1.6M)  <- aynan mos
    17: K_WELL,     # KULLER HanTaji (1.3M)
    # Muzlatgichlar
    20: B_BIRYUSA,  # Muzlatkich (2.65M)
    21: A_ARTEL316, # MUZLATGICH (2.75M)
    22: C_FERRE,    # MUZLATGICH (2.55M)
    23: B_BIRYUSA,  # MUZLATGICH (2.65M)
    24: A_ARTEL316, # MUZLATGICH (2.45M)
    25: C_FERRE,    # MUZLATGICH (2.95M)
}

prods = json.load(open(os.path.join(HERE, "products.json"), encoding="utf-8"))
changed = 0
for p in prods:
    if p.get("id") in MAP:
        p["photos"] = urls(MAP[p["id"]])
        p.pop("photo", None)  # eski bitta rasmli maydon bo'lsa olib tashlaymiz
        changed += 1
json.dump(prods, open(os.path.join(HERE, "products.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(f"{changed} ta mahsulot rasmi yangilandi.")

# ── barcha .json -> restore zip ─────────────────────────────────────────────
out = os.path.join(os.path.expanduser("~"), "Downloads",
                   f"restore_{datetime.now().strftime('%Y%m%d_%H%M')}.zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for f in glob.glob(os.path.join(HERE, "*.json")):
        z.write(f, arcname=os.path.basename(f))
print("ZIP:", out)
