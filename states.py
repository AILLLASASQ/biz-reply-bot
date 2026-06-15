from aiogram.fsm.state import State, StatesGroup


class AddRule(StatesGroup):
    keyword = State()
    match_type = State()
    reply = State()


class EditField(StatesGroup):
    value = State()


class Greeting(StatesGroup):
    text = State()
    hours = State()


class Buttons(StatesGroup):
    label = State()
    value = State()
