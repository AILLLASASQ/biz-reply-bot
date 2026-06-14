import time

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import config
import database as db
import keyboards as kb
from states import AddRule

router = Router()


def _fmt_status(plan, exp, active):
    if not exp:
        return "لا يوجد اشتراك بعد."
    days_left = max(0, int((exp - time.time()) / 86400))
    state = "فعّال ✅" if active else "منتهٍ ❌"
    return f"الباقة: {plan or '—'}\nالحالة: {state}\nالمتبقّي: {days_left} يوم"


@router.message(CommandStart())
async def start(message: Message):
    await db.ensure_trial(message.from_user.id, config.TRIAL_DAYS)
    await message.answer(
        "أهلاً بك 👋\n"
        "بوت الردود التلقائية لحساب <b>Telegram Business</b>.\n\n"
        f"حصلت على تجربة مجانية {config.TRIAL_DAYS} يوم.\n"
        "اربط البوت من: إعدادات تيليجرام ← Telegram Business ← Chatbots،\n"
        "ثم أضف الكلمات والردود من الأزرار بالأسفل.",
        reply_markup=kb.main_menu(),
    )


@router.message(F.text == "💳 اشتراكي")
async def my_sub(message: Message):
    await db.ensure_trial(message.from_user.id, config.TRIAL_DAYS)
    plan, exp, active = await db.get_subscription(message.from_user.id)
    await message.answer(
        f"{_fmt_status(plan, exp, active)}\n\n"
        f"معرّفك: <code>{message.from_user.id}</code>\n"
        "للتفعيل/التجديد، أرسل معرّفك للإدارة."
    )


@router.message(Command("activate"))
async def admin_activate(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer("الصيغة: /activate &lt;ايدي&gt; &lt;أيام&gt; [اسم الباقة]")
        return
    owner_id = parts[1]
    try:
        days = int(parts[2])
    except ValueError:
        await message.answer("عدد الأيام يجب أن يكون رقماً.")
        return
    plan = parts[3] if len(parts) > 3 else "paid"
    exp = await db.set_subscription(owner_id, plan, days)
    until = time.strftime("%Y-%m-%d", time.localtime(exp))
    await message.answer(f"✅ فُعّل اشتراك <code>{owner_id}</code>: {plan} — حتى {until}.")


@router.message(Command("sub"))
async def admin_sub(message: Message):
    if message.from_user.id not in config.ADMIN_IDS:
        return
    parts = (message.text or "").split()
    if len(parts) < 2:
        await message.answer("الصيغة: /sub &lt;ايدي&gt;")
        return
    plan, exp, active = await db.get_subscription(parts[1])
    await message.answer(f"اشتراك <code>{parts[1]}</code>:\n{_fmt_status(plan, exp, active)}")


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
    await state.update_data(reply=message.text)
    await state.set_state(AddRule.buttons)
    await message.answer(
        "أرسل الأزرار (اختياري) — سطر لكل زر بالصيغة <code>النص | القيمة</code>:\n\n"
        "• لو القيمة <b>رابط</b> ← يصير زر رابط.\n"
        "• لو القيمة <b>نص</b> ← يصير زر تفاعلي يرد عند الضغط.\n\n"
        "مثال:\n"
        "زيارة المتجر | https://store.example.com\n"
        "الأسعار | أسعارنا تبدأ من ٥٠ ريال\n\n"
        "أو اكتب «تخطي» بدون أزرار."
    )


@router.message(AddRule.buttons)
async def add_buttons(message: Message, state: FSMContext):
    buttons = []
    if (message.text or "").strip() != "تخطي":
        for line in (message.text or "").splitlines():
            if "|" in line:
                text, _, val = line.partition("|")
                text, val = text.strip(), val.strip()
                if text and val:
                    if val.startswith("http://") or val.startswith("https://"):
                        buttons.append({"text": text, "url": val})
                    else:
                        buttons.append({"text": text, "reply": val})

    data = await state.get_data()
    await db.add_rule(
        message.from_user.id,
        data["keyword"],
        data["reply"],
        data.get("match_type", "contains"),
        buttons,
    )
    await state.clear()
    note = f" مع {len(buttons)} زر" if buttons else ""
    await message.answer(f"✅ تم حفظ الرد{note}.", reply_markup=kb.main_menu())


@router.message(F.text == "📋 قائمة الردود")
async def list_rules(message: Message):
    rules = await db.get_rules(message.from_user.id)
    if not rules:
        await message.answer("لا توجد ردود بعد. أضف أول رد من الزر ➕")
        return
    lines = []
    for r in rules:
        btn_count = len(r.get("buttons") or [])
        extra = f" [{btn_count} زر]" if btn_count else ""
        lines.append(f"• <b>{r['keyword']}</b> ← {r['reply']}{extra}")
    await message.answer("\n".join(lines), reply_markup=kb.rules_kb(rules))


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
