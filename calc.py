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
    (8000000, 42),
]
_MAX_POINTS = 44


def parse_number(s):
    s = (s or "").translate(_ARABIC).strip().lower()
    s = s.replace(",", "").replace(" ", "")
    mult = 1
    if s.endswith("k"):
        mult, s = 1000, s[:-1]
    elif s.endswith("m"):
        mult, s = 1_000_000, s[:-1]
    try:
        val = float(s) * mult
    except ValueError:
        return None
    if val < 0:
        return None
    return int(val)


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


def _tier_info(value):
    lower = 0
    for i, (upper, pts) in enumerate(_TABLE):
        if value <= upper:
            next_pts = _TABLE[i + 1][1] if i + 1 < len(_TABLE) else _MAX_POINTS
            return lower, upper, pts, next_pts
        lower = upper + 1
    return _TABLE[-1][0] + 1, None, _MAX_POINTS, None


def progress_bar(value, segments=10):
    lower, upper, pts, next_pts = _tier_info(value)
    if upper is None:
        return f"🔝 أنت في أعلى شريحة ({_MAX_POINTS} نقطة)."
    span = upper - lower
    frac = (value - lower) / span if span > 0 else 1.0
    frac = max(0.0, min(1.0, frac))
    filled = round(frac * segments)
    bar = "▓" * filled + "░" * (segments - filled)
    remaining = upper + 1 - value
    return (
        f"📊 تقدّمك للشريحة التالية ({next_pts} نقطة):\n"
        f"{bar} {int(frac * 100)}%\n"
        f"متبقّي {remaining:,} شعبية"
    )


def format_result(you, opp):
    yp, op, win, loss = compute(you, opp)
    return (
        "🧮 حاسبة الشعبية (الفردية)\n\n"
        f"🟢 شعبيتك: {you:,} ⟵ ({yp} نقطة)\n"
        f"🔴 الخصم: {opp:,} ⟵ ({op} نقطة)\n\n"
        f"✅ فوزك يعطيك: +{win} نقطة\n"
        f"❌ خسارتك تخصم: −{loss} نقطة\n\n"
        f"{progress_bar(you)}\n\n"
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
