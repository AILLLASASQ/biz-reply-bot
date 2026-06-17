import time

from aiogram import Router, Bot, F
from aiogram.types import BusinessConnection, Message, CallbackQuery

import config
import database as db
import keyboards as kb
import calc

router = Router()

_calc_state = {}


@router.business_connection()
async def on_connect(conn: BusinessConnection):
    rights = getattr(conn, "rights", None)
    if rights is not None:
        can_reply = bool(getattr(rights, "can_reply", False))
    else:
        can_reply = bool(getattr(conn, "can_reply", False))

    enabled = bool(conn.is_enabled) and can_reply
    await db.save_connection(conn.user.id, conn.id, enabled)
    await db.ensure_trial(conn.user.id, config.TRIAL_DAYS)


async def _save_and_reply_calc(message, bot, conn_id, owner_id, customer_id, you, opp):
    yp, op, win, loss = calc.compute(you, opp)
    await bot.send_message(
        chat_id=message.chat.id,
        text=calc.format_result(you, opp),
        business_connection_id=conn_id,
        reply_markup=kb.calc_again_kb(),
    )
    await db.add_calc_history(
        owner_id,
        str(customer_id),
        {"you": you, "opp": opp, "yp": yp, "op": op, "win": win, "loss": loss, "ts": time.time()},
    )


async def _start_calc(message, bot, conn_id, owner_id, customer_id, text, key):
    parts = text.split()
    nums = [calc.parse_number(p) for p in parts[1:]]
    nums = [n for n in nums if n is not None]
    if len(nums) >= 2:
        await _save_and_reply_calc(message, bot, conn_id, owner_id, customer_id, nums[0], nums[1])
        return
    _calc_state[key] = {"step": "you"}
    await bot.send_message(
        chat_id=message.chat.id,
        text="🧮 أرسل شعبيتك (أو «إلغاء»):",
        business_connection_id=conn_id,
    )


async def _handle_calc_step(message, bot, conn_id, owner_id, customer_id, text, st, key):
    if text in ("إلغاء", "الغاء"):
        _calc_state.pop(key, None)
        await bot.send_message(
            chat_id=message.chat.id, text="أُلغيت الحاسبة.", business_connection_id=conn_id
        )
        return
    n = calc.parse_number(text)
    if n is None:
        await bot.send_message(
            chat_id=message.chat.id,
            text="أرسل رقماً صحيحاً (أو «إلغاء»).",
            business_connection_id=conn_id,
        )
        return
    if st["step"] == "you":
        st["you"] = n
        st["step"] = "opp"
        await bot.send_message(
            chat_id=message.chat.id,
            text="🔴 أرسل شعبية الخصم:",
            business_connection_id=conn_id,
        )
        return
    you = st.get("you", 0)
    _calc_state.pop(key, None)
    await _save_and_reply_calc(message, bot, conn_id, owner_id, customer_id, you, n)


async def _menu_keyboard(owner_id, greeting):
    main_id = await db.get_main_section_id(owner_id)
    if main_id:
        sections = await db.get_sections(owner_id)
        section = next((x for x in sections if x.get("id") == main_id), None)
        if section and section.get("buttons"):
            return kb.section_render_kb(section, main_id)
    return kb.greeting_buttons_kb(greeting.get("buttons"))


@router.business_message(F.text)
async def on_message(message: Message, bot: Bot):
    if message.from_user and message.from_user.is_bot:
        return

    conn_id = message.business_connection_id
    if not conn_id:
        return

    owner_id, enabled, rules, sub_active, greeting, calc_enabled = await db.get_reply_context(conn_id)
    if not owner_id or not enabled or not sub_active:
        return

    if not message.from_user:
        return
    if str(message.from_user.id) == str(owner_id):
        return

    customer_id = message.from_user.id
    text = (message.text or "").strip()
    key = (conn_id, str(customer_id))

    if calc_enabled:
        st = _calc_state.get(key)
        if st is not None:
            await _handle_calc_step(message, bot, conn_id, owner_id, customer_id, text, st, key)
            return
        if text in ("سجلي", "عملياتي"):
            ops = await db.get_calc_history(owner_id, str(customer_id))
            await bot.send_message(
                chat_id=message.chat.id,
                text=calc.format_history(ops),
                business_connection_id=conn_id,
                reply_markup=kb.calc_history_kb() if ops else None,
            )
            return
        if text == "حاسبة" or text.startswith("حاسبة "):
            await _start_calc(message, bot, conn_id, owner_id, customer_id, text, key)
            return

    if text == "الأقسام":
        main_id = await db.get_main_section_id(owner_id)
        if main_id:
            sections = await db.get_sections(owner_id)
            section = next((x for x in sections if x.get("id") == main_id), None)
            if section:
                await bot.send_message(
                    chat_id=message.chat.id,
                    text=section["name"],
                    business_connection_id=conn_id,
                    reply_markup=kb.section_render_kb(section, main_id),
                )
                return

    if text == "القائمة":
        await bot.send_message(
            chat_id=message.chat.id,
            text=greeting["text"] or "👋 اختر ما يهمك:",
            business_connection_id=conn_id,
            reply_markup=await _menu_keyboard(owner_id, greeting),
        )
        return

    if greeting["enabled"] and greeting["text"]:
        cust = str(message.from_user.id)
        last = await db.get_last_seen(owner_id, cust)
        now = time.time()
        gap = (greeting["hours"] or 0) * 3600
        should_greet = (
            last is None
            or (now - last) >= gap
            or (greeting["activated_at"] and last < greeting["activated_at"])
        )
        await db.set_last_seen(owner_id, cust, now)
        if should_greet:
            await bot.send_message(
                chat_id=message.chat.id,
                text=greeting["text"],
                business_connection_id=conn_id,
                reply_markup=await _menu_keyboard(owner_id, greeting),
            )

    low = text.lower()
    for rule in rules:
        kw = (rule.get("keyword") or "").lower().strip()
        if not kw:
            continue
        if rule.get("match_type") == "exact":
            hit = low == kw
        else:
            hit = kw in low
        if hit:
            await bot.send_message(
                chat_id=message.chat.id,
                text=rule["reply"],
                business_connection_id=conn_id,
                reply_markup=kb.reply_inline_kb(rule.get("id"), rule.get("buttons")),
            )
            break


@router.callback_query(F.data.in_({"calc:again", "calc:start"}))
async def on_calc_start(call: CallbackQuery, bot: Bot):
    try:
        await call.answer()
    except Exception:
        pass
    conn_id = getattr(call.message, "business_connection_id", None)
    if not conn_id:
        return
    key = (conn_id, str(call.from_user.id))
    _calc_state[key] = {"step": "you"}
    await bot.send_message(
        chat_id=call.message.chat.id,
        text="🧮 أرسل شعبيتك (أو «إلغاء»):",
        business_connection_id=conn_id,
    )


@router.callback_query(F.data == "calc:history")
async def on_calc_history(call: CallbackQuery, bot: Bot):
    try:
        await call.answer()
    except Exception:
        pass
    conn_id = getattr(call.message, "business_connection_id", None)
    if not conn_id:
        return
    owner_id, enabled, rules, sub_active, _, _ = await db.get_reply_context(conn_id)
    if not owner_id:
        return
    ops = await db.get_calc_history(owner_id, str(call.from_user.id))
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=calc.format_history(ops),
        business_connection_id=conn_id,
        reply_markup=kb.calc_history_kb() if ops else None,
    )


@router.callback_query(F.data == "calc:table")
async def on_calc_table(call: CallbackQuery, bot: Bot):
    try:
        await call.answer()
    except Exception:
        pass
    conn_id = getattr(call.message, "business_connection_id", None)
    if not conn_id:
        return
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=calc.format_table(),
        business_connection_id=conn_id,
    )


@router.callback_query(F.data == "calc:clear")
async def on_calc_clear(call: CallbackQuery, bot: Bot):
    try:
        await call.answer("تم المسح")
    except Exception:
        pass
    conn_id = getattr(call.message, "business_connection_id", None)
    if not conn_id:
        return
    owner_id, enabled, rules, sub_active, _, _ = await db.get_reply_context(conn_id)
    if not owner_id:
        return
    await db.clear_calc_history(owner_id, str(call.from_user.id))
    await bot.send_message(
        chat_id=call.message.chat.id,
        text="🗑 تم مسح سجلك.",
        business_connection_id=conn_id,
    )


@router.callback_query(F.data.startswith("gb:"))
async def on_greeting_button(call: CallbackQuery, bot: Bot):
    try:
        await call.answer()
    except Exception:
        pass
    conn_id = getattr(call.message, "business_connection_id", None)
    if not conn_id:
        return
    owner_id, enabled, rules, sub_active, greeting, calc_enabled = await db.get_reply_context(conn_id)
    if not owner_id:
        return
    try:
        idx = int(call.data.split(":")[1])
    except (ValueError, IndexError):
        return
    btns = greeting.get("buttons") or []
    if idx < 0 or idx >= len(btns):
        return
    b = btns[idx]
    if b.get("calc"):
        if not calc_enabled:
            await bot.send_message(
                chat_id=call.message.chat.id,
                text="🧮 الحاسبة موقوفة حالياً.",
                business_connection_id=conn_id,
            )
            return
        await bot.send_message(
            chat_id=call.message.chat.id,
            text=b.get("reply") or "🧮 حاسبة المعركة الفردية",
            business_connection_id=conn_id,
            reply_markup=kb.calc_intro_kb(),
        )
        return
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=b.get("reply", ""),
        business_connection_id=conn_id,
    )


@router.callback_query(F.data.startswith("sec:"))
async def on_section_nav(call: CallbackQuery, bot: Bot):
    try:
        await call.answer()
    except Exception:
        pass
    conn_id = getattr(call.message, "business_connection_id", None)
    if not conn_id:
        return
    owner_id, enabled, rules, sub_active, greeting, calc_enabled = await db.get_reply_context(conn_id)
    if not owner_id:
        return
    sid = call.data.split(":", 1)[1]
    sections = await db.get_sections(owner_id)
    section = next((x for x in sections if x.get("id") == sid), None)
    if not section:
        return
    main_id = await db.get_main_section_id(owner_id)
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=section["name"],
        business_connection_id=conn_id,
        reply_markup=kb.section_render_kb(section, main_id),
    )


@router.callback_query(F.data.startswith("sci:"))
async def on_section_content(call: CallbackQuery, bot: Bot):
    try:
        await call.answer()
    except Exception:
        pass
    conn_id = getattr(call.message, "business_connection_id", None)
    if not conn_id:
        return
    owner_id, enabled, rules, sub_active, greeting, calc_enabled = await db.get_reply_context(conn_id)
    if not owner_id:
        return
    parts = call.data.split(":")
    if len(parts) != 3:
        return
    sid = parts[1]
    try:
        i = int(parts[2])
    except ValueError:
        return
    sections = await db.get_sections(owner_id)
    section = next((x for x in sections if x.get("id") == sid), None)
    if not section:
        return
    btns = section.get("buttons", [])
    if i < 0 or i >= len(btns):
        return
    b = btns[i]
    if b.get("calc"):
        if not calc_enabled:
            await bot.send_message(
                chat_id=call.message.chat.id,
                text="🧮 الحاسبة موقوفة حالياً.",
                business_connection_id=conn_id,
            )
            return
        await bot.send_message(
            chat_id=call.message.chat.id,
            text=b.get("reply") or "🧮 حاسبة المعركة الفردية",
            business_connection_id=conn_id,
            reply_markup=kb.calc_intro_kb(),
        )
        return
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=b.get("reply", ""),
        business_connection_id=conn_id,
    )


@router.callback_query(F.data.startswith("b:"))
async def on_button(call: CallbackQuery, bot: Bot):
    try:
        await call.answer()
    except Exception:
        pass

    parts = call.data.split(":")
    if len(parts) != 3:
        return
    _, rule_id, idx_str = parts
    try:
        idx = int(idx_str)
    except ValueError:
        return

    conn_id = getattr(call.message, "business_connection_id", None)
    if not conn_id:
        return

    owner_id, enabled, rules, sub_active, _, calc_enabled = await db.get_reply_context(conn_id)
    if not owner_id or not sub_active:
        return

    rule = next((r for r in rules if r.get("id") == rule_id), None)
    if not rule:
        return
    buttons = rule.get("buttons") or []
    if idx < 0 or idx >= len(buttons):
        return

    btn = buttons[idx]
    if btn.get("calc"):
        if not calc_enabled:
            await bot.send_message(
                chat_id=call.message.chat.id,
                text="🧮 الحاسبة موقوفة حالياً.",
                business_connection_id=conn_id,
            )
            return
        await bot.send_message(
            chat_id=call.message.chat.id,
            text=btn.get("reply") or "🧮 حاسبة المعركة الفردية",
            business_connection_id=conn_id,
            reply_markup=kb.calc_intro_kb(),
        )
        return

    await bot.send_message(
        chat_id=call.message.chat.id,
        text=btn.get("reply", ""),
        business_connection_id=conn_id,
    )
