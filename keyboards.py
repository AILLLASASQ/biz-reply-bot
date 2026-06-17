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
            [KeyboardButton(text="🗂 الأقسام")],
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
            [InlineKeyboardButton(text="🔘 أزرار الترحيب", callback_data="gr:buttons")],
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


def calc_again_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔄 احسب مرة ثانية", callback_data="calc:again")]]
    )


def calc_intro_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🧮 ابدأ الحساب", callback_data="calc:start"),
                InlineKeyboardButton(text="📋 سجلي", callback_data="calc:history"),
            ],
            [InlineKeyboardButton(text="📖 الجدول", callback_data="calc:table")],
        ]
    )


def greeting_buttons_kb(buttons):
    if not buttons:
        return None
    btns = []
    for i, b in enumerate(buttons):
        if b.get("url"):
            btns.append(InlineKeyboardButton(text=_trunc(b["text"]), url=b["url"]))
        else:
            btns.append(InlineKeyboardButton(text=_trunc(b["text"]), callback_data=f"gb:{i}"))
    per_row = 1 if any(len(b.get("text", "")) > 16 for b in buttons) else 2
    rows = [btns[i : i + per_row] for i in range(0, len(btns), per_row)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def section_render_kb(section, main_id):
    sid = section.get("id")

    def _mk(b, i):
        if b.get("kind") == "section":
            return InlineKeyboardButton(text=_trunc(b["text"]), callback_data=f"sec:{b['target']}")
        elif b.get("url"):
            return InlineKeyboardButton(text=_trunc(b["text"]), url=b["url"])
        return InlineKeyboardButton(text=_trunc(b["text"]), callback_data=f"sci:{sid}:{i}")

    rows = []
    pending = []
    for i, b in enumerate(section.get("buttons", [])):
        btn = _mk(b, i)
        if b.get("wide", True):
            if pending:
                rows.append(pending)
                pending = []
            rows.append([btn])
        else:
            pending.append(btn)
            if len(pending) == 2:
                rows.append(pending)
                pending = []
    if pending:
        rows.append(pending)
    if not rows:
        rows.append([InlineKeyboardButton(text="(فارغ)", callback_data="noop")])
    if sid != main_id and main_id:
        rows.append([InlineKeyboardButton(text="🔙 رجوع", callback_data=f"sec:{main_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sx_width_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="◼️ صف كامل", callback_data="sx:w:full"),
            InlineKeyboardButton(text="◧ نصف", callback_data="sx:w:half"),
        ]]
    )


def sx_list_kb(sections, main_id):
    rows = []
    for sec in sections:
        star = " ⭐" if sec.get("id") == main_id else ""
        rows.append([InlineKeyboardButton(text=f"{sec['name']}{star}", callback_data=f"sx:open:{sec['id']}")])
    rows.append([InlineKeyboardButton(text="➕ قسم جديد", callback_data="sx:new")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sx_section_kb(section, main_id):
    sid = section["id"]
    rows = [
        [InlineKeyboardButton(text="➕ زر يفتح قسماً", callback_data=f"sx:addsec:{sid}")],
        [InlineKeyboardButton(text="➕ زر محتوى", callback_data=f"sx:addcon:{sid}")],
    ]
    if sid != main_id:
        rows.append([InlineKeyboardButton(text="⭐ تعيين كرئيسي", callback_data=f"sx:main:{sid}")])
    if section.get("buttons"):
        rows.append([InlineKeyboardButton(text="🗑 حذف زر", callback_data=f"sx:bmanage:{sid}")])
    rows.append([InlineKeyboardButton(text="🗑 حذف القسم", callback_data=f"sx:del:{sid}")])
    rows.append([InlineKeyboardButton(text="🔙 الأقسام", callback_data="sx:list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sx_pick_target_kb(sections, sid):
    rows = []
    for sec in sections:
        if sec["id"] == sid:
            continue
        rows.append([InlineKeyboardButton(text=sec["name"], callback_data=f"sx:pick:{sid}:{sec['id']}")])
    rows.append([InlineKeyboardButton(text="إلغاء", callback_data=f"sx:open:{sid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def sx_buttons_manage_kb(section):
    sid = section["id"]
    rows = []
    for i, b in enumerate(section.get("buttons", [])):
        rows.append([InlineKeyboardButton(text=f"🗑 {_trunc(b.get('text', ''), 24)}", callback_data=f"sx:bdel:{sid}:{i}")])
    if not rows:
        rows.append([InlineKeyboardButton(text="(لا أزرار)", callback_data="noop")])
    rows.append([InlineKeyboardButton(text="🔙 رجوع للقسم", callback_data=f"sx:open:{sid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
