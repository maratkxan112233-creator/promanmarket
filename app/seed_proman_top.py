"""Bir martalik xavfsiz "seed": ProMan Electronics do'koniga Uzum Market'da
oxirgi kunlarda ENG KO'P SOTILGAN 60 xil elektronika va maishiy texnika
mahsulotini qo'shadi.

Bot ishga tushganda chaqiriladi. Mantiq [seed_bikes.seed_products] da —
mavjud mahsulotlarga TEGMAYDI, faqat hali yo'q bo'lganlarini qo'shadi,
shuning uchun bot necha marta qayta ishga tushsa ham takror qo'shilmaydi.

Nom, narx va rasmlar Uzum Market'dan (images.uzum.uz CDN) olingan —
har bir mahsulotda 3 ta rasm.
"""

import logging

from app.seed_bikes import seed_products
from app.seed_proman import _find_proman_seller

logger = logging.getLogger(__name__)

# (nom, tavsif, narx so'm, [Uzum rasm ID lari]) — har birida 3 ta rasm.
_PRODUCTS = [
    # ── Quloqchinlar va audio ───────────────────────────────────────────────
    ("Simsiz quloqchin P9, mikrofonli",
     "P9 simsiz Bluetooth quloqchin — telefon va kompyuterga tez ulanadi, "
     "mikrofoni bilan qo'ng'iroqlarda toza ovoz beradi.",
     34000, ["d8865js9g1ktqmloqdug", "d8864ck9g1ktqmloqd5g", "d8868kjsv8vo2t0gnob0"]),

    ("Simsiz quloqchin Pods Pro, sensorli",
     "Pods Pro simsiz quloqchin — iPhone va Android uchun, sensorli "
     "boshqaruv va quvvatlash g'ilofi bilan.",
     67620, ["d868pp3sv8vo2t0fvbvg", "d868q4jsv8vo2t0fvc8g", "d868q5rsv8vo2t0fvca0"]),

    ("Mini kolonka WS-887, USB + Bluetooth",
     "WS-887 portativ mini kolonka — Bluetooth 5.0, kuchli bas va 360° "
     "ovoz, uy va sayohat uchun ixcham.",
     43200, ["d8ps2f49g1ku9j5bpd00", "d8ps10s9g1ku9j5bpbcg", "d8ps8qk9g1ku9j5bpjcg"]),

    ("Karaoke kolonka K12, 2 ta mikrofonli",
     "Karaoke uchun portativ Bluetooth kolonka, komplektda 2 ta mikrofon — "
     "oilaviy bayram va davralar uchun.",
     79900, ["d80ou7a1146tv06v84c0", "d6oh84lsp2tohdbe1dng", "d6oh84lsp2tohdbe1do0"]),

    # ── Quvvatlash va kabellar ──────────────────────────────────────────────
    ("Powerbank 10000 mAh, 22.5 Vt tezkor",
     "Jokade powerbank, 10000 mA/soat, 22.5 Vt tezkor quvvatlash — "
     "smartfonni bir necha marta zaryadlaydi.",
     72500, ["d6nosd8s9rf3ubr0qvv0", "d6nota5sp2tohdbdmp40", "d8k3cbk9g1ktqmlsuou0"]),

    ("Powerbank 20000 mAh, 22.5 Vt tezkor",
     "Tashqi akkumulyator 20000 mA/soat, 22.5 Vt tez zaryadlash — safar va "
     "uzoq kunlar uchun katta sig'im.",
     115000, ["d71riq43obpjedc439pg", "d71rj2s3obpjedc43a2g", "d8ip90k9g1ktqmlseb3g"]),

    ("Zaryadlovchi kabel 4 tasi 1 da, 65 Vt",
     "4-in-1 tezkor quvvatlash kabeli, 65 Vt, 1 metr — USB, Type-C va "
     "Lightning: bitta kabel hamma telefonga.",
     15550, ["d68sp3t75tf1bsrpi9h0", "d68sp79e6ph7gqpi6erg", "d68sp7d75tf1bsrpi9i0"]),

    ("Tezkor adapter Kingidike 120 Vt, USB-C",
     "Kingidike 120 Vt tezkor zaryadlovchi adapter — qizib ketishdan "
     "himoya, smartfonni daqiqalarda quvvatlaydi.",
     28000, ["d8q52ma1146phmqdpmt0", "d8q52ma1146phmqdpms0", "d8q52ma1146phmqdpmsg"]),

    ("iPhone uchun USB-C — Lightning kabel",
     "USB-C dan Lightning tezkor zaryadlash kabeli — iPhone X dan 16 "
     "gacha barcha modellarga mos, mustahkam o'rim.",
     18000, ["d929pm21146phmqh4o5g", "d929qujsv8vnuj129p0g", "d929poi1146phmqh4o6g"]),

    ("OTG adapter Type-C — USB, universal",
     "Universal OTG adapter: Type-C dan USB ga va aksincha — telefonga "
     "fleshka, sichqoncha va klaviatura ulash uchun.",
     9900, ["d2a7nfd2lln4bo5dakd0", "d2a7nr52lln4bo5daklg", "d2a7ntfiub3csu9vfsa0"]),

    # ── Telefon aksessuarlari ───────────────────────────────────────────────
    ("Telefon ushlagichi 360°, qisqichli, 50 sm",
     "Qisqichli telefon ushlagich, 50 sm prujinali, 360° aylanadi — "
     "yotib yoki ish paytida qo'lni bo'shatadi.",
     27900, ["cuhm07ei4n324lr8d1p0", "cuhm08ei4n324lr8d1q0", "cuhm0e5ht56sc95d24fg"]),

    ("Selfi tayoqcha-shtativ, LED chiroqli",
     "Selfi tayoqcha va tripod-shtativ bir qurilmada — LED chiroq va "
     "masofadan pult bilan, barcha telefonlarga mos.",
     37000, ["cvrs3itpb7fbmqmnbrig", "cvud095pb7fbmqmnsrqg", "cvud0l6i4n37npaoikbg"]),

    ("Xotira kartasi INVO microSD",
     "INVO microSD xotira kartasi — telefon va kameradagi rasm-videolar "
     "uchun ishonchli qo'shimcha xotira.",
     35000, ["d3dc0va1146soq7c714g", "d11dgj0n274lpu38c9m0", "d11dgir3uvpglcmar4lg"]),

    # ── Smart soatlar va taqiladigan qurilmalar ─────────────────────────────
    ("Aqlli soat Smart Watch T800 Pro Max",
     "T800 Pro Max aqlli soati — qo'ng'iroq, qadam va yurak urishi "
     "nazorati, Android va iOS bilan ishlaydi.",
     64000, ["cspq245pq3ggq63cuf1g", "cspluk5pq3ggq63csrv0", "ct1n99dpq3ggq63f5cv0"]),

    ("Fitnes-braslet, puls va bosim nazorati",
     "Aqlli fitnes-braslet — puls, qon kislorodi va qadamni real vaqtda "
     "o'lchaydi, suvga chidamli korpus.",
     297000, ["d7lo7ca1146tv06qjp5g", "d7lo7nad955cjr7cvsu0", "d7ucuv3sv8vo2t0cq1ng"]),

    ("Aqlli ko'zoynak Smart Glasses CY01, AI",
     "CY01 aqlli ko'zoynak — AI ovozli yordamchi, HD kamera, musiqa va "
     "qo'ng'iroqlar uchun o'rnatilgan karnay.",
     599990, ["d4ac4emj76ohd6e1d1hg", "d4ac4elsp2tr82i43re0", "d4ac4elsp2tr82i43reg"]),

    ("Telefon Novey Aura V1, tugmali",
     "Novey Aura V1 tugmali telefon — yupqa korpus, 2.4\" ekran, 2 SIM, "
     "Type-C quvvatlash. Sodda va ishonchli.",
     649000, ["d7kj9rbsv8vghom2jbig", "d7kjb6rsv8vghom2jbpg", "d7kj9r3sv8vghom2jbi0"]),

    ("LED stol soati, ko'p funksiyali",
     "Zamonaviy LED stol soati — yorqin displey, budilnik va harorat "
     "ko'rsatkichi, yotoqxona va ofis uchun.",
     99000, ["cvmnktk7fd1p445qtcrg", "cvmnktmi4n37npamp0qg", "cvmnktlpb7fbmqmm3jeg"]),

    # ── Xavfsizlik kameralari ───────────────────────────────────────────────
    ("Tashqi kuzatuv kamerasi Wi-Fi, HD",
     "Aqlli tashqi kuzatuv kamerasi — HD sifat, 355° panoramik aylanish, "
     "telefondan masofadan kuzatish.",
     160000, ["d7bl3ek3obpufnhaj2hg", "d7bl5143obpufnhaj410", "d7bl3ec3obpufnhaj2h0"]),

    ("CCTV video kuzatuv to'plami, 4 kamera",
     "CCTV to'plam: 4 ta HD 1080P kamera — tungi ko'rish, harakat sensori "
     "va 24/7 yozuv. Uy va do'kon uchun.",
     854000, ["d7te5r3sv8vo2t0caf7g", "d7te61bsv8vo2t0cafbg", "d7te6ua1146tv06ttkng"]),

    # ── Wi-Fi va tarmoq ─────────────────────────────────────────────────────
    ("Wi-Fi kuchaytirgich TP-Link RE",
     "TP-Link RE signal kuchaytirgichi — uyning har burchagiga barqaror "
     "Wi-Fi, ikki diapazonli tezkor ulanish.",
     303000, ["d3me07gn274r8aok28ag", "d3me07gn274r8aok28a0", "d3me09on274r8aok28d0"]),

    ("Mini router — repiter, 3 tasi 1 da",
     "Mini router, signal kuchaytirgich va repiter bir qurilmada — "
     "rozetkaga ulanadi, Wi-Fi qamrovini kengaytiradi.",
     129000, ["d8l6m749g1ktqmltbf80", "d1n1k609oh61u9a3q2pg", "d1n1kn09oh61u9a3q320"]),

    ("Wi-Fi adapter Go-Des GD-BT318",
     "Go-Des GD-BT318 Wi-Fi adapteri, 1200 m gacha qamrov — kompyuterga "
     "uzilishlarsiz simsiz internet.",
     97990, ["d8nr2trsv8vo2t0ma7s0", "d8nr34k9g1ktqmludkr0", "d8nr35k9g1ktqmludkrg"]),

    ("USB Bluetooth 5.3 adapter",
     "USB Bluetooth 5.3 adapter — kompyuterga quloqchin, sichqoncha va "
     "joystik ulash uchun, Plug&Play o'rnatish.",
     46000, ["d6r7vca1146th72vhr2g", "d60e7kmf4hvsl3r2idig", "d79ov9rsv8vlb6mm9iog"]),

    # ── Kompyuter aksessuarlari ─────────────────────────────────────────────
    ("Veb-kamera 4K, mikrofonli",
     "4K veb-kamera, o'rnatilgan mikrofon va 120° keng burchak — onlayn "
     "dars va video-qo'ng'iroqlar uchun.",
     199000, ["d80tess9g1ktqmllrl4g", "d80teda1146tv06vbjtg", "d80tedk9g1ktqmllrkrg"]),

    ("Simsiz sichqoncha, RGB, shovqinsiz",
     "Simsiz shovqinsiz sichqoncha — RGB yoritish, USB-C zaryadlash, "
     "ish va o'yin uchun qulay ergonomika.",
     39910, ["crk805k3t0q1s5n3tfr0", "crktb5ijot51rkb1oahg", "crktac1bjcvd8a776gmg"]),

    ("Klaviatura + sichqoncha, simsiz Bluetooth",
     "Simsiz Bluetooth klaviatura va sichqoncha to'plami — telefon, "
     "planshet va noutbukka bir vaqtda ulanadi.",
     73000, ["d64o8l43obpn7570nog0", "d64ocdmdd7e7njq7u320", "d64oc2c3obpn7570nqf0"]),

    ("Fleshka SanDisk USB 3.0",
     "SanDisk original USB 3.0 fleshka — 130 MB/s gacha o'qish tezligi, "
     "hujjat va fayllar uchun ishonchli.",
     97500, ["d7dursa1146ojv9e2l90", "d7dusai1146ojv9e2lh0", "d7dusajsv8vlb6mo1agg"]),

    ("MicroSD karta 512 GB, yuqori tezlik",
     "512 GB microSDXC karta, Class 10 — telefon, kamera va "
     "videoregistrator uchun katta va tez xotira.",
     98000, ["d6a7audv2sjru72527u0", "d6a7b09e6ph7gqpir1k0", "d6a7b1nqkmalqfncfgfg"]),

    ("Kardrider 4 tasi 1 da, SD/microSD",
     "Universal kardrider — SD, microSD va boshqa kartalarni kompyuterga "
     "ulaydi, 4 slot bitta qurilmada.",
     29000, ["cr5eqm7iraat934qu39g", "cr5eqo6sbq7g1s9aphd0", "cr5eqr7iraat934qu3ag"]),

    ("Noutbuk stendi, alyuminiy",
     "Alyuminiy noutbuk stendi — bo'yni charchatmaydigan ergonomik "
     "balandlik, sirg'almaydigan rezina taglik.",
     59000, ["d78g5s21146ojv9brnrg", "d7ac0tq1146ojv9cibmg", "d6he0l0s9rfd9u94qcvg"]),

    ("Sichqoncha gilamchasi 90×40 sm",
     "Katta o'lchamli sichqoncha gilamchasi, 90×40 sm — rezina asosli, "
     "sirpanmaydi, klaviatura ham sig'adi.",
     36500, ["d5tila2dk6jhqj0sv50g", "d67l2cnqkmalqfnbbdi0", "d5tiloidk6jhqj0sv59g"]),

    # ── TV va proyektorlar ──────────────────────────────────────────────────
    ("Smart televizor WellStars 32\"/43\"",
     "WellStars Smart TV, 32/43 dyuym — Android, Wi-Fi va Full HD: "
     "sevimli filmlar va YouTube bitta ekranda.",
     1265210, ["d2en8bviub3brtual5o0", "cv9rn8tpb7f9qcnhed20", "cv9rn8ui4n36ls3unsm0"]),

    ("Smart TV Box YouWei, 2/16 GB",
     "YouWei TV pristavkasi, 2/16 GB — oddiy televizorni to'liq Smart TV "
     "ga aylantiradi, ilovalar va IPTV bilan.",
     199000, ["d67ha4t75tf1bsrovuh0", "d8645oa1146tv071fbk0", "d661vldsp2tk1m7hpefg"]),

    ("Mini proyektor, pultli, USB",
     "Kompakt mini proyektor — film va prezentatsiyalarni katta ekranda "
     "ko'rsatadi, uy va ofis uchun qulay.",
     350000, ["d86r8crsv8vo2t0g6ivg", "d86r8k3sv8vo2t0g6j2g", "d86r8lk9g1ktqmlo9blg"]),

    ("LED proyektor-planetarium, tungi chiroq",
     "LED kosmik proyektor, 10 slayd sayyora — bolalar xonasiga sehrli "
     "yulduzli osmon, USB dan ishlaydi.",
     69990, ["d843o849g1ktqmln6d70", "d843ocs9g1ktqmln6d90", "d843osk9g1ktqmln6df0"]),

    ("Raqamli TV tyuner DVB-T2",
     "DVB-T2 raqamli tyuner — 20 dan ortiq kanalni HD sifatda bepul "
     "ko'rsatadi, pult bilan, ulash juda oson.",
     141570, ["d0rh4va7s4fo7mqbb37g", "d61d7kvqkmamvfqsn3p0", "d0rh4ui7s4fo7mqbb370"]),

    ("Televizor braketi, 17–43 dyuym",
     "Devorga o'rnatiladigan TV braketi, 17–43 dyuym — mustahkam po'lat, "
     "xonani keng va ozoda qiladi.",
     42000, ["crq16hqjot51rkb2vko0", "ci6n6qdenntd8rfbmc30", "ci6n6qf5d7kom1ti0ltg"]),

    ("Proyektor kronshteyni, devor va shift",
     "Proyektor uchun sozlanuvchi kronshteyn — devor va shiftga "
     "o'rnatiladi, barcha mashhur brendlarga mos.",
     106000, ["ctpohblht56ksubb597g", "ctpohhk5j42bjc460d4g", "ctpohe45j42bjc460d30"]),

    ("HDMI kabel, 1.5 m",
     "HDMI kabel 1.5 metr — televizor, monitor va o'yin pristavkasini "
     "yuqori sifatda ulash uchun.",
     29400, ["cq3b3lb5qt1gj8de36fg", "cq3b3lb5qt1gj8de36g0", "cq3b3l8sarnfdo9aeto0"]),

    # ── Oshxona texnikasi ───────────────────────────────────────────────────
    ("Blender statsionar + kofe maydalagich",
     "Statsionar blender — smuzi, sharbat va kofe maydalash bir "
     "qurilmada, turbo va impuls rejimlari bilan.",
     189000, ["d7pghdbsv8vo2t0amq70", "d7pghaq1146tv06s9t50", "d72ilnk3obpjedc4dhl0"]),

    ("Chopper — elektr maydalagich",
     "Elektr chopper-maydalagich, shisha idishli — go'sht, piyoz va "
     "yong'oqni soniyalarda maydalaydi.",
     116000, ["d705c821146ojv98cdug", "d45mgrlv2sjo4rvglsg0", "d45o8dlsp2tk7h63hf80"]),

    ("Sharbat chiqargich Bosch BS-2002, 1000 Vt",
     "Bosch BS-2002 elektr sharbat chiqargich, 1000 Vt, 2 tezlik — har "
     "kuni yangi tabiiy sharbat.",
     399000, ["d8rbn449g1ku9j5cems0", "d8rbn43sv8vnuj0veq4g", "d8rbn4c9g1ku9j5cemsg"]),

    ("Elektr choynak, tez qaynatadigan",
     "Elektr choynak — tez qaynatadi, avtomatik o'chish va quruq "
     "ishlashdan himoya tizimi bilan.",
     53900, ["d7l4ndvh478hcebt940g", "d7l4nrjsv8vo2t08nkcg", "d7l4o4fh478hcebt94bg"]),

    ("Mini elektr qozon Lucky Duck",
     "Lucky Duck mini elektr qozon — talaba va kichik oila uchun: "
     "sho'rva, makaron va tuxumni tez tayyorlaydi.",
     129000, ["d882bvc9g1ktqmlonvng", "d882bvc9g1ktqmlonvn0", "d882c03sv8vo2t0gl6hg"]),

    ("Tuxum pishirgich, ko'p funksiyali",
     "Elektr tuxum pishirgich — bug'da bir tekis pishiradi, nonushta "
     "tayyorlashni osonlashtiradi.",
     199000, ["cvj7rcei4n36ls41b9e0", "d8uh7oa1146phmqfj400", "d8uh7pc9g1ku9j5do8v0"]),

    ("Mini vafli pishirgich Vena",
     "Mini vafli pishirgich, yopishmaydigan qoplama — Belgiya vaflisi va "
     "mazali nonushta bir necha daqiqada.",
     84000, ["d1ppbsg9oh61u9a4f6qg", "d1ppc9nnrko5rk1c14hg", "d1ppcag9oh61u9a4f740"]),

    ("Toster Uakeen, 2 bo'limli, 1000 Vt",
     "Uakeen toster, 2 slot, 1000 Vt — qovurish darajasi sozlanadi, "
     "ertalabki issiq tost bir zumda.",
     305000, ["d4vcqv3s2ta3qj5kjq00", "d4vcrgjtqdhua1usdvbg", "d4vcrvrtqdhua1usdvig"]),

    ("Kapuchinator — sut ko'pirtirgich",
     "Mini kapuchinator — sutni soniyalarda ko'pirtiradi: uyda kafe "
     "darajasidagi kapuchino va latte.",
     33950, ["d880ng49g1ktqmlon550", "d880p1jsv8vo2t0gkckg", "d866eec9g1ktqmlo0sjg"]),

    # ── Uy texnikasi ────────────────────────────────────────────────────────
    ("Yuvuvchi changyutgich Karcher SE 3",
     "Karcher SE 3 Compact yuvuvchi changyutgich — gilam va mebelni suv "
     "bilan chuqur tozalaydi. Original.",
     4165000, ["cupdk9dht56sc95faau0", "cudkq745j42bjc4bbrrg", "cudkq7mi4n324lr772ug"]),

    ("Elektr dazmol NIKAI, 1200 Vt",
     "NIKAI elektr dazmol, 1200 Vt, po'lat tovon — kiyimni tez va silliq "
     "dazmollaydi, 1 yil kafolat.",
     159000, ["cr3cdqviraat934qdu3g", "d5ijhngjsv1q0h275ksg", "d5ijhpjtqdhu87jrng50"]),

    ("Qo'l bug'lagich-dazmol, 3 tasi 1 da",
     "Qo'l bug'lagich dazmol, 1200 Vt — 15 soniyada qiziydi, osilgan "
     "kiyimni ham tez tekislaydi.",
     189000, ["d1v7t9viub3cuo9ddh3g", "d4bqc2dv2sjo4rvifk90", "d1pf3a7nrkoeo1hk491g"]),

    ("Mini ventilyator, portativ, quvvatlanadigan",
     "Ixcham portativ ventilyator — uy, ofis va sayohatda issiq kunlarda "
     "qutqaruvchi, USB dan quvvatlanadi.",
     199000, ["d8v621q1146phmqfr5e0", "d8v5vpjsv8vnuj1108pg", "d8v5vrbsv8vnuj1108s0"]),

    # ── Parvarish texnikasi ─────────────────────────────────────────────────
    ("Trimmer Vintage T9, soch va soqol",
     "Vintage T9 akkumulyatorli trimmer — soch va soqolni aniq oladi, "
     "uyda sartarosh xizmati.",
     41990, ["d1que809oh61u9a4ntpg", "d1nrrutsp2tm1pihuvpg", "d1nrruo9oh61u9a41h70"]),

    ("Trimmer Philips OneBlade QP2824",
     "Philips OneBlade — soqol oladi, to'g'rilaydi va shakl beradi: har "
     "qanday uzunlik uchun bitta qurilma. Original.",
     650000, ["d5bqnk3s2tab83s9f6h0", "d5bqntojsv1neacsccjg", "d5bqntrs2tab83s9f6kg"]),

    ("Fen BASOCK, professional",
     "BASOCK professional soch quritgich — kuchli havo oqimi bilan tez "
     "quritadi va sochni jonli ko'rsatadi.",
     80000, ["d8ooovc9g1ku9j5baur0", "d8palsbsv8vnuj0uiin0", "d8palu49g1ku9j5binjg"]),

    ("Gofre qisqich — uchtalik ployka",
     "Uchtalik gofre ployka — sochga tabiiy to'lqin va hajm beradi, "
     "keramik qoplama sochni asraydi.",
     148400, ["cppfr6j6eisq2rkcpb8g", "d7v0vc49g1ktqmll4p4g", "d8ugva49g1ku9j5do2h0"]),

    ("Yuz tozalagich, vakuumli, 6 nasadka",
     "Vakuumli yuz tozalagich — qora nuqtalarni olib tashlaydi, 6 "
     "nasadka, USB quvvatlash. Toza va silliq teri.",
     138310, ["d0fj4kb3uvph509thm9g", "d0fj4o8n274j5scm4vlg", "d0fj4pq7s4fo7mq8ke70"]),

    ("Ultratovushli yuz tozalash apparati",
     "Ultratovushli piling apparati — 4 rejim: tozalash, lifting va "
     "massaj. Salon parvarishi endi uyda.",
     119990, ["d37545r4eu2s0bgisdp0", "d3754h34eu2s0bgisdu0", "d3754pt2llnbilep2agg"]),

    ("Yuz uchun bug'li sauna",
     "Yuz saunasi — yumshoq issiq bug' teri g'ovaklarini ochadi, "
     "tozalaydi va chuqur namlantiradi.",
     345510, ["d97q3ji1146g73hra9fg", "d97q3o21146g73hra9ig", "d97q3k49g1ku9j5hqe0g"]),
]


def seed_proman_top() -> int:
    """Uzum'dagi eng ko'p sotilgan 60 mahsulotni ProMan do'koniga qo'shadi."""
    return seed_products(_PRODUCTS, _find_proman_seller, "ProMan Top-60")
