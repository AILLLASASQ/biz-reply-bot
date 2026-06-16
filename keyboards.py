from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

RULES_PER_PAGE = 5


def _trunc(t, n=30):
    t = t or ""
    return t if len(t) <= n else t[: n - 1] + "…"


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ إضافة رد"), KeyboardButton(text="👋 الترحيب")],
            [KeyboardButton(text="📋 قائمة الردود"), KeyboardButton(text="🧮 الحاسبة")],
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


def rules_kb(rules, page=0) -> InlineKeyboardMarkup:
    total = len(rules)
    pages = max(1, (total + RULES_PER_PAGE - 1) // RULES_PER_PAGE)
    page = max(0, min(page, pages - 1))
    chunk = rules[page * RULES_PER_PAGE : (page + 1) * RULES_PER_PAGE]

    rows = []
    for r in chunk:
        rows.append(
            [
                InlineKeyboardButton(text=f"✏️ {_trunc(r['keyword'], 18)}", callback_data=f"edit:{r['id']}"),
                InlineKeyboardButton(text="🗑", callback_data=f"del:{r['id']}"),
            ]
        )
    if not chunk:
        rows.append([InlineKeyboardButton(text="لا توجد ردود", callback_data="noop")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="« السابق", callback_data=f"page:{page-1}"))
    if pages > 1:
        nav.append(InlineKeyboardButton(text=f"{page+1}/{pages}", callback_data="noop"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton(text="التالي »", callback_data=f"page:{page+1}"))
    if nav:
        rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def edit_fields_kb(rule_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="الكلمة المفتاحية", callback_data=f"ef:kw:{rule_id}")],
            [InlineKeyboardButton(text="نص الرد", callback_data=f"ef:reply:{rule_id}")],
            [InlineKeyboardButton(text="نوع المطابقة", callback_data=f"ef:match:{rule_id}")],
            [InlineKeyboardButton(text="الأزرار", callback_data=f"ef:buttons:{rule_id}")],
        ]
    )


def edit_match_kb(rule_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="يحتوي على الكلمة", callback_data=f"em:contains:{rule_id}")],
            [InlineKeyboardButton(text="مطابقة تامة", callback_data=f"em:exact:{rule_id}")],
        ]
    )


def reply_inline_kb(rule_id, buttons):
    if not buttons:
        return None
    btns = []
    for i, b in enumerate(buttons):
        if b.get("url"):
            btns.append(InlineKeyboardButton(text=_trunc(b["text"]), url=b["url"]))
        else:
            btns.append(InlineKeyboardButton(text=_trunc(b["text"]), callback_data=f"b:{rule_id}:{i}"))
    rows = [btns[i : i + 2] for i in range(0, len(btns), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def greeting_menu_kb(enabled) -> InlineKeyboardMarkup:
    toggle = "⏸ إيقاف الترحيب" if enabled else "▶️ تفعيل الترحيب"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ نص الترحيب", callback_data="gr:text")],
            [InlineKeyboardButton(text="⏱ عدد الساعات", callback_data="gr:hours")],
            [InlineKeyboardButton(text=toggle, callback_data="gr:toggle")],
        ]
    )


def calc_menu_kb(enabled) -> InlineKeyboardMarkup:
    toggle = "⏸ إيقاف الحاسبة" if enabled else "▶️ تفعيل الحاسبة"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=toggle, callback_data="calc:toggle")]]
    )


def calc_history_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🗑 مسح سجلي", callback_data="calc:clear")]]
    )
