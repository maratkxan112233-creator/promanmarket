import asyncio
import logging

from app.bot.bot import bot
from app.bot.dispatcher import dp
from app.seed_ac import seed_all
from app.seed_bikes import seed_bikes
from app.seed_cars import seed_cars
from app.seed_conditioners import seed_conditioners
from app.seed_strollers import seed_strollers
from app.seed_bravo_video import seed_bravo_video
from app.seed_proman import seed_proman

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Proman Market starting...")
    # Bir martalik xavfsiz seed: Bravo electronics do'koniga mahsulotlarni
    # (konditsioner + kir yuvish mashinasi) — agar hali yo'q bo'lsa — qo'shadi.
    # Xato bo'lsa ham bot to'xtamasin.
    try:
        seed_all()
    except Exception:
        logger.exception("Seed (mahsulotlar) bajarilmadi")
    # DinamoKids do'koniga velosipedlar (yo'q bo'lsa) qo'shiladi.
    try:
        seed_bikes()
    except Exception:
        logger.exception("Seed (velosipedlar) bajarilmadi")
    # DinamoKids do'koniga bolalar minadigan mashinalari (yo'q bo'lsa) qo'shiladi.
    try:
        seed_cars()
    except Exception:
        logger.exception("Seed (bolalar mashinalari) bajarilmadi")
    # DinamoKids do'koniga konditsionerlar (Artel/AUX/Premier) qo'shiladi.
    try:
        seed_conditioners()
    except Exception:
        logger.exception("Seed (konditsionerlar) bajarilmadi")
    # DinamoKids do'koniga bolalar aravachalari (kolyaska) qo'shiladi.
    try:
        seed_strollers()
    except Exception:
        logger.exception("Seed (kolyaskalar) bajarilmadi")
    # Bravo electronics do'koniga video'dan aniqlangan mahsulotlar (yarim avtomat,
    # vitrina sovutkich, gaz panel, ventilyator, quritgich, chivin to'ri) qo'shiladi.
    try:
        seed_bravo_video()
    except Exception:
        logger.exception("Seed (video mahsulotlari) bajarilmadi")
    # ProMan Electronics do'koniga 25 ta kunlik zarur (300k+) mahsulot qo'shiladi.
    try:
        seed_proman()
    except Exception:
        logger.exception("Seed (ProMan Electronics) bajarilmadi")
    # Guruhlarga avtomatik reklama tarqatuvchi fon vazifasi.
    # Sozlash: Admin panel → «📣 Guruhlarga reklama» yoki /reklama buyrug'i.
    from app.handlers.ads import ads_scheduler
    asyncio.create_task(ads_scheduler(bot))
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
