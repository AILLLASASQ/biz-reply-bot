import time

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import config
import database as db
import keyboards as kb
from states import AddRule, EditField, DefaultReply

router = Router()


def _fmt_status(plan, exp, active):
    if not exp:
        return "لا يوجد اشتراك بعد."
    days_left = max(0, int((exp - time.time()) / 86400))
    until = time.strftime("%Y-%m-%d", time.localtime(exp))
    state = "فعّال ✅" if active else "منتهٍ ❌"
    return f"الباقة: {plan or '—'}\nالحالة: {state}\nينتهي: {until} ({days_left} يوم متبقٍّ)"


def _rules_text(rules, page):
    per = kb.RULES_PER_PAGE
    chunk = rules[page * per : (page + 1) * per]
    if not chunk:
        return "لا توجد ردود."
    lines = []
    for r in chunk:
        bc = len(r.get("buttons") or [])
        extra = f" [{bc} زر]" if bc else ""
        lines.append(f"• <b>{r['keyword']}</b> ← {r['reply']}{extra}")
    return "\n".join(lines)


def _parse_buttons(text):
    buttons = []
    if (text or "").strip() != "تخطي":
        for line in (text or "").splitlines():
            if "|" in line:
                t, _, v = line.partition("|")
                t, v = t.strip(), v.strip()
                if t and v:
                    if v.startswith("http://") or v.startswith("https://"):
                        buttons.append({"text": t, "url": v})
                    else:
                        buttons.append({"text": t, "reply": v})
    return buttons


@router.message(CommandStart())
async def start(message: Message):
    await db.ensure_trial(message.from_user.id, config.TRIAL_DAYS)
    await message.answer(
        "أهلاً بك 👋\n"
        "بوت الردود التلقائية لحساب <b>Telegram Business</b>.\n\n"
        f"حصلت على تجربة مجانية {config.TRIAL_DAYS} يوم.\n"
        "اربط البوت من: إعدادات تيليجرام ← Telegram Business ← Chatbots،\n"
        "ثم أضف الكلمات والردود من الأزرار بالأسفل.\n\n"
        "اكتب /help لعرض كل الأوامر.",
        reply_markup=kb.main_menu(),
    )


@router.message(Command("menu"))
async def menu_cmd(message: Message):
    await message.answer("القائمة:", reply_markup=kb.main_menu())


@router.message(Command("help"))
async def help_cmd(message: Message):
    text = (
        "<b>الأزرار:</b>\n"
        "➕ إضافة رد — كلمة + رد (مع أزرار اختيارية).\n"
        "📋 قائمة الردود — عرض/تعديل/حذف الردود.\n"
        "⏯ تشغيل / إيقاف — تفعيل أو إيقاف الردود.\n"
        "💳 اشتراكي — حالة اشتراكك ومعرّفك.\n\n"
        "<b>الأوامر:</b>\n"
        "/menu — إظهار الأزرار.\n"
        "/help — هذه المساعدة."
    )
    if message.from_user.id in config.ADMIN_IDS:
        text += (
            "\n\n<b>أوامر الأدمن:</b>\n"
            "/activate &lt;ايدي&gt; &lt;أيام&gt; [باقة]\n"
            "/sub &lt;ايدي&gt;"
        )
    await message.answer(text, reply_markup=kb.main_menu())


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
    exp = await db.set_subscription(owner_id, plan, days, message.from_user.id)
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
        "• لو القيمة <b>رابط</b> ← زر رابط.\n"
        "• لو القيمة <b>نص</b> ← زر تفاعلي يرد عند الضغط.\n\n"
        "مثال:\n"
        "زيارة المتجر | https://store.example.com\n"
        "الأسعار | أسعارنا تبدأ من ٥٠ ريال\n\n"
        "أو اكتب «تخطي» بدون أزرار."
    )


@router.message(AddRule.buttons)
async def add_buttons(message: Message, state: FSMContext):
    buttons = _parse_buttons(message.text)
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
    await message.answer(_rules_text(rules, 0), reply_markup=kb.rules_kb(rules, 0))


@router.callback_query(F.data.startswith("page:"))
async def page_nav(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    rules = await db.get_rules(call.from_user.id)
    await call.message.edit_text(_rules_text(rules, page), reply_markup=kb.rules_kb(rules, page))
    await call.answer()


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    await call.answer()


@router.callback_query(F.data.startswith("del:"))
async def del_rule(call: CallbackQuery):
    rule_id = call.data.split(":")[1]
    await db.delete_rule(call.from_user.id, rule_id)
    await call.message.edit_text("🗑 تم حذف الرد.")
    await call.answer()


@router.callback_query(F.data.startswith("edit:"))
async def edit_open(call: CallbackQuery):
    rule_id = call.data.split(":")[1]
    await call.message.answer("وش تبي تعدّل؟", reply_markup=kb.edit_fields_kb(rule_id))
    await call.answer()


@router.callback_query(F.data.startswith("ef:"))
async def edit_field(call: CallbackQuery, state: FSMContext):
    _, field, rule_id = call.data.split(":", 2)
    if field == "match":
        await call.message.answer("اختر نوع المطابقة:", reply_markup=kb.edit_match_kb(rule_id))
        await call.answer()
        return
    await state.set_state(EditField.value)
    await state.update_data(edit_id=rule_id, edit_field=field)
    prompts = {
        "kw": "أرسل الكلمة المفتاحية الجديدة:",
        "reply": "أرسل نص الرد الجديد:",
        "buttons": "أرسل الأزرار الجديدة (سطر لكل زر: النص | القيمة)، أو «تخطي» لحذف كل الأزرار:",
    }
    await call.message.answer(prompts[field])
    await call.answer()


@router.callback_query(F.data.startswith("em:"))
async def edit_match_set(call: CallbackQuery):
    _, mtype, rule_id = call.data.split(":", 2)
    await db.update_rule_field(call.from_user.id, rule_id, "match_type", mtype)
    await call.message.edit_text("✅ تم تحديث نوع المطابقة.")
    await call.answer()


@router.message(EditField.value)
async def edit_field_value(message: Message, state: FSMContext):
    data = await state.get_data()
    rule_id = data["edit_id"]
    field = data["edit_field"]
    if field == "kw":
        await db.update_rule_field(message.from_user.id, rule_id, "keyword", message.text)
    elif field == "reply":
        await db.update_rule_field(message.from_user.id, rule_id, "reply", message.text)
    elif field == "buttons":
        await db.update_rule_field(message.from_user.id, rule_id, "buttons", _parse_buttons(message.text))
    await state.clear()
    await message.answer("✅ تم التعديل.", reply_markup=kb.main_menu())


@router.message(F.text == "🤖 الرد الافتراضي")
async def default_reply_menu(message: Message, state: FSMContext):
    current = await db.get_default_reply(message.from_user.id)
    cur_txt = current if current else "غير مفعّل"
    await state.set_state(DefaultReply.text)
    await message.answer(
        f"الرد الافتراضي الحالي:\n{cur_txt}\n\n"
        "أرسل النص الجديد للرد على أي رسالة <b>غير مطابقة</b> لأي كلمة،\n"
        "أو «إيقاف» لتعطيله، أو «إلغاء» للخروج."
    )


@router.message(DefaultReply.text)
async def default_reply_set(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    await state.clear()
    if txt == "إلغاء":
        await message.answer("تم الإلغاء.", reply_markup=kb.main_menu())
        return
    if txt == "إيقاف":
        await db.set_default_reply(message.from_user.id, "")
        await message.answer("تم إيقاف الرد الافتراضي.", reply_markup=kb.main_menu())
        return
    await db.set_default_reply(message.from_user.id, txt)
    await message.answer("✅ تم تعيين الرد الافتراضي.", reply_markup=kb.main_menu())


@router.message(F.text == "⏯ تشغيل / إيقاف")
async def toggle(message: Message):
    current = await db.is_enabled(message.from_user.id)
    await db.set_enabled(message.from_user.id, not current)
    await message.answer("تم الإيقاف ⏸" if current else "تم التشغيل ▶️")
