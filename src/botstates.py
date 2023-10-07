from aiogram.fsm.state import StatesGroup, State

class UserRegistration(StatesGroup):
    full_name = State()
    company = State()
    password = State()