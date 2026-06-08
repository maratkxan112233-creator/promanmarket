# Man Market

Telegram Marketplace Bot

## Features

- Multi Seller Marketplace
- Seller Verification (FSM based application flow)
- Shopping Cart
- Order Management
- Receipt Verification
- Admin Panel
- Reports
- AI Search
- Recommendation System

## Stack

- Python 3.12
- Aiogram 3.4.1
- PostgreSQL + asyncpg
- SQLAlchemy 2.0 (async)
- Redis
- Railway (deployment)

## Setup

1. Clone the repo
2. Copy `.env.example` to `.env` and fill in your values:
   ```
   BOT_TOKEN=your_telegram_bot_token
   DATABASE_URL=postgresql+asyncpg://user:password@host:5432/man_market
   REDIS_URL=redis://localhost:6379
   OWNER_ID=your_telegram_user_id
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the bot:
   ```bash
   python -m app.main
   ```

## Docker

```bash
docker build -t man-market .
docker run --env-file .env man-market
```

## Project Structure

```
app/
├── main.py                  # Entry point (bot polling + Mini App HTTP server)
├── storage.py               # JSON fayl asosidagi ma'lumotlar saqlovchi
├── album.py                 # Albom (media group) rasmlarini yig'uvchi
├── bot/
│   ├── bot.py               # Bot instance
│   └── dispatcher.py        # Dispatcher + routers
├── handlers/
│   ├── start.py             # /start command
│   ├── common.py            # Bozor, qidiruv, zakaz oqimi, profil
│   ├── admin.py             # Admin panel
│   ├── seller_panel.py      # Seller panel
│   └── seller/
│       └── application.py   # Seller application FSM
├── keyboards/
│   └── seller.py            # All keyboards
├── states/
│   └── seller_application.py # FSM states
└── app/
    └── config/
        └── settings.py      # Pydantic settings (.env)
```

---

## 🛍 Mini App (Uzum'daqa do'kon interfeysi)

Mahsulotlar endi Telegram ichida **grid (karta)** ko'rinishda chiqadi — rasm, narx, chegirma, reyting va "shu bugun yetkazib berish" chipi bilan.

### Ishlash tartibi
- `app/main.py` ichidagi HTTP server ham health-check, ham Mini App'ni (`/`), ham `/api/products` va `/api/photo` (rasm proksisi) ni beradi.
- Botning pastki menyusida **"🛍 Do'kon (ilova)"** tugmasi paydo bo'ladi (faqat `WEBAPP_URL` sozlangan bo'lsa).
- Mahsulotda **"Buyurtma berish"** bosilsa — Mini App yopiladi va botdagi mavjud zakaz oqimi (olib ketish/dostavka → telefon → chek) ishga tushadi.

### Sozlash (Railway)
1. Railway → loyiha → **Settings → Networking → Generate Domain**. Hosil bo'lgan https manzilni oling.
2. Railway → **Variables**:
   - `WEBAPP_URL=https://<sizning-domeningiz>.up.railway.app`
   - (PORT'ni Railway o'zi beradi — qo'shish shart emas.)
3. Redeploy. Tugma chiqadi.

### Chegirma ko'rsatish (ixtiyoriy)
Mahsulot JSON'iga `"old_price": 99000` qo'shilsa — kartada `↓%` chegirma va ustidan chizilgan eski narx chiqadi. Bo'lmasa, oddiy narx ko'rinadi (soxta chegirma qo'yilmaydi).
