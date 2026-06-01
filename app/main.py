import asyncio
import logging

from app.bot.bot import bot
from app.bot.dispatcher import dp


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    logger.info("Man Market starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
