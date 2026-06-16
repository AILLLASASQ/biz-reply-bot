# منطق حاسبة الشعبية (الفردية) — دوال خالصة بلا قاعدة بيانات

_ARABIC = str.maketrans("٠١٢٣٤٥٦٧٨٩،", "0123456789,")

_TABLE = [
    (2000, 6),
    (4000, 10),
    (8000, 14),
    (15000, 16),
    (50000, 20),
    (120000, 24),
    (260000, 28),
    (500000, 32),
    (900000, 36),
    (2000000, 40),
]
_MAX_POINTS = 42


def parse_number(s):
    s = (s or "").translate(_ARABIC)
    s = s.replace(",", "").replace(" ", "").strip()
    if s.isdigit():
        return int(s)
    return None


def points_for(value):
    for upper, pts in _TABLE:
        if value <= upper:
            return pts
    return _MAX_POINTS


def compute(you, opp):
    yp = points_for(you)
    op = points_for(opp)
    win = yp + op // 2
    loss = yp // 2
    return yp, op, win, loss


def format_result(you, opp):
    yp, op, win, loss = compute(you, opp)
    return (
        "🧮 حاسبة الشعبية (الفردية)\n\n"
        f"🟢 شعبيتك: {you:,} ⟵ ({yp} نقطة)\n"
        f"🔴 الخصم: {opp:,} ⟵ ({op} نقطة)\n\n"
        f"✅ فوزك يعطيك: +{win} نقطة\n"
        f"❌ خسارتك تخصم: −{loss} نقطة\n\n"
        "اكتب «حاسبة» لحساب آخر، أو «سجلي» لعملياتك."
    )


def format_history(ops):
    if not ops:
        return "📋 ما عندك عمليات بعد. اكتب «حاسبة» لتبدأ."
    lines = ["📋 آخر عملياتك:\n"]
    for i, o in enumerate(ops, 1):
        lines.append(
            f"{i}) {o['you']:,} ({o['yp']}) ضد {o['opp']:,} ({o['op']}) "
            f"← فوز +{o['win']} / خسارة −{o['loss']}"
        )
    return "\n".join(lines)
