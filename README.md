# Proman Market

Telegram Marketplace Bot — ko'p sotuvchili (multi-seller) bozor.

## Imkoniyatlar

- Ko'p sotuvchili bozor (har shahar bo'yicha do'konlar)
- Sotuvchi arizasi (FSM oqimi) va admin tasdig'i
- Mahsulot katalogi, qidiruv, ❤️ istaklar
- Buyurtma berish + 10% oldi-to'lov (platforma komissiyasi)
- To'lov chekini admin tasdiqlashi
- Kurier tizimi (yetkazib berish — shu bugunoq)
- Xaridor ma'lumotlari sotuvchidan yashirin (faqat kurierga ochiladi)
- Admin panel: sotuvchilar, buyurtmalar, kurierlar, hisobotlar (Excel/Word), audit jurnali

## Texnologiyalar

- Python 3.11
- aiogram 3.7
- Ma'lumotlar: JSON fayllar (`data/` papkada) — `app/storage.py`
- Deploy: Docker / Railway

## Sozlash

1. Reponi clone qiling
2. `.env.example` faylidan `.env` yarating va qiymatlarni to'ldiring:
   ```
   BOT_TOKEN=telegram_bot_tokeningiz
   OWNER_ID=telegram_id_raqamingiz
   ADMIN_USERNAME=admin_username
   PLATFORM_CARD=karta_raqami
   COMMISSION_RATE=0.10
   ```
3. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```
4. Botni ishga tushiring:
   ```bash
   python -m app.main
   ```

## Docker

```bash
docker build -t proman-market .
docker run --env-file .env -v proman_data:/app/data proman-market
```

## ⚠️ Muhim — ma'lumotlarni saqlash (Railway / Docker)

Bot barcha ma'lumotni (sotuvchilar, buyurtmalar, mahsulotlar) `data/` papkasidagi
JSON fayllarga yozadi. Bu papka **doimiy diskka (persistent volume) ulanmasa**,
har deploy / qayta ishga tushirishda **o'chib ketadi**.

- **Railway:** loyihaga **Volume** qo'shing va uni `/app/data` ga ulang.
- **Docker:** `-v proman_data:/app/data` bilan ishga tushiring (yuqoridagidek).

Aks holda yangilanish qilganingizda barcha buyurtma va do'konlar yo'qoladi.

## Loyiha tuzilishi

```
app/
├── main.py                  # Kirish nuqtasi (bot polling) + seed
├── storage.py               # JSON fayl asosidagi ma'lumotlar saqlovchi
├── album.py                 # Albom (media group) rasmlarini yig'uvchi
├── ui.py                    # Matn/format yordamchilari
├── seed_*.py                # Do'konlarga boshlang'ich mahsulot qo'shuvchilar
├── bot/
│   ├── bot.py               # Bot instance
│   └── dispatcher.py        # Dispatcher + routerlar + menyu middleware
├── handlers/
│   ├── start.py             # /start komandasi
│   ├── common.py            # Bozor, qidiruv, buyurtma oqimi, profil
│   ├── admin.py             # Admin panel
│   ├── seller_panel.py      # Sotuvchi paneli
│   └── seller/
│       └── application.py   # Sotuvchi arizasi (FSM)
├── keyboards/
│   └── seller.py            # Klaviaturalar
├── states/
│   └── seller_application.py # FSM holatlari
└── app/
    └── config/
        └── settings.py      # Pydantic sozlamalar (.env)
```
