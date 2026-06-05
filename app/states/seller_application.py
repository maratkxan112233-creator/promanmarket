from aiogram.fsm.state import State, StatesGroup


class SellerApplicationState(StatesGroup):
    full_name = State()
    phone = State()
    city = State()
    shop_name = State()
    card_number = State()
    passport_photo = State()
    selfie_photo = State()


class EditShopState(StatesGroup):
    field = State()
    value = State()


class EditProductState(StatesGroup):
    field = State()
    value = State()


class OrderState(StatesGroup):
    delivery = State()
    address  = State()
    phone    = State()
    receipt  = State()
    confirm  = State()


class ReviewState(StatesGroup):
    stars = State()
    comment = State()


class SearchState(StatesGroup):
    query = State()
