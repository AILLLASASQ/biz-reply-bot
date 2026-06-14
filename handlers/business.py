from aiogram import Router, Bot, F
from aiogram.types import BusinessConnection, Message, CallbackQuery

import database as db
import keyboards as kb

router = Router()


@router.business_connection()
async def on_connect(conn: BusinessConnection):
    rights = getattr(conn, "rights", None)
    if rights is not None:
        can_reply = bool(getattr(rights, "can_reply", False))
    else:
        can_reply = bool(getattr(conn, "can_reply", False))

    enabled = bool(conn.is_enabled) and can_reply
    await db.save_connection(conn.user.id, conn.id, enabled)


@router.business_message(F.text)
async def on_message(message: Message, bot: Bot):
    if message.from_user and message.from_user.is_bot:
        return

    conn_id = message.business_connection_id
    if not conn_id:
        return

    owner_id, enabled, rules = await db.get_reply_context(conn_id)
    if not owner_id or not enabled:
        return

    if message.from_user and str(message.from_user.id) == str(owner_id):
        return

    text = message.text.lower().strip()
    for rule in rules:
        kw = (rule.get("keyword") or "").lower().strip()
        if not kw:
            continue
        if rule.get("match_type") == "exact":
            hit = text == kw
        else:
            hit = kw in text
        if hit:
            await bot.send_message(
                chat_id=message.chat.id,
                text=rule["reply"],
                business_connection_id=conn_id,
                reply_markup=kb.reply_inline_kb(rule.get("id"), rule.get("buttons")),
            )
            break


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

    owner_id, enabled, rules = await db.get_reply_context(conn_id)
    if not owner_id:
        return

    rule = next((r for r in rules if r.get("id") == rule_id), None)
    if not rule:
        return
    buttons = rule.get("buttons") or []
    if idx < 0 or idx >= len(buttons):
        return

    await bot.send_message(
        chat_id=call.message.chat.id,
        text=buttons[idx]["reply"],
        business_connection_id=conn_id,
    )
