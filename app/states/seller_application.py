from aiogram.fsm.state import State
from aiogram.fsm.state import StatesGroup


class SellerApplicationState(StatesGroup):
    full_name = State()
    phone = State()
    shop_name = State()
    card_number = State()
    passport_photo = State()
    selfie_photo = State()
