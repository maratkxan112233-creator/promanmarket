from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.handlers.start import router as start_router
from app.handlers.seller.application import router as seller_app_router
from app.handlers.admin import router as admin_router
from app.handlers.seller_panel import router as seller_panel_router
from app.handlers.common import router as common_router

# MemoryStorage вЂ” bot restart bo'lganda barcha FSM state yo'qoladi!
# Production uchun RedisStorage tavsiya etiladi:
#
#   from aiogram.fsm.storage.redis import RedisStorage
#   storage = RedisStorage.from_url("redis://localhost:6379")
#
# Hozircha MemoryStorage qoldirildi (test uchun):
storage = MemoryStorage()

dp = Dispatcher(storage=storage)

# MUHIM: seller_app_router common_router dan OLDIN bo'lishi kerak,
# aks holda FSM state dagi xabarlar common handler tomonidan ushlansa mumkin.
dp.include_router(admin_router)
dp.include_router(seller_panel_router)
dp.include_router(seller_app_router)   # в†ђ common dan OLDIN
dp.include_router(common_router)
dp.include_router(start_router)
