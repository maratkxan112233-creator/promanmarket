from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.start import router as start_router
from app.handlers.seller.application import router as seller_router


storage = MemoryStorage()

dp = Dispatcher(storage=storage)

dp.include_router(start_router)
dp.include_router(seller_router)
