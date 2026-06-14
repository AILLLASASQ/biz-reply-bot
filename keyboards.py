from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ إضافة رد")],
            [KeyboardButton(text="📋 قائمة الردود")],
            [KeyboardButton(text="⏯ تشغيل / إيقاف"), KeyboardButton(text="💳 اشتراكي")],
        ],
        resize_keyboard=True,
    )


def match_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="يحتوي على الكلمة", callback_data="match:contains")],
            [InlineKeyboardButton(text="مطابقة تامة", callback_data="match:exact")],
        ]
    )


def rules_kb(rules) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"🗑 حذف: {r['keyword']}", callback_data=f"del:{r['id']}")]
        for r in rules
    ]
    if not rows:
        rows = [[InlineKeyboardButton(text="لا توجد ردود", callback_data="noop")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reply_inline_kb(rule_id, buttons):
    if not buttons:
        return None
    rows = []
    for i, b in enumerate(buttons):
        if b.get("url"):
            rows.append([InlineKeyboardButton(text=b["text"], url=b["url"])])
        else:
            rows.append([InlineKeyboardButton(text=b["text"], callback_data=f"b:{rule_id}:{i}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
