from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.start import router as start_router
from app.handlers.seller.application import router as seller_app_router
from app.handlers.admin import router as admin_router
from app.handlers.seller_panel import router as seller_panel_router
from app.handlers.common import router as common_router

storage = MemoryStorage()

dp = Dispatcher(storage=storage)

dp.include_router(admin_router)
dp.include_router(seller_panel_router)
dp.include_router(common_router)
dp.include_router(seller_app_router)
dp.include_router(start_router)
