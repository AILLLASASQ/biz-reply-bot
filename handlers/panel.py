import time

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

import config
import database as db
import keyboards as kb
from states import AddRule, EditField, Greeting, Buttons

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
        "👋 الترحيب — رسالة ترحيب تلقائية حسب الساعات.\n"
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


# ===== إضافة رد =====
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
    await call.message.answer("الآن أرسل نص الرد (يمكن أن يكون طويلاً ومرتباً بالأسطر):")
    await call.answer()


@router.message(AddRule.reply)
async def add_reply(message: Message, state: FSMContext):
    await state.update_data(reply=message.text, btns=[], btn_mode="add")
    await state.set_state(Buttons.label)
    await message.answer(
        "تبي تضيف أزرار للرد؟\n"
        "أرسل <b>اسم الزر</b> الأول، أو اكتب «تخطي» للحفظ بدون أزرار."
    )


# ===== تدفّق الأزرار (إضافة وتعديل) =====
async def _finalize_buttons(message: Message, state: FSMContext):
    data = await state.get_data()
    btns = data.get("btns", [])
    if data.get("btn_mode") == "greeting":
        await db.set_greeting_buttons(message.from_user.id, btns)
        await state.clear()
        await message.answer(f"✅ تم حفظ أزرار الترحيب ({len(btns)}).", reply_markup=kb.main_menu())
        return
    if data.get("btn_mode") == "edit":
        await db.update_rule_field(message.from_user.id, data["edit_id"], "buttons", btns)
        msg = "✅ تم تحديث أزرار الرد."
    else:
        await db.add_rule(
            message.from_user.id,
            data["keyword"],
            data["reply"],
            data.get("match_type", "contains"),
            btns,
        )
        msg = f"✅ تم حفظ الرد{f' مع {len(btns)} زر' if btns else ''}."
    await state.clear()
    await message.answer(msg, reply_markup=kb.main_menu())


@router.message(Buttons.label)
async def btn_label(message: Message, state: FSMContext):
    label = (message.text or "").strip()
    if label == "تخطي":
        await _finalize_buttons(message, state)
        return
    await state.update_data(pending_label=label)
    await state.set_state(Buttons.value)
    await message.answer(
        "أرسل <b>رد هذا الزر</b>:\n"
        "• نص طويل/مرتب، أو رابط (يبدأ بـ http)\n"
        "• أو <code>/calc</code> ثم شرحك ← زر يفتح الحاسبة"
    )


@router.message(Buttons.value)
async def btn_value(message: Message, state: FSMContext):
    val = (message.text or "").strip()
    data = await state.get_data()
    label = data.get("pending_label", "زر")
    btns = data.get("btns", [])
    if val.startswith("/calc"):
        explanation = val[5:].strip() or "🧮 حاسبة المعركة الفردية"
        btns.append({"text": label, "calc": True, "reply": explanation})
    elif val.startswith("http://") or val.startswith("https://"):
        btns.append({"text": label, "url": val})
    else:
        btns.append({"text": label, "reply": val})
    await state.update_data(btns=btns)
    await state.set_state(Buttons.label)
    await message.answer(
        f"✅ أُضيف الزر «{label}».\n"
        "أرسل اسم الزر التالي، أو اكتب «تخطي» للحفظ."
    )


# ===== قائمة الردود + الترقيم =====
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


# ===== تعديل رد =====
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
    if field == "buttons":
        await state.update_data(btns=[], btn_mode="edit", edit_id=rule_id)
        await state.set_state(Buttons.label)
        await call.message.answer(
            "تعديل الأزرار — أرسل <b>اسم الزر</b> الأول، أو «تخطي» لجعل الرد بدون أزرار."
        )
        await call.answer()
        return
    await state.set_state(EditField.value)
    await state.update_data(edit_id=rule_id, edit_field=field)
    prompts = {
        "kw": "أرسل الكلمة المفتاحية الجديدة:",
        "reply": "أرسل نص الرد الجديد (يمكن أن يكون طويلاً ومرتباً بالأسطر):",
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
    await state.clear()
    await message.answer("✅ تم التعديل.", reply_markup=kb.main_menu())


# ===== الترحيب =====
def _greeting_status(g):
    state = "مفعّل ✅" if g["enabled"] else "موقوف ⏸"
    txt = g["text"] or "— (لم يُحدّد بعد)"
    nb = len(g.get("buttons") or [])
    return f"حالة الترحيب: {state}\nالأزرار: {nb}\nيرحّب من جديد لو الزبون ساكت أكثر من {g['hours']} ساعة.\n\nالنص:\n{txt}"


@router.message(F.text == "👋 الترحيب")
async def greeting_menu(message: Message):
    g = await db.get_greeting(message.from_user.id)
    await message.answer(
        _greeting_status(g) + "\n\nاختر ما تريد تعديله:",
        reply_markup=kb.greeting_menu_kb(g["enabled"]),
    )


@router.callback_query(F.data == "gr:text")
async def greeting_text_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(Greeting.text)
    await call.message.answer("أرسل نص رسالة الترحيب:")
    await call.answer()


@router.message(Greeting.text)
async def greeting_text_set(message: Message, state: FSMContext):
    await db.set_greeting_text(message.from_user.id, (message.text or "").strip())
    await state.clear()
    await message.answer("✅ تم حفظ نص الترحيب.", reply_markup=kb.main_menu())


@router.callback_query(F.data == "gr:hours")
async def greeting_hours_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(Greeting.hours)
    await call.message.answer("كم ساعة سكوت قبل إعادة الترحيب؟ أرسل رقماً (مثال: 12):")
    await call.answer()


@router.message(Greeting.hours)
async def greeting_hours_set(message: Message, state: FSMContext):
    try:
        hours = float((message.text or "").strip())
        if hours < 0:
            raise ValueError
    except ValueError:
        await message.answer("أرسل رقماً صحيحاً للساعات.")
        return
    if hours == int(hours):
        hours = int(hours)
    await db.set_greeting_hours(message.from_user.id, hours)
    await state.clear()
    await message.answer(f"✅ ضُبطت الفجوة على {hours} ساعة.", reply_markup=kb.main_menu())


@router.callback_query(F.data == "gr:buttons")
async def greeting_buttons_start(call: CallbackQuery, state: FSMContext):
    await state.update_data(btns=[], btn_mode="greeting")
    await state.set_state(Buttons.label)
    await call.message.answer(
        "أرسل <b>اسم الزر</b> الأول لأزرار الترحيب، أو «تخطي» للحفظ بدون أزرار.\n"
        "القيمة لكل زر: نص، أو رابط (http)، أو <code>/calc</code> ثم الشرح (للحاسبة)."
    )
    await call.answer()


@router.callback_query(F.data == "gr:toggle")
async def greeting_toggle(call: CallbackQuery):
    enabled = await db.toggle_greeting(call.from_user.id)
    await call.message.edit_text("▶️ تم تفعيل الترحيب (يبدأ من جديد مع الجميع)." if enabled else "⏸ تم إيقاف الترحيب.")
    await call.answer()


# ===== الحاسبة =====
@router.message(F.text == "🧮 الحاسبة")
async def calc_menu(message: Message):
    enabled = await db.get_calc_enabled(message.from_user.id)
    state = "مفعّلة ✅" if enabled else "موقوفة ⏸"
    await message.answer(
        "🧮 حاسبة الشعبية (الفردية)\n"
        f"الحالة: {state}\n\n"
        "لما تكون مفعّلة، الزبون في الخاص يكتب:\n"
        "• «حاسبة 55555 7» ← نتيجة فورية\n"
        "• أو «حاسبة» ← يسأله خطوة بخطوة\n"
        "• «سجلي» ← آخر ٣ عملياته",
        reply_markup=kb.calc_menu_kb(enabled),
    )


@router.callback_query(F.data == "calc:toggle")
async def calc_toggle(call: CallbackQuery):
    enabled = await db.toggle_calc(call.from_user.id)
    await call.message.edit_text("▶️ تم تفعيل الحاسبة." if enabled else "⏸ تم إيقاف الحاسبة.")
    await call.answer()


@router.message(F.text == "⏯ تشغيل / إيقاف")
async def toggle(message: Message):
    current = await db.is_enabled(message.from_user.id)
    await db.set_enabled(message.from_user.id, not current)
    await message.answer("تم الإيقاف ⏸" if current else "تم التشغيل ▶️")
