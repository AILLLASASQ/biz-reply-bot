from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import database as db
import keyboards as kb
from states import AddRule

router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        "أهلاً بك 👋\n"
        "هذا بوت الردود التلقائية لحساب <b>Telegram Business</b>.\n\n"
        "1) اربط البوت من: إعدادات تيليجرام ← Telegram Business ← Chatbots.\n"
        "2) أضف الكلمات والردود من الأزرار بالأسفل.\n"
        "3) فعّل الردود وستعمل تلقائياً مع زبائنك.",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == "➕ إضافة رد")
async def add_start(message: Message, state: FSMContext):
    await state.set_state(AddRule.keyword)
    await message.answer("أرسل الكلمة المفتاحية التي سيرد عليها البوت:")


@router.message(AddRule.keyword)
async def add_keyword(message: Message, state: FSMContext):
    await state.update_data(keyword=message.text)
    await state.set_state(AddRule.match_type)
    await message.answer("اختر نوع المطابقة:", reply_markup=kb.match_type_kb())


@router.callback_query(AddRule.match_type, F.data.startswith("match:"))
async def add_match(call: CallbackQuery, state: FSMContext):
    await state.update_data(match_type=call.data.split(":")[1])
    await state.set_state(AddRule.reply)
    await call.message.answer("الآن أرسل نص الرد:")
    await call.answer()


@router.message(AddRule.reply)
async def add_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.add_rule(
        message.from_user.id,
        data["keyword"],
        message.text,
        data.get("match_type", "contains"),
    )
    await state.clear()
    await message.answer("✅ تم حفظ الرد.", reply_markup=kb.main_menu())


@router.message(F.text == "📋 قائمة الردود")
async def list_rules(message: Message):
    rules = await db.get_rules(message.from_user.id)
    if not rules:
        await message.answer("لا توجد ردود بعد. أضف أول رد من الزر ➕")
        return
    text = "\n".join([f"• <b>{r['keyword']}</b> ← {r['reply']}" for r in rules])
    await message.answer(text, reply_markup=kb.rules_kb(rules))


@router.callback_query(F.data.startswith("del:"))
async def del_rule(call: CallbackQuery):
    rule_id = call.data.split(":")[1]
    await db.delete_rule(call.from_user.id, rule_id)
    await call.message.edit_text("🗑 تم حذف الرد.")
    await call.answer()


@router.message(F.text == "⏯ تشغيل / إيقاف")
async def toggle(message: Message):
    current = await db.is_enabled(message.from_user.id)
    await db.set_enabled(message.from_user.id, not current)
    await message.answer("تم الإيقاف ⏸" if current else "تم التشغيل ▶️")
