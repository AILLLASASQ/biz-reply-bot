from aiogram.fsm.state import State, StatesGroup


class AddRule(StatesGroup):
    keyword = State()
    match_type = State()
    reply = State()
    buttons = State()


class EditField(StatesGroup):
    value = State()


class DefaultReply(StatesGroup):
    text = State()
