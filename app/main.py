import asyncio
import logging
import os

from app.app.config.settings import settings
from app.bot.bot import bot
from app.bot.dispatcher import dp
from app.web.server import start_web_server
from app.seed_ac import seed_all
from app.seed_bikes import seed_bikes
from app.seed_cars import seed_cars
from app.seed_conditioners import seed_conditioners
from app.seed_strollers import seed_strollers
from app.seed_bravo_video import seed_bravo_video
from app.seed_proman import seed_proman
from app.seed_kitchen import seed_kitchen
from app.seed_proman_top import seed_proman_top

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
    # ProMan Electronics do'koniga Uzum'da eng ko'p sotilayotgan 40 xil oshxona
    # buyumi (har birida 3 ta rasm) qo'shiladi.
    try:
        seed_kitchen()
    except Exception:
        logger.exception("Seed (ProMan oshxona buyumlari) bajarilmadi")
    # ProMan Electronics do'koniga Uzum'da eng ko'p sotilgan 60 xil elektronika
    # va maishiy texnika mahsuloti (har birida 3 ta rasm) qo'shiladi.
    try:
        seed_proman_top()
    except Exception:
        logger.exception("Seed (ProMan Top-60) bajarilmadi")
    # Guruhlarga avtomatik reklama tarqatuvchi fon vazifasi.
    # Sozlash: Admin panel → «📣 Guruhlarga reklama» yoki /reklama buyrug'i.
    from app.handlers.ads import ads_scheduler
    asyncio.create_task(ads_scheduler(bot))

    # Mini App (ilova) web-serveri — bot bilan bitta event-loop'da.
    # Railway $PORT ni beradi; lokalda settings.WEB_PORT (standart 8080).
    port = int(os.getenv("PORT", settings.WEB_PORT))
    runner = None
    try:
        runner = await start_web_server("0.0.0.0", port)
    except Exception:
        logger.exception("Web-server (Mini App) ishga tushmadi — bot davom etadi")

    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True,
        )
    finally:
        if runner is not None:
            await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
