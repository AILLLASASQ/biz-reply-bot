from aiogram.fsm.state import State, StatesGroup


class AddRule(StatesGroup):
    keyword = State()
    match_type = State()
    reply = State()
