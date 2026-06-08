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
├── main.py                  # Entry point (bot polling)
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
