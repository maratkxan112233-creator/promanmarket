import asyncio
import logging

from app.bot.bot import bot
from app.bot.dispatcher import dp
from app.seed_ac import seed_air_conditioners

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Man Market starting...")
    # Bir martalik xavfsiz seed: Bravo electronics do'koniga konditsionerlarni
    # (agar hali yo'q bo'lsa) qo'shadi. Xato bo'lsa ham bot to'xtamasin.
    try:
        seed_air_conditioners()
    except Exception:
        logger.exception("Seed (konditsionerlar) bajarilmadi")
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    asyncio.run(main())
